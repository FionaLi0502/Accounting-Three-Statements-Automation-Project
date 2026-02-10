"""
Three Statements Automation - Refactored Main Application
Supports Trial Balance and GL Activity uploads with intelligent downgrade behavior
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import os
from typing import Dict, List, Tuple, Optional

# Import custom modules
from validation import (normalize_column_headers, check_required_columns,
                       validate_trial_balance, validate_gl_activity,
                       validate_common_issues, apply_auto_fixes)
from mapping import map_accounts, get_mapping_stats
from excel_writer import (write_financial_data_to_template, 
                          calculate_financial_statements,
                          validate_template_structure)
from pdf_export import create_pdf_report
from ai_summary import generate_ai_summary, summarize_validation_issues
from sample_data import (load_sample_tb, load_sample_gl, load_random_backup_gl,
                         get_template_path, list_available_datasets)

# Page config
st.set_page_config(
    page_title="Three Statements Automation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.validation-critical{background-color:#f8d7da;border-left:4px solid #dc3545;padding:1rem;margin:0.5rem 0;border-radius:4px}
.validation-warning{background-color:#fff3cd;border-left:4px solid #ffc107;padding:1rem;margin:0.5rem 0;border-radius:4px}
.validation-info{background-color:#d1ecf1;border-left:4px solid #17a2b8;padding:1rem;margin:0.5rem 0;border-radius:4px}
.success-box{background-color:#d4edda;border-left:4px solid #28a745;padding:1rem;margin:0.5rem 0;border-radius:4px}
.info-box{background-color:#e7f3ff;border-left:4px solid #2196F3;padding:1rem;margin:0.5rem 0;border-radius:4px}
.warning-banner{background-color:#fff3cd;border:2px solid #ffc107;padding:1rem;margin:1rem 0;border-radius:8px;text-align:center;font-weight:bold}
</style>
""", unsafe_allow_html=True)

# Initialize session state
for key in ['tb_data', 'gl_data', 'tb_cleaned', 'gl_cleaned', 'tb_issues', 'gl_issues',
            'issue_selections', 'financial_data', 'changes_log', 'excel_output', 'pdf_output',
            'validation_complete', 'model_generated', 'unit_selection', 'has_tb', 'has_gl']:
    if key not in st.session_state:
        if key in ['tb_issues', 'gl_issues', 'changes_log']:
            st.session_state[key] = []
        elif key == 'issue_selections':
            st.session_state[key] = {}
        elif key == 'unit_selection':
            st.session_state[key] = 'USD dollars'
        elif key in ['has_tb', 'has_gl']:
            st.session_state[key] = False
        else:
            st.session_state[key] = None

for key in ['validation_complete', 'model_generated']:
    if key not in st.session_state:
        st.session_state[key] = False

# Currency conversion
EXCHANGE_RATES = {
    'USD': 1.0, 'EUR': 1.08, 'GBP': 1.27, 'JPY': 0.0067, 'CNY': 0.14,
    'CAD': 0.71, 'AUD': 0.64, 'CHF': 1.13, 'INR': 0.012, 'MXN': 0.058
}

def detect_currency(df):
    """Detect currency from DataFrame"""
    if 'Currency' in df.columns and not df['Currency'].isna().all():
        return df['Currency'].mode()[0]
    return 'USD'

def convert_to_usd(df):
    """Convert amounts to USD"""
    df = df.copy()
    src_currency = detect_currency(df)
    
    if src_currency != 'USD':
        rate = EXCHANGE_RATES.get(src_currency, 1.0)
        for col in ['Amount', 'Debit', 'Credit']:
            if col in df.columns:
                df[col] = df[col] * rate
        st.info(f"💱 Converted from {src_currency} to USD (rate: {rate})")
    
    return df


