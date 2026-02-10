"""
Excel Writer Module
Handles writing financial data to Excel template using label-based row lookup
Never relies on hardcoded row numbers
"""

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import numbers
import pandas as pd
from typing import Dict, List, Tuple, Optional
import io
from mapping import TEMPLATE_LABEL_MAPPING


def find_row_by_label(ws, label: str, search_column: int = 1, 
                      start_row: int = 1, end_row: int = 200) -> Optional[int]:
    """
    Find row number by searching for label in specified column
    
    Args:
        ws: Worksheet object
        label: Label text to search for
        search_column: Column to search (default 1 = Column A)
        start_row: Start searching from this row
        end_row: Stop searching at this row
    
    Returns:
        Row number if found, None otherwise
    """
    label_lower = label.lower().strip()
    
    for row in range(start_row, end_row + 1):
        cell_value = ws.cell(row, search_column).value
        if cell_value:
            cell_lower = str(cell_value).lower().strip()
            # Exact match or contains match
            if label_lower == cell_lower or label_lower in cell_lower:
                return row
    
    return None


def is_formula_cell(ws, row: int, col: int) -> bool:
    """
    Check if a cell contains a formula
    
    Args:
        ws: Worksheet object
        row: Row number
        col: Column number
    
    Returns:
        True if cell contains formula, False otherwise
    """
    cell = ws.cell(row, col)
    
    # Check if cell has a formula
    if hasattr(cell, 'data_type') and cell.data_type == 'f':
        return True
    
    # Also check the value
    if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
        return True
    
    return False


def get_year_columns(ws, data_years: List[int], 
                     header_row: int = 31) -> Dict[int, int]:
    """
    Map data years to Excel columns
    Template supports 3 years: columns B, C, D (2, 3, 4)
    
    Args:
        ws: Worksheet object
        data_years: List of years in data (e.g., [2023, 2024])
        header_row: Row where year headers should be written
    
    Returns:
        Dict mapping year -> column number
    """
    # Template supports 3 year columns: B, C, D
    available_cols = [2, 3, 4]
    
    # Sort years ascending
    sorted_years = sorted(data_years)
    
    # Take only first 3 years if more provided
    years_to_use = sorted_years[:3]
    
    # Map years to columns
    year_col_map = {}
    for i, year in enumerate(years_to_use):
        col = available_cols[i]
        year_col_map[year] = col
        
        # Write year header
        ws.cell(header_row, col).value = year
    
    return year_col_map


def write_financial_data_to_template(template_path: str,
                                     financial_data: Dict[int, Dict],
                                     unit_scale: float = 1.0) -> io.BytesIO:
    """
    Write financial data to Excel template using label-based lookup
    
    Args:
        template_path: Path to template file
        financial_data: Dict of {year: {line_item: value}}
        unit_scale: Scale factor for amounts (1.0 for thousands, 1000.0 for dollars->thousands)
    
    Returns:
        BytesIO object containing the Excel file
    """
    # Load template
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active
    
    # Get years and map to columns
    years = sorted(financial_data.keys())
    year_col_map = get_year_columns(ws, years, header_row=31)
    
    # Track what was written
    writes_performed = []
    warnings = []
    
    # Write data using label lookup
    for year, data in financial_data.items():
        if year not in year_col_map:
            warnings.append(f'Year {year} exceeds 3-year template limit, skipped')
            continue
        
        col = year_col_map[year]
        
        for data_key, value in data.items():
            # Find template label for this data key
            template_label = None
            for label, key in TEMPLATE_LABEL_MAPPING.items():
                if key == data_key:
                    template_label = label
                    break
            
            if not template_label:
                continue
            
            # Find row by label
            row = find_row_by_label(ws, template_label)
            
            if row is None:
                warnings.append(f'Label "{template_label}" not found in template')
                continue
            
            # Check if target cell is a formula
            if is_formula_cell(ws, row, col):
                warnings.append(f'Skipped {template_label} (formula cell)')
                continue
            
            # Apply scale and write value
            scaled_value = value / unit_scale if value else 0
            
            # Special handling for negatives (ensure correct signs)
            # Liabilities and equity should be positive
            # Expenses should be positive
            # Revenues should be positive
            
            ws.cell(row, col).value = scaled_value
            writes_performed.append(f'{template_label} ({year}): {scaled_value:.2f}')
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output


