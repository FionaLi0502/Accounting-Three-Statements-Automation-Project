"""Three Statements Automation (v6) - Streamlit App"""

import streamlit as st
import pandas as pd
import openpyxl

from validation import validate_trial_balance, validate_gl_activity, apply_auto_fixes
from mapping import map_accounts
from excel_writer import write_financial_data_to_template, calculate_financial_statements, calculate_3statements_from_tb_gl
from sample_data import load_sample_tb, load_sample_gl, load_random_backup_gl, load_random_backup_tb, get_template_path
from pdf_export import create_pdf_report

st.set_page_config(page_title="3-Statement Generator (v6)", layout="wide")

st.title("3-Statement Generator (v6)")
st.caption("Upload a Trial Balance (BS snapshot) and/or GL activity (IS activity). The app validates, maps, and generates Excel + PDF.")

ALL_AUTO_FIXES = ["fix_account_numbers", "remove_missing_dates", "remove_future_dates", "remove_duplicates", "map_unclassified"]

with st.sidebar:
    st.header("Demo data")
    if st.button("Load Sample TB (BS-only)"):
        st.session_state['tb_df'] = load_sample_tb()
    if st.button("Load Sample GL (with TxnID)"):
        st.session_state['gl_df'] = load_sample_gl(with_txnid=True)
    if st.button("Load Random Backup TB (3 years)"):
        df, name = load_random_backup_tb()
        st.session_state['tb_df'] = df
        st.session_state['tb_name'] = name
    if st.button("Load Random Backup GL (3 years)"):
        df, name = load_random_backup_gl()
        st.session_state['gl_df'] = df
        st.session_state['gl_name'] = name

    st.divider()
    st.header("Template")
    template_choice = st.selectbox("Excel template", ["ZERO (processing)", "SAMPLE (demo)"])
    template_type = 'zero' if template_choice.startswith('ZERO') else 'demo'

    st.divider()
    unit_scale = st.number_input("Unit scale (divide by)", value=1000.0, help="Template is in USD thousands by default. If your data is in USD, use 1000.")

    st.divider()
    strict_mode = st.checkbox("Strict mode", value=True, help="Strict mode enforces required accounts/categories for realistic 3-statement output.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Trial Balance (BS snapshot)")
    tb_file = st.file_uploader("Upload TB CSV", type=["csv"], key="tb_upload")
    if tb_file is not None:
        st.session_state['tb_df'] = pd.read_csv(tb_file)
    tb_df = st.session_state.get('tb_df')
    if tb_df is not None:
        st.dataframe(tb_df.head(20), use_container_width=True)

with col2:
    st.subheader("GL Activity (IS activity)")
    gl_file = st.file_uploader("Upload GL CSV", type=["csv"], key="gl_upload")
    if gl_file is not None:
        st.session_state['gl_df'] = pd.read_csv(gl_file)
    gl_df = st.session_state.get('gl_df')
    if gl_df is not None:
        st.dataframe(gl_df.head(20), use_container_width=True)

st.divider()

REQUIRED_TB_CATEGORIES = {
    'cash','accounts_receivable','inventory','prepaid_expenses','other_current_assets',
    'ppe_gross','accumulated_depreciation',
    'accounts_payable','accrued_payroll','deferred_revenue','other_current_liabilities',
    'long_term_debt','common_stock','retained_earnings'
}

REQUIRED_GL_CATEGORIES = {
    'revenue','cogs','distribution_expenses','marketing_admin','research_dev',
    'depreciation_expense','interest_expense'
}

def strict_category_check(mapped_df: pd.DataFrame, required: set, dataset_name: str):
    present = set(mapped_df['FSLI_Category'].dropna().unique())
    missing = sorted(list(required - present))
    if missing:
        return [f"{dataset_name}: missing required categories: {', '.join(missing)}"]
    return []

