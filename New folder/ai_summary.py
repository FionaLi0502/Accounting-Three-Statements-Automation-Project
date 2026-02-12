"""
AI Summary Module
Generates financial insights using AI or rule-based fallback
"""

import os
from typing import Dict, Optional, Tuple
import pandas as pd


def generate_rule_based_summary(financial_data: Dict[int, Dict],
                                has_balance_sheet: bool = True,
                                has_cash_flow: bool = True) -> str:
    """
    Generate rule-based summary when AI is unavailable
    
    Args:
        financial_data: Dict of {year: {line_item: value}}
        has_balance_sheet: Whether balance sheet is available
        has_cash_flow: Whether cash flow is available
    
    Returns:
        Summary text
    """
    years = sorted(financial_data.keys())
    
    summary_parts = []
    
    # Executive Summary
    summary_parts.append("📊 FINANCIAL SUMMARY\n")
    summary_parts.append("=" * 60)
    
    # Income Statement Analysis (always available)
    if len(years) >= 1:
        latest_year = years[-1]
        latest = financial_data[latest_year]
        
        revenue = latest.get('revenue', 0)
        gross_profit = revenue - latest.get('cogs', 0)
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
        
        total_opex = sum([
            latest.get('distribution_expenses', 0),
            latest.get('marketing_admin', 0),
            latest.get('research_dev', 0),
            latest.get('depreciation_expense', 0)
        ])
        ebit = gross_profit - total_opex
        ebit_margin = (ebit / revenue * 100) if revenue > 0 else 0
        
        net_income = ebit - latest.get('interest_expense', 0) - latest.get('tax_expense', 0)
        net_margin = (net_income / revenue * 100) if revenue > 0 else 0
        
        summary_parts.append(f"\n\n📈 INCOME STATEMENT ({latest_year})")
        summary_parts.append(f"Revenue: ${revenue:,.0f}")
        summary_parts.append(f"Gross Margin: {gross_margin:.1f}%")
        summary_parts.append(f"EBIT Margin: {ebit_margin:.1f}%")
        summary_parts.append(f"Net Margin: {net_margin:.1f}%")
        summary_parts.append(f"Net Income: ${net_income:,.0f}")
    
    # Trend Analysis (if multi-year)
    if len(years) >= 2:
        first_year = years[0]
        latest_year = years[-1]
        
        rev_first = financial_data[first_year].get('revenue', 0)
        rev_latest = financial_data[latest_year].get('revenue', 0)
        rev_growth = ((rev_latest / rev_first - 1) * 100) if rev_first > 0 else 0
        
        ni_first = (financial_data[first_year].get('revenue', 0) - 
                   financial_data[first_year].get('cogs', 0) - 
                   sum([financial_data[first_year].get(k, 0) for k in 
                       ['distribution_expenses', 'marketing_admin', 'research_dev', 
                        'depreciation_expense', 'interest_expense', 'tax_expense']]))
        ni_latest = (financial_data[latest_year].get('revenue', 0) - 
                    financial_data[latest_year].get('cogs', 0) - 
                    sum([financial_data[latest_year].get(k, 0) for k in 
                        ['distribution_expenses', 'marketing_admin', 'research_dev', 
                         'depreciation_expense', 'interest_expense', 'tax_expense']]))
        ni_growth = ((ni_latest / ni_first - 1) * 100) if ni_first > 0 else 0
        
        summary_parts.append(f"\n\n📊 TREND ANALYSIS ({first_year} to {latest_year})")
        summary_parts.append(f"Revenue Growth: {rev_growth:+.1f}%")
        summary_parts.append(f"Net Income Growth: {ni_growth:+.1f}%")
    
    # Balance Sheet Analysis (if available)
    if has_balance_sheet and len(years) >= 1:
        latest_year = years[-1]
        latest = financial_data[latest_year]
        
        total_assets = sum([
            latest.get('cash', 0),
            latest.get('accounts_receivable', 0),
            latest.get('inventory', 0),
            latest.get('prepaid_expenses', 0),
            latest.get('other_current_assets', 0),
            latest.get('ppe_gross', 0),
            -latest.get('accumulated_depreciation', 0)
        ])
        
        total_liab = sum([
            latest.get('accounts_payable', 0),
            latest.get('accrued_payroll', 0),
            latest.get('deferred_revenue', 0),
            latest.get('interest_payable', 0),
            latest.get('other_current_liabilities', 0),
            latest.get('income_taxes_payable', 0),
            latest.get('long_term_debt', 0)
        ])
        
        total_equity = sum([
            latest.get('common_stock', 0),
            latest.get('retained_earnings', 0)
        ])
        
        debt_to_equity = (total_liab / total_equity) if total_equity > 0 else 0
        
        summary_parts.append(f"\n\n💰 BALANCE SHEET ({latest_year})")
        summary_parts.append(f"Total Assets: ${total_assets:,.0f}")
        summary_parts.append(f"Total Liabilities: ${total_liab:,.0f}")
        summary_parts.append(f"Total Equity: ${total_equity:,.0f}")
        summary_parts.append(f"Debt-to-Equity Ratio: {debt_to_equity:.2f}x")
    
    # Cash Flow Analysis (if available and multi-year)
    if has_cash_flow and len(years) >= 2:
        latest_year = years[-1]
        latest = financial_data[latest_year]
        
        cfo = sum([
            latest.get('revenue', 0) - latest.get('cogs', 0) - 
            sum([latest.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 
                                            'research_dev', 'depreciation_expense', 
                                            'interest_expense', 'tax_expense']]),
            latest.get('depreciation_expense', 0),
            latest.get('delta_ar', 0),
            latest.get('delta_inventory', 0),
            latest.get('delta_prepaid', 0),
            latest.get('delta_other_current_assets', 0),
            latest.get('delta_ap', 0),
            latest.get('delta_accrued_payroll', 0),
            latest.get('delta_deferred_revenue', 0),
            latest.get('delta_interest_payable', 0),
            latest.get('delta_other_current_liabilities', 0),
            latest.get('delta_income_taxes_payable', 0),
        ])
        
        cfi = latest.get('capex', 0)
        cff = (latest.get('stock_issuance', 0) - latest.get('dividends', 0) + 
              latest.get('delta_debt', 0))
        
        summary_parts.append(f"\n\n💵 CASH FLOW ({latest_year})")
        summary_parts.append(f"Operating Cash Flow: ${cfo:,.0f}")
        summary_parts.append(f"Investing Cash Flow: ${cfi:,.0f}")
        summary_parts.append(f"Financing Cash Flow: ${cff:,.0f}")
    
    # Recommendations
    summary_parts.append("\n\n💡 KEY OBSERVATIONS")
    
    if len(years) >= 1:
        latest_year = years[-1]
        latest = financial_data[latest_year]
        
        # Profitability
        revenue = latest.get('revenue', 0)
        net_income = (revenue - latest.get('cogs', 0) - 
                     sum([latest.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 
                                                     'research_dev', 'depreciation_expense', 
                                                     'interest_expense', 'tax_expense']]))
        net_margin = (net_income / revenue * 100) if revenue > 0 else 0
        
        if net_margin > 15:
            summary_parts.append("✓ Strong profitability with healthy margins")
        elif net_margin > 5:
            summary_parts.append("• Moderate profitability - room for improvement")
        else:
            summary_parts.append("⚠ Low profitability - review cost structure")
        
        # Leverage
        if has_balance_sheet:
            total_liab = sum([latest.get(k, 0) for k in 
                            ['accounts_payable', 'accrued_payroll', 'deferred_revenue', 
                             'interest_payable', 'other_current_liabilities', 
                             'income_taxes_payable', 'long_term_debt']])
            total_equity = sum([latest.get(k, 0) for k in ['common_stock', 'retained_earnings']])
            debt_to_equity = (total_liab / total_equity) if total_equity > 0 else 0
            
            if debt_to_equity < 1:
                summary_parts.append("✓ Conservative leverage position")
            elif debt_to_equity < 2:
                summary_parts.append("• Moderate leverage - monitor debt levels")
            else:
                summary_parts.append("⚠ High leverage - consider deleveraging")
    
    # Data quality note
    if not has_balance_sheet:
        summary_parts.append("\n\n⚠️ NOTE: Balance Sheet data unavailable (Trial Balance not provided)")
    if not has_cash_flow:
        summary_parts.append("⚠️ NOTE: Cash Flow Statement incomplete (requires multi-year data)")
    
    summary_parts.append("\n\n" + "=" * 60)
    summary_parts.append("Generated by Rule-Based Analysis Engine")
    
    return "\n".join(summary_parts)


