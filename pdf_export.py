"""
PDF Export Module
Generates professional PDF reports with complete 3-statement financials
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, 
                                TableStyle, PageBreak, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io
from typing import Dict, List, Optional


def create_pdf_report(financial_data: Dict[int, Dict],
                     ai_summary: Optional[str] = None,
                     company_name: str = "Sample Company",
                     unit_label: str = "USD thousands") -> io.BytesIO:
    """
    Create comprehensive PDF report with all three statements
    
    Args:
        financial_data: Dict of {year: {line_item: value}}
        ai_summary: Optional AI-generated summary text
        company_name: Name to display in report
        unit_label: Unit label (e.g., "USD thousands")
    
    Returns:
        BytesIO containing PDF file
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           topMargin=0.75*inch, bottomMargin=0.75*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    # Title
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph(f"Financial Statements ({unit_label})", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Get years (exclude internal Year0 opening balances)
    all_years = sorted(financial_data.keys())
    years = all_years[1:] if len(all_years) > 1 else all_years
    
    # Income Statement
    elements.append(Paragraph("Income Statement", section_style))
    is_table = create_income_statement_table(financial_data, years)
    elements.append(is_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Balance Sheet
    elements.append(Paragraph("Balance Sheet", section_style))
    bs_table = create_balance_sheet_table(financial_data, years)
    elements.append(bs_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Cash Flow Statement
    if len(years) >= 1:
        elements.append(Paragraph("Cash Flow Statement", section_style))
        cf_table = create_cash_flow_table(financial_data, years)
        elements.append(cf_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # AI Summary (if provided)
    if ai_summary:
        elements.append(PageBreak())
        elements.append(Paragraph("AI-Generated Summary & Insights", section_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Split summary into paragraphs
        for para in ai_summary.split('\n\n'):
            if para.strip():
                elements.append(Paragraph(para.strip(), styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def create_income_statement_table(financial_data: Dict[int, Dict], 
                                   years: List[int]) -> Table:
    """Create Income Statement table"""
    
    # Header row
    header = ['', *[str(year) for year in years]]
    
    # Data rows
    data = [header]
    
    # Add line items
    line_items = [
        ('Revenues', 'revenue'),
        ('Cost of Goods Sold', 'cogs'),
        ('Gross Profit', lambda d: d['revenue'] - d['cogs']),
        ('', None),  # Blank row
        ('Operating Expenses:', None),
        ('  Distribution Expenses', 'distribution_expenses'),
        ('  Marketing and Administration', 'marketing_admin'),
        ('  Research and Development', 'research_dev'),
        ('  Depreciation', 'depreciation_expense'),
        ('Total Operating Expenses', lambda d: (d.get('distribution_expenses', 0) + 
                                                 d.get('marketing_admin', 0) + 
                                                 d.get('research_dev', 0) + 
                                                 d.get('depreciation_expense', 0))),
        ('', None),
        ('EBIT (Operating Profit)', lambda d: (d['revenue'] - d['cogs'] - 
                                               (d.get('distribution_expenses', 0) + 
                                                d.get('marketing_admin', 0) + 
                                                d.get('research_dev', 0) + 
                                                d.get('depreciation_expense', 0)))),
        ('Interest Expense', 'interest_expense'),
        ('Income Before Taxes', lambda d: (d['revenue'] - d['cogs'] - 
                                           (d.get('distribution_expenses', 0) + 
                                            d.get('marketing_admin', 0) + 
                                            d.get('research_dev', 0) + 
                                            d.get('depreciation_expense', 0)) - 
                                           d.get('interest_expense', 0))),
        ('Income Tax Expense', 'tax_expense'),
        ('Net Income', lambda d: (d['revenue'] - d['cogs'] - 
                                 (d.get('distribution_expenses', 0) + 
                                  d.get('marketing_admin', 0) + 
                                  d.get('research_dev', 0) + 
                                  d.get('depreciation_expense', 0)) - 
                                 d.get('interest_expense', 0) - 
                                 d.get('tax_expense', 0))),
    ]
    
    for label, key in line_items:
        row = [label]
        for year in years:
            if key is None:
                row.append('')
            elif callable(key):
                try:
                    value = key(financial_data[year])
                    row.append(f'{value:,.1f}')
                except:
                    row.append('—')
            else:
                value = financial_data[year].get(key, 0)
                row.append(f'{value:,.1f}')
        data.append(row)
    
    # Create table
    table = Table(data, colWidths=[3*inch] + [1.2*inch]*len(years))
    
    # Style
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        # Bold for totals
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    return table


def create_balance_sheet_table(financial_data: Dict[int, Dict], 
                               years: List[int]) -> Table:
    """Create Balance Sheet table"""
    
    header = ['', *[str(year) for year in years]]
    data = [header]
    
    line_items = [
        ('ASSETS', None),
        ('Current Assets:', None),
        ('  Cash', 'cash'),
        ('  Accounts Receivable', 'accounts_receivable'),
        ('  Inventory', 'inventory'),
        ('  Prepaid Expenses', 'prepaid_expenses'),
        ('  Other Current Assets', 'other_current_assets'),
        ('Total Current Assets', lambda d: (d.get('cash', 0) + 
                                           d.get('accounts_receivable', 0) + 
                                           d.get('inventory', 0) + 
                                           d.get('prepaid_expenses', 0) + 
                                           d.get('other_current_assets', 0))),
        ('', None),
        ('Non-Current Assets:', None),
        ('  Property, Plant & Equipment - Gross', 'ppe_gross'),
        ('  Less: Accumulated Depreciation', lambda d: -d.get('accumulated_depreciation', 0)),
        ('  Property, Plant & Equipment - Net', lambda d: (d.get('ppe_gross', 0) - 
                                                           d.get('accumulated_depreciation', 0))),
        ('TOTAL ASSETS', lambda d: (d.get('cash', 0) + d.get('accounts_receivable', 0) + 
                                   d.get('inventory', 0) + d.get('prepaid_expenses', 0) + 
                                   d.get('other_current_assets', 0) + d.get('ppe_gross', 0) - 
                                   d.get('accumulated_depreciation', 0))),
        ('', None),
        ('LIABILITIES AND EQUITY', None),
        ('Current Liabilities:', None),
        ('  Accounts Payable', 'accounts_payable'),
        ('  Accrued Payroll', 'accrued_payroll'),
        ('  Deferred Revenue', 'deferred_revenue'),
        ('  Interest Payable', 'interest_payable'),
        ('  Other Current Liabilities', 'other_current_liabilities'),
        ('  Income Taxes Payable', 'income_taxes_payable'),
        ('Total Current Liabilities', lambda d: (d.get('accounts_payable', 0) + 
                                                d.get('accrued_payroll', 0) + 
                                                d.get('deferred_revenue', 0) + 
                                                d.get('interest_payable', 0) + 
                                                d.get('other_current_liabilities', 0) + 
                                                d.get('income_taxes_payable', 0))),
        ('', None),
        ('Non-Current Liabilities:', None),
        ('  Long-Term Debt', 'long_term_debt'),
        ('', None),
        ('Shareholders\' Equity:', None),
        ('  Common Stock and APIC', 'common_stock'),
        ('  Retained Earnings', 'retained_earnings'),
        ('Total Shareholders\' Equity', lambda d: (d.get('common_stock', 0) + 
                                                   d.get('retained_earnings', 0))),
        ('', None),
        ('TOTAL LIABILITIES AND EQUITY', lambda d: (d.get('accounts_payable', 0) + 
                                                   d.get('accrued_payroll', 0) + 
                                                   d.get('deferred_revenue', 0) + 
                                                   d.get('interest_payable', 0) + 
                                                   d.get('other_current_liabilities', 0) + 
                                                   d.get('income_taxes_payable', 0) + 
                                                   d.get('long_term_debt', 0) + 
                                                   d.get('common_stock', 0) + 
                                                   d.get('retained_earnings', 0))),
    ]
    
    for label, key in line_items:
        row = [label]
        for year in years:
            if key is None:
                row.append('')
            elif callable(key):
                try:
                    value = key(financial_data[year])
                    row.append(f'{value:,.1f}')
                except:
                    row.append('—')
            else:
                value = financial_data[year].get(key, 0)
                row.append(f'{value:,.1f}')
        data.append(row)
    
    table = Table(data, colWidths=[3*inch] + [1.2*inch]*len(years))
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    return table


def create_cash_flow_table(financial_data: Dict[int, Dict], 
                           years: List[int]) -> Table:
    """Create Cash Flow Statement table (indirect method)"""
    
    header = ['', *[str(year) for year in years]]
    data = [header]
    
    line_items = [
        ('Operating Activities:', None),
        ('  Net Income', lambda d: (d['revenue'] - d['cogs'] - 
                                   (d.get('distribution_expenses', 0) + 
                                    d.get('marketing_admin', 0) + 
                                    d.get('research_dev', 0) + 
                                    d.get('depreciation_expense', 0)) - 
                                   d.get('interest_expense', 0) - 
                                   d.get('tax_expense', 0))),
        ('  Depreciation', 'depreciation_expense'),
        ('  Change in Accounts Receivable', 'delta_ar'),
        ('  Change in Inventory', 'delta_inventory'),
        ('  Change in Prepaid Expenses', 'delta_prepaid'),
        ('  Change in Other Current Assets', 'delta_other_current_assets'),
        ('  Change in Accounts Payable', 'delta_ap'),
        ('  Change in Accrued Payroll', 'delta_accrued_payroll'),
        ('  Change in Deferred Revenue', 'delta_deferred_revenue'),
        ('  Change in Interest Payable', 'delta_interest_payable'),
        ('  Change in Other Current Liabilities', 'delta_other_current_liabilities'),
        ('  Change in Income Taxes Payable', 'delta_income_taxes_payable'),
        ('Cash from Operating Activities', lambda d: sum([
            d['revenue'] - d['cogs'] - (d.get('distribution_expenses', 0) + 
                                       d.get('marketing_admin', 0) + 
                                       d.get('research_dev', 0) + 
                                       d.get('depreciation_expense', 0)) - 
            d.get('interest_expense', 0) - d.get('tax_expense', 0),
            d.get('depreciation_expense', 0),
            d.get('delta_ar', 0),
            d.get('delta_inventory', 0),
            d.get('delta_prepaid', 0),
            d.get('delta_other_current_assets', 0),
            d.get('delta_ap', 0),
            d.get('delta_accrued_payroll', 0),
            d.get('delta_deferred_revenue', 0),
            d.get('delta_interest_payable', 0),
            d.get('delta_other_current_liabilities', 0),
            d.get('delta_income_taxes_payable', 0),
        ])),
        ('', None),
        ('Investing Activities:', None),
        ('  Acquisitions of PP&E', 'capex'),
        ('Cash from Investing Activities', 'capex'),
        ('', None),
        ('Financing Activities:', None),
        ('  Issuance of Common Stock', 'stock_issuance'),
        ('  Dividends', lambda d: -d.get('dividends', 0)),
        ('  Change in Long-Term Debt', 'delta_debt'),
        ('Cash from Financing Activities', lambda d: (d.get('stock_issuance', 0) - 
                                                     d.get('dividends', 0) + 
                                                     d.get('delta_debt', 0))),
    ]
    
    for label, key in line_items:
        row = [label]
        for year in years:
            if key is None:
                row.append('')
            elif callable(key):
                try:
                    value = key(financial_data[year])
                    row.append(f'{value:,.1f}')
                except:
                    row.append('—')
            else:
                value = financial_data[year].get(key, 0)
                row.append(f'{value:,.1f}' if value != 0 else '—')
        data.append(row)
    
    table = Table(data, colWidths=[3*inch] + [1.2*inch]*len(years))
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('FONTNAME', (0, 13), (-1, 13), 'Helvetica-Bold'),
        ('LINEABOVE', (0, 13), (-1, 13), 1, colors.black),
    ]))
    
    return table