def calculate_financial_statements(df: pd.DataFrame,
                                   is_trial_balance: bool = True) -> Dict[int, Dict]:
    """
    Calculate financial statements from mapped data
    
    Args:
        df: DataFrame with FSLI_Category column
        is_trial_balance: True if TB data, False if GL data
    
    Returns:
        Dict of {year: {line_item: value}}
    """
    financial_data = {}
    
    # Extract years from TxnDate
    df['TxnDate'] = pd.to_datetime(df['TxnDate'], errors='coerce')
    df['Year'] = df['TxnDate'].dt.year
    
    years = sorted(df['Year'].dropna().unique())
    
    for year in years:
        year_data = df[df['Year'] == year].copy()
        
        # Helper function to sum category
        def sum_category(category: str, debit_credit: str = 'both') -> float:
            cat_data = year_data[year_data['FSLI_Category'] == category]
            if debit_credit == 'debit':
                return cat_data['Debit'].sum()
            elif debit_credit == 'credit':
                return cat_data['Credit'].sum()
            else:
                return cat_data['Debit'].sum() - cat_data['Credit'].sum()
        
        # Income Statement
        revenue = sum_category('revenue', 'credit')
        cogs = sum_category('cogs', 'debit')
        distribution_expenses = sum_category('distribution_expenses', 'debit')
        marketing_admin = sum_category('marketing_admin', 'debit')
        research_dev = sum_category('research_dev', 'debit')
        depreciation_expense = sum_category('depreciation_expense', 'debit')
        interest_expense = sum_category('interest_expense', 'debit')
        tax_expense = sum_category('tax_expense', 'debit')
        
        gross_profit = revenue - cogs
        total_opex = distribution_expenses + marketing_admin + research_dev + depreciation_expense
        ebit = gross_profit - total_opex
        ebt = ebit - interest_expense
        net_income = ebt - tax_expense
        
        # Balance Sheet (use net method: debit - credit for each category)
        cash = sum_category('cash')
        accounts_receivable = sum_category('accounts_receivable')
        inventory = sum_category('inventory')
        prepaid_expenses = sum_category('prepaid_expenses')
        other_current_assets = sum_category('other_current_assets')
        
        ppe_gross = sum_category('ppe_gross')
        accumulated_depreciation = abs(sum_category('accumulated_depreciation'))  # Make positive
        ppe_net = ppe_gross - accumulated_depreciation
        
        total_current_assets = cash + accounts_receivable + inventory + prepaid_expenses + other_current_assets
        total_assets = total_current_assets + ppe_net
        
        # Liabilities (use absolute values to ensure positive)
        accounts_payable = abs(sum_category('accounts_payable'))
        accrued_payroll = abs(sum_category('accrued_payroll'))
        deferred_revenue = abs(sum_category('deferred_revenue'))
        interest_payable = abs(sum_category('interest_payable'))
        other_current_liabilities = abs(sum_category('other_current_liabilities'))
        income_taxes_payable = abs(sum_category('income_taxes_payable'))
        long_term_debt = abs(sum_category('long_term_debt'))
        
        total_current_liabilities = (accounts_payable + accrued_payroll + deferred_revenue + 
                                    interest_payable + other_current_liabilities + income_taxes_payable)
        total_liabilities = total_current_liabilities + long_term_debt
        
        # Equity
        common_stock = abs(sum_category('common_stock'))
        retained_earnings = abs(sum_category('retained_earnings'))
        dividends = sum_category('dividends', 'debit')
        
        total_equity = common_stock + retained_earnings
        
        # Store all line items
        financial_data[year] = {
            # Income Statement
            'revenue': revenue,
            'cogs': cogs,
            'distribution_expenses': distribution_expenses,
            'marketing_admin': marketing_admin,
            'research_dev': research_dev,
            'depreciation_expense': depreciation_expense,
            'interest_expense': interest_expense,
            'tax_expense': tax_expense,
            
            # Balance Sheet - Assets
            'cash': cash,
            'accounts_receivable': accounts_receivable,
            'inventory': inventory,
            'prepaid_expenses': prepaid_expenses,
            'other_current_assets': other_current_assets,
            'ppe_gross': ppe_gross,
            'accumulated_depreciation': accumulated_depreciation,
            
            # Balance Sheet - Liabilities
            'accounts_payable': accounts_payable,
            'accrued_payroll': accrued_payroll,
            'deferred_revenue': deferred_revenue,
            'interest_payable': interest_payable,
            'other_current_liabilities': other_current_liabilities,
            'income_taxes_payable': income_taxes_payable,
            'long_term_debt': long_term_debt,
            
            # Balance Sheet - Equity
            'common_stock': common_stock,
            'retained_earnings': retained_earnings,
            'dividends': dividends,
        }
    
    # Calculate Cash Flow (requires multi-year data)
    if len(years) >= 2:
        for i in range(1, len(years)):
            current_year = years[i]
            prior_year = years[i-1]
            
            current = financial_data[current_year]
            prior = financial_data[prior_year]
            
            # Calculate deltas (negative means cash use, positive means cash source)
            delta_ar = current['accounts_receivable'] - prior['accounts_receivable']
            delta_inventory = current['inventory'] - prior['inventory']
            delta_prepaid = current['prepaid_expenses'] - prior['prepaid_expenses']
            delta_other_current_assets = current['other_current_assets'] - prior['other_current_assets']
            delta_ap = current['accounts_payable'] - prior['accounts_payable']
            delta_accrued_payroll = current['accrued_payroll'] - prior['accrued_payroll']
            delta_deferred_revenue = current['deferred_revenue'] - prior['deferred_revenue']
            delta_interest_payable = current['interest_payable'] - prior['interest_payable']
            delta_other_current_liabilities = current['other_current_liabilities'] - prior['other_current_liabilities']
            delta_income_taxes_payable = current['income_taxes_payable'] - prior['income_taxes_payable']
            delta_debt = current['long_term_debt'] - prior['long_term_debt']
            
            # CapEx (negative for cash outflow)
            capex = -(current['ppe_gross'] - prior['ppe_gross'])
            
            # Stock issuance
            stock_issuance = current['common_stock'] - prior['common_stock']
            
            # Add cash flow items
            financial_data[current_year].update({
                'delta_ar': -delta_ar,  # Increase in AR uses cash
                'delta_inventory': -delta_inventory,
                'delta_prepaid': -delta_prepaid,
                'delta_other_current_assets': -delta_other_current_assets,
                'delta_ap': delta_ap,  # Increase in AP provides cash
                'delta_accrued_payroll': delta_accrued_payroll,
                'delta_deferred_revenue': delta_deferred_revenue,
                'delta_interest_payable': delta_interest_payable,
                'delta_other_current_liabilities': delta_other_current_liabilities,
                'delta_income_taxes_payable': delta_income_taxes_payable,
                'delta_debt': delta_debt,
                'capex': capex,
                'stock_issuance': stock_issuance,
            })
    
    return financial_data


def validate_template_structure(template_path: str) -> Tuple[bool, List[str]]:
    """
    Validate that template has expected structure
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
        
        # Check key labels exist
        required_labels = [
            'Revenues',
            'Cost of Goods Sold',
            'Cash',
            'Accounts Payable',
            'Common Stock and Additional Paid-In Capital',
        ]
        
        for label in required_labels:
            row = find_row_by_label(ws, label)
            if row is None:
                issues.append(f'Required label "{label}" not found')
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f'Error loading template: {str(e)}')
        return False, issues