def generate_ai_summary(financial_data: Dict[int, Dict],
                       has_balance_sheet: bool = True,
                       has_cash_flow: bool = True,
                       api_key: Optional[str] = None) -> Tuple[str, bool]:
    """
    Generate AI-powered summary using Anthropic Claude
    
    Args:
        financial_data: Dict of {year: {line_item: value}}
        has_balance_sheet: Whether balance sheet is available
        has_cash_flow: Whether cash flow is available
        api_key: Anthropic API key
    
    Returns:
        (summary_text, used_ai_flag)
    """
    # Try to get API key
    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    # Fall back to rule-based if no API key
    if not api_key:
        return generate_rule_based_summary(financial_data, has_balance_sheet, has_cash_flow), False
    
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=api_key)
        
        # Prepare financial data summary
        years = sorted(financial_data.keys())
        
        # Build context
        context = "Financial Data:\n\n"
        
        for year in years:
            data = financial_data[year]
            context += f"{year}:\n"
            context += f"  Revenue: ${data.get('revenue', 0):,.0f}\n"
            context += f"  COGS: ${data.get('cogs', 0):,.0f}\n"
            context += f"  Operating Expenses: ${sum([data.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 'research_dev', 'depreciation_expense']]):,.0f}\n"
            context += f"  Net Income: ${data.get('revenue', 0) - data.get('cogs', 0) - sum([data.get(k, 0) for k in ['distribution_expenses', 'marketing_admin', 'research_dev', 'depreciation_expense', 'interest_expense', 'tax_expense']]):,.0f}\n"
            
            if has_balance_sheet:
                context += f"  Total Assets: ${sum([data.get(k, 0) for k in ['cash', 'accounts_receivable', 'inventory', 'prepaid_expenses', 'other_current_assets', 'ppe_gross']]) - data.get('accumulated_depreciation', 0):,.0f}\n"
                context += f"  Total Debt: ${data.get('long_term_debt', 0):,.0f}\n"
            
            context += "\n"
        
        # Add data availability notes
        context += f"\nData Availability:\n"
        context += f"- Balance Sheet: {'Available' if has_balance_sheet else 'NOT AVAILABLE (TB missing)'}\n"
        context += f"- Cash Flow: {'Available' if has_cash_flow else 'INCOMPLETE (single year or TB missing)'}\n"
        
        # Call Claude
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""You are a financial analyst. Analyze this financial data and provide:

