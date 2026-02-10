"""
Account Mapping Module
Handles mapping of GL accounts to financial statement line items using:
1. Primary: Name-based alias matching (big company FSLI style)
2. Secondary: Account number range fallback
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
import re


# Default account number ranges (configurable)
DEFAULT_ACCOUNT_RANGES = {
    # Assets
    'cash': (1000, 1099),
    'accounts_receivable': (1100, 1199),
    'inventory': (1200, 1299),
    'prepaid_expenses': (1300, 1349),
    'other_current_assets': (1350, 1499),
    'ppe_gross': (1500, 1599),
    'accumulated_depreciation': (1590, 1599),
    'other_fixed_assets': (1600, 1999),
    
    # Liabilities
    'accounts_payable': (2000, 2099),
    'accrued_payroll': (2100, 2149),
    'deferred_revenue': (2150, 2249),
    'interest_payable': (2250, 2299),
    'other_current_liabilities': (2300, 2449),
    'income_taxes_payable': (2450, 2499),
    'long_term_debt': (2500, 2999),
    
    # Equity
    'common_stock': (3000, 3099),
    'retained_earnings': (3100, 3199),
    'dividends': (3200, 3999),
    
    # Income Statement
    'revenue': (4000, 4999),
    'cogs': (5000, 5099),
    'distribution_expenses': (5100, 5199),
    'marketing_admin': (5200, 5299),
    'research_dev': (5300, 5349),
    'depreciation_expense': (5350, 5399),
    'other_opex': (5400, 5999),
    'interest_expense': (6000, 6099),
    'tax_expense': (6100, 6999),
}


# Name-based alias mapping (primary method)
ACCOUNT_NAME_ALIASES = {
    # Assets
    'cash': [
        'cash', 'cash and cash equivalents', 'cash equivalents', 
        'bank', 'petty cash', 'cash on hand'
    ],
    'accounts_receivable': [
        'accounts receivable', 'a/r', 'ar', 'trade receivable', 
        'trade and other receivables', 'receivables', 'debtors'
    ],
    'inventory': [
        'inventory', 'inventories', 'stock', 'merchandise', 
        'finished goods', 'raw materials', 'work in process', 'wip'
    ],
    'prepaid_expenses': [
        'prepaid', 'prepaid expenses', 'prepayments', 'deferred expenses'
    ],
    'other_current_assets': [
        'other current assets', 'current assets - other', 
        'deposits', 'advances'
    ],
    'ppe_gross': [
        'property plant and equipment', 'ppe', 'pp&e', 'fixed assets',
        'property, plant & equipment', 'capital assets', 'plant and equipment',
        'property and equipment', 'equipment', 'machinery', 'buildings',
        'land and buildings', 'furniture', 'fixtures', 'vehicles'
    ],
    'accumulated_depreciation': [
        'accumulated depreciation', 'accumulated depr', 'acc depreciation',
        'depreciation', 'amortization'
    ],
    
    # Liabilities
    'accounts_payable': [
        'accounts payable', 'a/p', 'ap', 'trade payable', 
        'trade payables', 'payables', 'creditors'
    ],
    'accrued_payroll': [
        'accrued payroll', 'accrued wages', 'accrued salaries', 
        'payroll payable', 'wages payable', 'salaries payable',
        'employee compensation', 'accrued compensation', 'bonus accrual'
    ],
    'deferred_revenue': [
        'deferred revenue', 'unearned revenue', 'deferred income',
        'contract liabilities', 'customer deposits', 'advance payments',
        'prepayments from customers'
    ],
    'interest_payable': [
        'interest payable', 'accrued interest', 'interest accrual'
    ],
    'other_current_liabilities': [
        'other current liabilities', 'accrued liabilities', 
        'accrued expenses', 'other accruals', 'current liabilities - other'
    ],
    'income_taxes_payable': [
        'income taxes payable', 'income tax payable', 'tax payable',
        'taxes payable', 'current tax liability'
    ],
    'long_term_debt': [
        'long-term debt', 'long term debt', 'notes payable', 
        'term loan', 'revolver', 'loan payable', 'borrowings',
        'bank loan', 'debt'
    ],
    
    # Equity
    'common_stock': [
        'common stock', 'share capital', 'paid-in capital', 
        'additional paid-in capital', 'apic', 'contributed capital',
        'common stock and additional paid-in capital'
    ],
    'retained_earnings': [
        'retained earnings', 'accumulated earnings', 
        'accumulated profits', 'earnings retained'
    ],
    'dividends': [
        'dividends', 'dividend', 'dividends declared', 
        'common dividends', 'dividend payable'
    ],
    
    # Income Statement
    'revenue': [
        'revenue', 'revenues', 'sales', 'income', 'turnover',
        'product revenue', 'service revenue', 'net sales'
    ],
    'cogs': [
        'cost of goods sold', 'cogs', 'cost of sales', 
        'cost of revenue', 'direct costs'
    ],
    'distribution_expenses': [
        'distribution', 'distribution expenses', 'shipping', 
        'freight', 'delivery', 'logistics'
    ],
    'marketing_admin': [
        'marketing', 'marketing and administration', 'sg&a',
        'selling general and administrative', 'admin', 'administrative',
        'general and administrative', 'overhead'
    ],
    'research_dev': [
        'research and development', 'r&d', 'research', 'development'
    ],
    'depreciation_expense': [
        'depreciation expense', 'depreciation', 'amortization expense',
        'depr expense', 'amort expense'
    ],
    'interest_expense': [
        'interest expense', 'interest', 'finance charges', 
        'interest on debt', 'borrowing costs'
    ],
    'tax_expense': [
        'income tax expense', 'tax expense', 'taxes', 
        'provision for income taxes', 'current tax', 'income taxes'
    ],
}


# Special handling for accrued liabilities (context-dependent)
def classify_accrued_liability(account_name: str) -> str:
    """
    Apply standard rule for accrued liabilities:
    - If contains payroll/wages/bonus -> Accrued Payroll
    - Else -> Other Current Liabilities
    """
    account_lower = account_name.lower()
    
    payroll_keywords = ['payroll', 'wage', 'salary', 'bonus', 'compensation']
    
    for keyword in payroll_keywords:
        if keyword in account_lower:
            return 'accrued_payroll'
    
    return 'other_current_liabilities'


def normalize_account_name(name: str) -> str:
    """Normalize account name for matching"""
    if pd.isna(name):
        return ""
    
    # Convert to lowercase
    normalized = str(name).lower().strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove common punctuation
    normalized = normalized.replace(',', '').replace('.', '').replace('&', 'and')
    
    return normalized


def map_account_by_name(account_name: str) -> Optional[str]:
    """
    Map account to FSLI line item by name matching
    Returns the FSLI category or None if no match
    """
    if pd.isna(account_name):
        return None
    
    normalized = normalize_account_name(account_name)
    
    # Special handling for accrued liabilities
    if 'accrued' in normalized:
        return classify_accrued_liability(account_name)
    
    # Check all aliases
    for fsli_category, aliases in ACCOUNT_NAME_ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalized or normalized in alias.lower():
                return fsli_category
    
    return None


def map_account_by_range(account_number: int, 
                         custom_ranges: Optional[Dict] = None) -> Optional[str]:
    """
    Map account to FSLI line item by account number range
    Falls back to default ranges if custom not provided
    """
    if pd.isna(account_number):
        return None
    
    ranges = custom_ranges or DEFAULT_ACCOUNT_RANGES
    
    for fsli_category, (range_start, range_end) in ranges.items():
        if range_start <= account_number <= range_end:
            return fsli_category
    
    return None


def map_accounts(df: pd.DataFrame, 
                 custom_ranges: Optional[Dict] = None) -> pd.DataFrame:
    """
    Map all accounts in dataframe to FSLI categories
    
    Priority:
    1. Name-based matching (primary)
    2. Range-based matching (fallback)
    3. Unclassified if no match
    
    Args:
        df: DataFrame with AccountNumber and AccountName columns
        custom_ranges: Optional custom account ranges (overrides defaults)
    
    Returns:
        DataFrame with added 'FSLI_Category' column
    """
    df = df.copy()
    
    # Initialize FSLI_Category column
    df['FSLI_Category'] = None
    
    # First pass: Name-based mapping
    if 'AccountName' in df.columns:
        df['FSLI_Category'] = df['AccountName'].apply(map_account_by_name)
    
    # Second pass: Range-based mapping for unmapped accounts
    if 'AccountNumber' in df.columns:
        unmapped = df['FSLI_Category'].isna()
        df.loc[unmapped, 'FSLI_Category'] = df.loc[unmapped, 'AccountNumber'].apply(
            lambda x: map_account_by_range(x, custom_ranges)
        )
    
    # Mark remaining as unclassified
    df['FSLI_Category'] = df['FSLI_Category'].fillna('unclassified')
    
    return df


def get_mapping_stats(df: pd.DataFrame) -> Dict:
    """
    Get statistics on account mapping
    """
    if 'FSLI_Category' not in df.columns:
        return {}
    
    total = len(df)
    mapped = (df['FSLI_Category'] != 'unclassified').sum()
    unclassified = (df['FSLI_Category'] == 'unclassified').sum()
    
    category_counts = df['FSLI_Category'].value_counts().to_dict()
    
    return {
        'total_accounts': total,
        'mapped_accounts': mapped,
        'unclassified_accounts': unclassified,
        'mapping_rate': mapped / total if total > 0 else 0,
        'category_distribution': category_counts
    }


# Template label mapping (for Excel writing)
TEMPLATE_LABEL_MAPPING = {
    # Income Statement
    'Revenues': 'revenue',
    'Cost of Goods Sold': 'cogs',
    'Distribution Expenses': 'distribution_expenses',
    'Marketing and Administration': 'marketing_admin',
    'Research and Development': 'research_dev',
    'Depreciation': 'depreciation_expense',
    'Interest': 'interest_expense',
    'Taxes': 'tax_expense',
    
    # Balance Sheet - Assets
    'Cash': 'cash',
    'Trade and Other Receivables': 'accounts_receivable',
    'Inventories': 'inventory',
    'Prepaid Expenses': 'prepaid_expenses',
    'Other Current Assets': 'other_current_assets',
    'Property Plant and Equipment - Gross': 'ppe_gross',
    'Less: Accumulated Depreciation': 'accumulated_depreciation',
    
    # Balance Sheet - Liabilities
    'Accounts Payable': 'accounts_payable',
    'Accrued Payroll': 'accrued_payroll',
    'Deferred Revenue': 'deferred_revenue',
    'Interest Payable': 'interest_payable',
    'Other Current Liabilities': 'other_current_liabilities',
    'Income Taxes Payable': 'income_taxes_payable',
    'Long-Term Debt': 'long_term_debt',
    
    # Balance Sheet - Equity
    'Common Stock and Additional Paid-In Capital': 'common_stock',
    'Retained Earnings': 'retained_earnings',
    
    # Cash Flow Statement
    'Change in Accounts Receivable': 'delta_ar',
    'Change in Inventory': 'delta_inventory',
    'Change in Prepaid Expenses': 'delta_prepaid',
    'Change in Other Current Assets': 'delta_other_current_assets',
    'Change in Accounts Payable': 'delta_ap',
    'Change in Accrued Payroll': 'delta_accrued_payroll',
    'Change in Deferred Revenue': 'delta_deferred_revenue',
    'Change in Interest Payable': 'delta_interest_payable',
    'Change in Other Current Liabilities': 'delta_other_current_liabilities',
    'Change in Income Taxes Payable': 'delta_income_taxes_payable',
    'Acquisitions of Property and Equipment': 'capex',
    'Dividends (current year)': 'dividends',
    'Issuance of Common Stock': 'stock_issuance',
    'Increase/(Decrease) in Long-Term Debt': 'delta_debt',
}