def main():
    """Main application"""
    
    # Header
    st.title("📊 Three Statements Automation")
    st.markdown("**AI-Powered Financial Statement Generator**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Unit selection (REQUIRED)
        st.subheader("Data Unit")
        unit_selection = st.radio(
            "My GL amounts are in:",
            options=['USD dollars', 'USD thousands'],
            index=0 if st.session_state.unit_selection == 'USD dollars' else 1,
            help="Select the unit of your source data. The template uses USD thousands."
        )
        st.session_state.unit_selection = unit_selection
        
        # Calculate scale factor
        if unit_selection == 'USD dollars':
            unit_scale = 1000.0  # Divide by 1000 to convert to thousands
        else:
            unit_scale = 1.0  # Already in thousands
        
        st.markdown("---")
        
        # Sample data buttons
        st.subheader("📥 Sample Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Download Sample Model", use_container_width=True):
                try:
                    demo_path = get_template_path('demo')
                    with open(demo_path, 'rb') as f:
                        st.download_button(
                            label="⬇️ Download Demo Model",
                            data=f,
                            file_name="Financial_Model_SAMPLE_DEMO.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        with col2:
            if st.button("📊 Use Sample Data", use_container_width=True):
                try:
                    # Load sample TB and GL
                    st.session_state.tb_data = load_sample_tb()
                    st.session_state.gl_data = load_sample_gl(with_txnid=True)
                    st.session_state.has_tb = True
                    st.session_state.has_gl = True
                    st.success("✅ Sample data loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading sample data: {str(e)}")
        
        if st.button("🎲 Load Random Test Dataset", use_container_width=True):
            try:
                df, name = load_random_backup_gl()
                st.session_state.gl_data = df
                st.session_state.has_gl = True
                st.session_state.has_tb = False  # Backups are GL only
                st.info(f"📦 Loaded: {name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading random dataset: {str(e)}")
        
        st.markdown("---")
        
        # Info box
        st.info("""
        **Upload Tips:**
        
        ✅ **Best results:** Upload Trial Balance (ending balances) including both BS and P&L accounts.
        
        ⚠️ **GL Activity only:** Works well for Income Statement. Balance Sheet and Cash Flow may be incomplete.
        
        💡 **Required columns:** TxnDate, AccountNumber, AccountName, Debit, Credit
        
        🔧 **TransactionID:** Optional but recommended for better validation
        """)
    
    # Main content area
    
    # Upload section
    st.header("1️⃣ Upload Data")
    
    # Info box about workflow
    st.markdown("""
    <div class="info-box">
    <strong>📘 How to use:</strong><br>
    • Upload Trial Balance for complete 3-statement model (recommended)<br>
    • Upload GL Activity for transaction-level validation and Income Statement<br>
    • Upload both for best results
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Trial Balance (TB)")
        tb_file = st.file_uploader(
            "Upload Trial Balance CSV/Excel",
            type=['csv', 'xlsx'],
            key='tb_upload',
            help="Ending balances by account. Required for complete Balance Sheet and Cash Flow."
        )
        
        if tb_file:
            try:
                if tb_file.name.endswith('.csv'):
                    df = pd.read_csv(tb_file)
                else:
                    df = pd.read_excel(tb_file)
                
                df = normalize_column_headers(df)
                df = convert_to_usd(df)
                st.session_state.tb_data = df
                st.session_state.has_tb = True
                st.success(f"✅ Loaded {len(df)} Trial Balance entries")
                
                # Preview
                with st.expander("Preview TB Data"):
                    st.dataframe(df.head(10))
                
            except Exception as e:
                st.error(f"Error loading TB: {str(e)}")
    
    with col2:
        st.subheader("GL Activity")
        gl_file = st.file_uploader(
            "Upload GL Activity CSV/Excel",
            type=['csv', 'xlsx'],
            key='gl_upload',
            help="Transaction-level detail. Optional but recommended for validation."
        )
        
        if gl_file:
            try:
                if gl_file.name.endswith('.csv'):
                    df = pd.read_csv(gl_file)
                else:
                    df = pd.read_excel(gl_file)
                
                df = normalize_column_headers(df)
                df = convert_to_usd(df)
                st.session_state.gl_data = df
                st.session_state.has_gl = True
                st.success(f"✅ Loaded {len(df)} GL transactions")
                
                # Preview
                with st.expander("Preview GL Data"):
                    st.dataframe(df.head(10))
                
            except Exception as e:
                st.error(f"Error loading GL: {str(e)}")
    
    # Check what we have
    has_tb = st.session_state.has_tb and st.session_state.tb_data is not None
    has_gl = st.session_state.has_gl and st.session_state.gl_data is not None
    
    if not has_tb and not has_gl:
        st.info("👆 Please upload Trial Balance and/or GL Activity data to continue")
        return
    
    # Downgrade warning
    if has_gl and not has_tb:
        st.markdown("""
        <div class="warning-banner">
        ⚠️ DOWNGRADED MODE: Only GL Activity uploaded<br>
        Income Statement: ✅ Available<br>
        Balance Sheet: ⚠️ Incomplete (opening balances missing)<br>
        Cash Flow: ⚠️ Incomplete (Trial Balance required)
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Validation section
    st.header("2️⃣ Data Validation")
    
    all_issues = []
    
    # Validate TB if present
    if has_tb:
        st.subheader("Trial Balance Validation")
        tb_issues = validate_trial_balance(st.session_state.tb_data)
        tb_common_issues = validate_common_issues(st.session_state.tb_data)
        tb_issues.extend(tb_common_issues)
        st.session_state.tb_issues = tb_issues
        all_issues.extend(tb_issues)
        
        if tb_issues:
            st.warning(f"⚠️ Found {len(tb_issues)} issue(s) in Trial Balance")
            
            for i, issue in enumerate(tb_issues):
                severity_class = f"validation-{issue['severity'].lower()}"
                with st.expander(f"{issue['severity']}: {issue['issue']}", expanded=False):
                    st.markdown(f"**Impact:** {issue['impact']}")
                    st.markdown(f"**Suggestion:** {issue['suggestion']}")
                    
                    if 'sample_data' in issue and issue['sample_data'] is not None:
                        st.dataframe(issue['sample_data'])
                    
                    # Checkbox for auto-fix
                    if issue['auto_fix']:
                        key = f"tb_fix_{i}"
                        if key not in st.session_state.issue_selections:
                            st.session_state.issue_selections[key] = True
                        
                        st.session_state.issue_selections[key] = st.checkbox(
                            "Apply this fix",
                            value=st.session_state.issue_selections[key],
                            key=f"checkbox_{key}"
                        )
        else:
            st.success("✅ No issues found in Trial Balance")
    
    # Validate GL if present
    if has_gl:
        st.subheader("GL Activity Validation")
        gl_issues = validate_gl_activity(st.session_state.gl_data)
        gl_common_issues = validate_common_issues(st.session_state.gl_data)
        gl_issues.extend(gl_common_issues)
        st.session_state.gl_issues = gl_issues
        all_issues.extend(gl_issues)
        
        if gl_issues:
            st.warning(f"⚠️ Found {len(gl_issues)} issue(s) in GL Activity")
            
            for i, issue in enumerate(gl_issues):
                with st.expander(f"{issue['severity']}: {issue['issue']}", expanded=False):
                    st.markdown(f"**Impact:** {issue['impact']}")
                    st.markdown(f"**Suggestion:** {issue['suggestion']}")
                    
                    if 'sample_data' in issue and issue['sample_data'] is not None:
                        st.dataframe(issue['sample_data'])
                    
                    if issue['auto_fix']:
                        key = f"gl_fix_{i}"
                        if key not in st.session_state.issue_selections:
                            st.session_state.issue_selections[key] = True
                        
                        st.session_state.issue_selections[key] = st.checkbox(
                            "Apply this fix",
                            value=st.session_state.issue_selections[key],
                            key=f"checkbox_{key}"
                        )
        else:
            st.success("✅ No issues found in GL Activity")
    
    # Fix buttons
    if all_issues:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ Accept All Fixes", use_container_width=True):
                for key in st.session_state.issue_selections:
                    st.session_state.issue_selections[key] = True
                st.rerun()
        
        with col2:
            if st.button("❌ Decline All Fixes", use_container_width=True):
                for key in st.session_state.issue_selections:
                    st.session_state.issue_selections[key] = False
                st.rerun()
        
        with col3:
            if st.button("🔧 Apply Selected Fixes", type="primary", use_container_width=True):
                # Apply fixes to TB
                if has_tb and st.session_state.tb_issues:
                    selected_tb_fixes = []
                    for i, issue in enumerate(st.session_state.tb_issues):
                        if issue['auto_fix']:
                            key = f"tb_fix_{i}"
                            if st.session_state.issue_selections.get(key, False):
                                selected_tb_fixes.append(issue['auto_fix'])
                    
                    if selected_tb_fixes:
                        tb_cleaned, tb_changes = apply_auto_fixes(
                            st.session_state.tb_data,
                            selected_tb_fixes
                        )
                        st.session_state.tb_cleaned = tb_cleaned
                        st.session_state.changes_log.extend(
                            [f"TB: {change}" for change in tb_changes]
                        )
                
                # Apply fixes to GL
                if has_gl and st.session_state.gl_issues:
                    selected_gl_fixes = []
                    for i, issue in enumerate(st.session_state.gl_issues):
                        if issue['auto_fix']:
                            key = f"gl_fix_{i}"
                            if st.session_state.issue_selections.get(key, False):
                                selected_gl_fixes.append(issue['auto_fix'])
                    
                    if selected_gl_fixes:
                        gl_cleaned, gl_changes = apply_auto_fixes(
                            st.session_state.gl_data,
                            selected_gl_fixes
                        )
                        st.session_state.gl_cleaned = gl_cleaned
                        st.session_state.changes_log.extend(
                            [f"GL: {change}" for change in gl_changes]
                        )
                
                st.session_state.validation_complete = True
                st.success("✅ Fixes applied successfully!")
                
                if st.session_state.changes_log:
                    with st.expander("View Changes"):
                        for change in st.session_state.changes_log:
                            st.write(f"• {change}")
                
                st.rerun()
    else:
        # No issues, can proceed directly
        st.session_state.validation_complete = True
        st.session_state.tb_cleaned = st.session_state.tb_data
        st.session_state.gl_cleaned = st.session_state.gl_data
    
    st.markdown("---")
    
    # Generate financial model
    st.header("3️⃣ Generate Financial Model")
    
    if not st.session_state.validation_complete:
        st.info("Complete validation and apply fixes first")
        return
    
    if st.button("🚀 Generate 3-Statement Model", type="primary", use_container_width=True):
        with st.spinner("Generating financial statements..."):
            try:
                # Use TB data if available, otherwise GL
                data_to_use = st.session_state.tb_cleaned if has_tb else st.session_state.gl_cleaned
                
                if data_to_use is None:
                    st.error("No clean data available")
                    return
                
                # Map accounts
                mapped_data = map_accounts(data_to_use)
                
                # Get mapping stats
                mapping_stats = get_mapping_stats(mapped_data)
                
                # Calculate financial statements
                financial_data = calculate_financial_statements(
                    mapped_data,
                    is_trial_balance=has_tb
                )
                
                st.session_state.financial_data = financial_data
                st.session_state.model_generated = True
                
                # Generate Excel
                template_path = get_template_path('zero')
                excel_output = write_financial_data_to_template(
                    template_path,
                    financial_data,
                    unit_scale
                )
                st.session_state.excel_output = excel_output
                
                # Generate AI summary
                has_cash_flow = len(financial_data) >= 2 and has_tb
                ai_summary, used_ai = generate_ai_summary(
                    financial_data,
                    has_balance_sheet=has_tb,
                    has_cash_flow=has_cash_flow
                )
                
                # Generate PDF
                pdf_output = create_pdf_report(
                    financial_data,
                    ai_summary=ai_summary,
                    unit_label=st.session_state.unit_selection
                )
                st.session_state.pdf_output = pdf_output
                
                st.success("✅ Financial model generated successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error generating model: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Display results if generated
    if st.session_state.model_generated and st.session_state.financial_data:
        st.markdown("---")
        st.header("4️⃣ Results")
        
        financial_data = st.session_state.financial_data
        years = sorted(financial_data.keys())
        
        # Income Statement
        st.subheader("📈 Income Statement")
        is_data = []
        for year in years:
            data = financial_data[year]
            is_data.append({
                'Year': year,
                'Revenue': data.get('revenue', 0),
                'COGS': data.get('cogs', 0),
                'Gross Profit': data.get('revenue', 0) - data.get('cogs', 0),
                'Operating Expenses': sum([data.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 'research_dev', 'depreciation_expense']]),
                'Net Income': data.get('revenue', 0) - data.get('cogs', 0) - sum([data.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 'research_dev', 'depreciation_expense', 'interest_expense', 'tax_expense']])
            })
        st.dataframe(pd.DataFrame(is_data), use_container_width=True)
        
        # Balance Sheet (if TB available)
        if has_tb:
            st.subheader("💰 Balance Sheet")
            bs_data = []
            for year in years:
                data = financial_data[year]
                bs_data.append({
                    'Year': year,
                    'Total Assets': sum([data.get(k, 0) for k in ['cash', 'accounts_receivable', 'inventory', 'prepaid_expenses', 'other_current_assets', 'ppe_gross']]) - data.get('accumulated_depreciation', 0),
                    'Total Liabilities': sum([data.get(k, 0) for k in ['accounts_payable', 'accrued_payroll', 'deferred_revenue', 'interest_payable', 'other_current_liabilities', 'income_taxes_payable', 'long_term_debt']]),
                    'Total Equity': sum([data.get(k, 0) for k in ['common_stock', 'retained_earnings']])
                })
            st.dataframe(pd.DataFrame(bs_data), use_container_width=True)
        else:
            st.info("⚠️ Balance Sheet incomplete (Trial Balance not provided)")
        
        # Cash Flow (if multi-year TB)
        if has_tb and len(years) >= 2:
            st.subheader("💵 Cash Flow Statement")
            st.info("Cash Flow Statement generated using GAAP indirect method")
        else:
            st.info("⚠️ Cash Flow Statement requires multi-year Trial Balance data")
        
        # Downloads
        st.markdown("---")
        st.subheader("📥 Download Reports")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.excel_output:
                st.download_button(
                    label="📊 Download Excel Model",
                    data=st.session_state.excel_output,
                    file_name=f"Financial_Model_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col2:
            if st.session_state.pdf_output:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=st.session_state.pdf_output,
                    file_name=f"Financial_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p><strong>⚠️ Early Demo Notice</strong></p>
    <p>This is an early-stage demo built as part of a self-learning experiment.</p>
    <p>For educational purposes only - not intended for production use.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