1. Executive Summary (2-3 sentences)
2. Key Trends (revenue, profitability)
3. Financial Health Assessment
4. Recommendations (2-3 actionable items)

IMPORTANT: Only analyze statements that are marked as "Available". Do NOT make assumptions about missing data.

{context}

Provide concise, professional analysis suitable for a management report."""
            }]
        )
        
        ai_summary = message.content[0].text
        
        # Add disclaimer about data limitations
        if not has_balance_sheet or not has_cash_flow:
            disclaimer = "\n\n⚠️ NOTE: "
            if not has_balance_sheet:
                disclaimer += "Balance Sheet analysis limited (Trial Balance not provided). "
            if not has_cash_flow:
                disclaimer += "Cash Flow analysis incomplete (requires multi-year Trial Balance). "
            ai_summary += disclaimer
        
        return ai_summary, True
        
    except Exception as e:
        # Fall back to rule-based on any error
        fallback = generate_rule_based_summary(financial_data, has_balance_sheet, has_cash_flow)
        error_note = f"\n\n⚠️ AI summary unavailable ({str(e)}). Using rule-based analysis."
        return fallback + error_note, False


def summarize_validation_issues(issues: list) -> str:
    """
    Summarize validation issues for inclusion in reports
    
    Args:
        issues: List of validation issue dicts
    
    Returns:
        Summary text
    """
    if not issues:
        return "✓ No data quality issues detected."
    
    summary = f"⚠️ {len(issues)} data quality issue(s) detected:\n\n"
    
    for issue in issues:
        severity_emoji = {
            'Critical': '🔴',
            'Warning': '🟡',
            'Info': 'ℹ️'
        }.get(issue.get('severity', 'Info'), 'ℹ️')
        
        summary += f"{severity_emoji} {issue.get('issue', 'Unknown issue')}\n"
    
    return summary