if st.button("Generate 3-Statement Outputs", type="primary"):
    if tb_df is None and gl_df is None:
        st.error("Please upload at least one dataset (TB and/or GL).")
        st.stop()

    # Auto-fix common issues
    if tb_df is not None:
        tb_df = apply_auto_fixes(tb_df, selected_fixes=ALL_AUTO_FIXES)
    if gl_df is not None:
        gl_df = apply_auto_fixes(gl_df, selected_fixes=ALL_AUTO_FIXES)

    # Validate basic structure
    issues = []
    if tb_df is not None:
        for it in validate_trial_balance(tb_df):
            issues.append(f"TB [{it.get('severity','')}]: {it.get('issue','')}")
    if gl_df is not None:
        for it in validate_gl_activity(gl_df):
            issues.append(f"GL [{it.get('severity','')}]: {it.get('issue','')}")

    if issues:
        st.error("Validation issues found:\n" + "\n".join(issues))
        st.stop()
# Mapping
    tb_mapped = map_accounts(tb_df) if tb_df is not None else None
    gl_mapped = map_accounts(gl_df) if gl_df is not None else None

    if strict_mode:
        if tb_mapped is not None:
            issues += strict_category_check(tb_mapped, REQUIRED_TB_CATEGORIES, "TB")
        if gl_mapped is not None:
            issues += strict_category_check(gl_mapped, REQUIRED_GL_CATEGORIES, "GL")

        # Year 0 opening snapshot requirement (TB must include prior-year year-end for opening balances)
        if tb_df is not None:
            try:
                from validation import validate_year0_opening_snapshot
                issues += validate_year0_opening_snapshot(tb_df, statement_years=3)
            except Exception as e:
                issues += [f"TB: Year0 opening check error: {str(e)}"]

        if issues:
            st.error("Strict-mode checks failed:
" + "
".join(issues))
            st.stop()


    # Calculate financial data
    if tb_mapped is not None and gl_mapped is not None:
        financial_data = calculate_3statements_from_tb_gl(tb_mapped, gl_mapped)
    elif tb_mapped is not None:
        financial_data = calculate_financial_statements(tb_mapped, is_trial_balance=True)
    else:
        financial_data = calculate_financial_statements(gl_mapped, is_trial_balance=False)

    # Internal reconciliation checks (do not rely on Excel recalculation)
    try:
        from excel_writer import compute_reconciliation_checks
        checks = compute_reconciliation_checks(financial_data)
        bad = {y: v for y, v in checks.items() if abs(v.get('balance_sheet_check', 0.0)) > 0.01 or abs(v.get('cashflow_check', 0.0)) > 0.01}
        if bad:
            st.warning("Reconciliation checks failed (pre-Excel):\n" + "\n".join(
                [f"{y}: BS_check={vals['balance_sheet_check']:.2f}, Cash_check={vals['cashflow_check']:.2f}" for y, vals in bad.items()]
            ))
        else:
            st.success("Reconciliation checks passed (pre-Excel): BS + Cash checks are ~0 for all statement years.")
    except Exception as e:
        st.warning(f"Could not compute reconciliation checks: {str(e)}")

    years = sorted(financial_data.keys())
    template_path = get_template_path(template_type=template_type)

    # Excel + PDF
    excel_bytes = write_financial_data_to_template(template_path, financial_data, unit_scale=unit_scale)
    pdf_bytes = create_pdf_report(financial_data)

    st.success("Generated outputs for years: " + ", ".join(str(y) for y in years))

    st.download_button(
        label="Download Excel",
        data=excel_bytes.getvalue(),
        file_name=f"3statement_output_v6_{years[0]}_{years[-1]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        label="Download PDF",
        data=pdf_bytes.getvalue(),
        file_name=f"3statement_output_v6_{years[0]}_{years[-1]}.pdf",
        mime="application/pdf"
    )

    # Show template check cells for the first year column
    try:
        wb = openpyxl.load_workbook(excel_bytes, data_only=True)
        ws = wb.active
        bs_checks = {col: ws[f'{col}3'].value for col in ['B','C','D']}
        cf_checks = {col: ws[f'{col}81'].value for col in ['B','C','D']}
        st.info(f"Template checks: BS Check (B/C/D)={bs_checks} | Cash Check (B/C/D)={cf_checks} (should be 0)")
    except Exception:
        pass
