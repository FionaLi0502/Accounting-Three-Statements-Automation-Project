"""
Data Validation Module
Handles validation of Trial Balance and GL Activity data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime


def normalize_column_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column headers: case-insensitive, trim spaces
    Accept common variations
    """
    df = df.copy()
    
    # Column name mappings (variations -> standard)
    column_mappings = {
        'txndate': 'TxnDate',
        'transaction_date': 'TxnDate',
        'date': 'TxnDate',
        'transdate': 'TxnDate',
        
        'accountnumber': 'AccountNumber',
        'account_number': 'AccountNumber',
        'acct_num': 'AccountNumber',
        'account': 'AccountNumber',
        'acct': 'AccountNumber',
        
        'accountname': 'AccountName',
        'account_name': 'AccountName',
        'acct_name': 'AccountName',
        'description': 'AccountName',
        
        'debit': 'Debit',
        'dr': 'Debit',
        
        'credit': 'Credit',
        'cr': 'Credit',
        
        'transactionid': 'TransactionID',
        'transaction_id': 'TransactionID',
        'txn_id': 'TransactionID',
        'txnid': 'TransactionID',
        'glid': 'TransactionID',
        
        'currency': 'Currency',
        'curr': 'Currency',
    }
    
    # Normalize: lowercase, trim, remove spaces
    normalized_cols = {}
    for col in df.columns:
        normalized = str(col).lower().strip().replace(' ', '_')
        if normalized in column_mappings:
            normalized_cols[col] = column_mappings[normalized]
        else:
            normalized_cols[col] = col  # Keep original if no mapping
    
    df = df.rename(columns=normalized_cols)
    
    return df


def check_required_columns(df: pd.DataFrame, 
                           data_type: str = 'GL') -> Tuple[bool, List[str]]:
    """
    Check if required columns are present
    
    Args:
        df: DataFrame to check
        data_type: 'TB' or 'GL'
    
    Returns:
        (is_valid, missing_columns)
    """
    required = ['TxnDate', 'AccountNumber', 'AccountName', 'Debit', 'Credit']
    
    missing = [col for col in required if col not in df.columns]
    
    return len(missing) == 0, missing


def validate_trial_balance(df: pd.DataFrame, 
                           tolerance_abs: float = 0.01,
                           tolerance_rel: float = 0.0001) -> List[Dict]:
    """
    Validate Trial Balance data
    
    Requirements:
    - Must balance per period (TxnDate)
    - sum(Debit) ≈ sum(Credit) within tolerance
    
    Args:
        df: Trial Balance DataFrame
        tolerance_abs: Absolute tolerance (USD thousands)
        tolerance_rel: Relative tolerance (0.0001 = 0.01%)
    
    Returns:
        List of validation issues
    """
    issues = []
    
    # Check required columns
    is_valid, missing = check_required_columns(df, 'TB')
    if not is_valid:
        issues.append({
            'severity': 'Critical',
            'category': 'Missing Columns',
            'issue': f'Required columns missing: {", ".join(missing)}',
            'impact': 'Cannot validate Trial Balance',
            'suggestion': 'Ensure file has: TxnDate, AccountNumber, AccountName, Debit, Credit',
            'auto_fix': None,
            'affected_rows': [],
            'total_affected': 0,
        })
        return issues
    
    # Group by period and check balance
    if 'TxnDate' in df.columns:
        df['TxnDate'] = pd.to_datetime(df['TxnDate'], errors='coerce')
        
        # Group by date (period)
        grouped = df.groupby('TxnDate').agg({
            'Debit': 'sum',
            'Credit': 'sum'
        }).reset_index()
        
        # Calculate differences
        grouped['Difference'] = grouped['Debit'] - grouped['Credit']
        grouped['Abs_Diff'] = grouped['Difference'].abs()
        
        # Calculate tolerance
        grouped['Max_Amount'] = grouped[['Debit', 'Credit']].max(axis=1)
        grouped['Tolerance'] = grouped['Max_Amount'] * tolerance_rel
        grouped['Tolerance'] = grouped['Tolerance'].clip(lower=tolerance_abs)
        
        # Find unbalanced periods
        unbalanced = grouped[grouped['Abs_Diff'] > grouped['Tolerance']]
        
        if len(unbalanced) > 0:
            issues.append({
                'severity': 'Critical',
                'category': 'Trial Balance',
                'issue': f'TB does not balance for {len(unbalanced)} period(s)',
                'impact': 'Financial statements will be inaccurate',
                'suggestion': 'Review source data for these periods',
                'auto_fix': None,
                'affected_rows': [],
                'total_affected': len(unbalanced),
                'sample_data': unbalanced[['TxnDate', 'Debit', 'Credit', 'Difference']],
                'detail': f'Periods out of balance: {unbalanced["TxnDate"].dt.strftime("%Y-%m-%d").tolist()}'
            })
    
    # Overall balance check
    total_debit = df['Debit'].sum()
    total_credit = df['Credit'].sum()
    diff = abs(total_debit - total_credit)
    
    max_total = max(total_debit, total_credit)
    tol = max(tolerance_abs, max_total * tolerance_rel)
    
    if diff > tol:
        issues.append({
            'severity': 'Critical',
            'category': 'Trial Balance',
            'issue': f'Overall TB out of balance by ${diff:,.2f}',
            'impact': f'Total Debits: ${total_debit:,.2f} ≠ Total Credits: ${total_credit:,.2f}',
            'suggestion': 'Review all entries',
            'auto_fix': None,
            'affected_rows': [],
            'total_affected': 0,
            'sample_data': pd.DataFrame({
                'Item': ['Total Debits', 'Total Credits', 'Difference'],
                'Amount': [f'${total_debit:,.2f}', f'${total_credit:,.2f}', f'${diff:,.2f}']
            })
        })
    
    return issues


def validate_gl_activity(df: pd.DataFrame,
                         tolerance_abs: float = 0.01,
                         tolerance_rel: float = 0.0001) -> List[Dict]:
    """
    Validate GL Activity data
    
    Requirements:
    - If TransactionID exists: validate per transaction
    - If TransactionID missing: validate overall totals only (with warning)
    
    Args:
        df: GL Activity DataFrame
        tolerance_abs: Absolute tolerance
        tolerance_rel: Relative tolerance
    
    Returns:
        List of validation issues
    """
    issues = []
    
    # Check required columns
    is_valid, missing = check_required_columns(df, 'GL')
    if not is_valid:
        issues.append({
            'severity': 'Critical',
            'category': 'Missing Columns',
            'issue': f'Required columns missing: {", ".join(missing)}',
            'impact': 'Cannot validate GL Activity',
            'suggestion': 'Ensure file has: TxnDate, AccountNumber, AccountName, Debit, Credit',
            'auto_fix': None,
            'affected_rows': [],
            'total_affected': 0,
        })
        return issues
    
    # Check if TransactionID exists and has sufficient data
    has_txnid = 'TransactionID' in df.columns
    
    if has_txnid:
        non_null_pct = df['TransactionID'].notna().sum() / len(df)
        
        if non_null_pct < 0.5:
            # Less than 50% have TransactionID - warn and fall back to overall
            issues.append({
                'severity': 'Warning',
                'category': 'Data Quality',
                'issue': f'TransactionID column exists but only {non_null_pct:.0%} populated',
                'impact': 'Transaction-level balancing unavailable',
                'suggestion': 'Using total-file balancing only',
                'auto_fix': None,
                'affected_rows': [],
                'total_affected': 0,
            })
            has_txnid = False
    else:
        # No TransactionID column
        issues.append({
            'severity': 'Info',
            'category': 'Data Quality',
            'issue': 'TransactionID column not found',
            'impact': 'Transaction-level balancing unavailable',
            'suggestion': 'Using total-file balancing only (weaker validation)',
            'auto_fix': None,
            'affected_rows': [],
            'total_affected': 0,
        })
    
    # Validate per transaction if TransactionID available
    if has_txnid:
        # Group by TransactionID
        txn_df = df[df['TransactionID'].notna()].copy()
        grouped = txn_df.groupby('TransactionID').agg({
            'Debit': 'sum',
            'Credit': 'sum'
        }).reset_index()
        
        grouped['Difference'] = grouped['Debit'] - grouped['Credit']
        grouped['Abs_Diff'] = grouped['Difference'].abs()
        
        # Calculate tolerance per transaction
        grouped['Max_Amount'] = grouped[['Debit', 'Credit']].max(axis=1)
        grouped['Tolerance'] = grouped['Max_Amount'] * tolerance_rel
        grouped['Tolerance'] = grouped['Tolerance'].clip(lower=tolerance_abs)
        
        # Find unbalanced transactions
        unbalanced = grouped[grouped['Abs_Diff'] > grouped['Tolerance']]
        
        if len(unbalanced) > 0:
            issues.append({
                'severity': 'Critical',
                'category': 'Transaction Balance',
                'issue': f'{len(unbalanced)} transaction(s) do not balance',
                'impact': 'Debits ≠ Credits for these transactions',
                'suggestion': 'Review and correct these transactions',
                'auto_fix': None,
                'affected_rows': [],
                'total_affected': len(unbalanced),
                'sample_data': unbalanced.head(20)[['TransactionID', 'Debit', 'Credit', 'Difference']],
            })
    
    # Overall balance check (always perform)
    total_debit = df['Debit'].sum()
    total_credit = df['Credit'].sum()
    diff = abs(total_debit - total_credit)
    
    max_total = max(total_debit, total_credit)
    tol = max(tolerance_abs, max_total * tolerance_rel)
    
    if diff > tol:
        severity = 'Critical' if not has_txnid else 'Warning'
        issues.append({
            'severity': severity,
            'category': 'Overall Balance',
            'issue': f'Overall GL out of balance by ${diff:,.2f}',
            'impact': f'Total Debits: ${total_debit:,.2f} ≠ Total Credits: ${total_credit:,.2f}',
            'suggestion': 'Review all entries',
            'auto_fix': None,
            'affected_rows': [],
            'total_affected': 0,
            'sample_data': pd.DataFrame({
                'Item': ['Total Debits', 'Total Credits', 'Difference'],
                'Amount': [f'${total_debit:,.2f}', f'${total_credit:,.2f}', f'${diff:,.2f}']
            })
        })
    
    return issues


def validate_common_issues(df: pd.DataFrame) -> List[Dict]:
    """
    Validate common data quality issues
    
    - Missing dates
    - Missing account numbers
    - Invalid account numbers
    - Duplicates
    - Outliers
    - Future dates
    """
    issues = []
    
    # Missing dates
    if 'TxnDate' in df.columns:
        df['TxnDate'] = pd.to_datetime(df['TxnDate'], errors='coerce')
        missing_dates = df['TxnDate'].isna()
        if missing_dates.sum() > 0:
            rows = df[missing_dates].index.tolist()
            issues.append({
                'severity': 'Warning',
                'category': 'Missing Data',
                'issue': f'{missing_dates.sum()} transactions missing dates',
                'impact': 'Cannot determine period',
                'suggestion': f'Remove {missing_dates.sum()} rows',
                'auto_fix': 'remove_missing_dates',
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df[missing_dates].head(10),
            })
    
    # Missing account numbers
    if 'AccountNumber' in df.columns:
        missing_acct = df['AccountNumber'].isna()
        if missing_acct.sum() > 0:
            rows = df[missing_acct].index.tolist()
            issues.append({
                'severity': 'Critical',
                'category': 'Missing Data',
                'issue': f'{missing_acct.sum()} transactions without account numbers',
                'impact': 'Cannot categorize',
                'suggestion': 'Map to Unclassified (9999)',
                'auto_fix': 'map_unclassified',
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df[missing_acct].head(10),
            })
        
        # Invalid account numbers
        valid_accts = df['AccountNumber'].notna()
        invalid_acct = (df.loc[valid_accts, 'AccountNumber'] < 0) | \
                       (df.loc[valid_accts, 'AccountNumber'] > 99999)
        if invalid_acct.sum() > 0:
            rows = df[valid_accts][invalid_acct].index.tolist()
            issues.append({
                'severity': 'Critical',
                'category': 'Data Quality',
                'issue': f'{invalid_acct.sum()} invalid account numbers',
                'impact': 'Mapping errors',
                'suggestion': 'Convert negative to positive',
                'auto_fix': 'fix_account_numbers',
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df.loc[rows[:10]],
            })
    
    # Duplicates (if TransactionID exists)
    if 'TransactionID' in df.columns:
        duplicates = df.duplicated(subset=['TransactionID'], keep=False)
        if duplicates.sum() > 0:
            rows = df[duplicates].index.tolist()
            issues.append({
                'severity': 'Warning',
                'category': 'Duplicates',
                'issue': f'{duplicates.sum()} duplicate transaction IDs',
                'impact': 'May inflate amounts',
                'suggestion': f'Remove {duplicates.sum()//2} duplicates',
                'auto_fix': 'remove_duplicates',
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df[duplicates].sort_values(by='TransactionID').head(10),
            })
    
    # Future dates
    if 'TxnDate' in df.columns:
        df['TxnDate'] = pd.to_datetime(df['TxnDate'], errors='coerce')
        future_dates = df['TxnDate'] > datetime.now()
        if future_dates.sum() > 0:
            rows = df[future_dates].index.tolist()
            issues.append({
                'severity': 'Warning',
                'category': 'Data Quality',
                'issue': f'{future_dates.sum()} future-dated transactions',
                'impact': 'May affect current period',
                'suggestion': f'Remove {future_dates.sum()} rows',
                'auto_fix': 'remove_future_dates',
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df[future_dates].head(10),
            })
    
    # Outliers
    amt_col = 'Debit' if 'Debit' in df.columns else None
    if amt_col:
        mean = df[amt_col].abs().mean()
        std = df[amt_col].abs().std()
        outliers = df[amt_col].abs() > (mean + 3 * std)
        if outliers.sum() > 0:
            rows = df[outliers].index.tolist()
            issues.append({
                'severity': 'Info',
                'category': 'Outliers',
                'issue': f'{outliers.sum()} potential outlier transactions',
                'impact': 'Unusual amounts detected',
                'suggestion': 'Review for accuracy',
                'auto_fix': None,
                'affected_rows': rows[:100],
                'total_affected': len(rows),
                'sample_data': df[outliers].head(10),
            })
    
    return issues


def apply_auto_fixes(df: pd.DataFrame, 
                     selected_fixes: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Apply selected auto-fixes to the data
    
    Args:
        df: DataFrame to fix
        selected_fixes: List of fix names to apply
    
    Returns:
        (fixed_df, change_log)
    """
    df = df.copy()
    changes = []
    
    if 'remove_missing_dates' in selected_fixes:
        before = len(df)
        df = df[df['TxnDate'].notna()]
        removed = before - len(df)
        if removed > 0:
            changes.append(f'Removed {removed} rows with missing dates')
    
    if 'map_unclassified' in selected_fixes:
        missing = df['AccountNumber'].isna()
        count = missing.sum()
        df.loc[missing, 'AccountNumber'] = 9999
        if count > 0:
            changes.append(f'Mapped {count} entries to Unclassified (9999)')
    
    if 'fix_account_numbers' in selected_fixes:
        invalid = (df['AccountNumber'] < 0) | (df['AccountNumber'] > 99999)
        count = invalid.sum()
        df.loc[invalid & (df['AccountNumber'] < 0), 'AccountNumber'] = \
            df.loc[invalid & (df['AccountNumber'] < 0), 'AccountNumber'].abs()
        if count > 0:
            changes.append(f'Fixed {count} invalid account numbers')
    
    if 'remove_duplicates' in selected_fixes and 'TransactionID' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['TransactionID'], keep='first')
        removed = before - len(df)
        if removed > 0:
            changes.append(f'Removed {removed} duplicate transactions')
    
    if 'remove_future_dates' in selected_fixes:
        before = len(df)
        df = df[df['TxnDate'] <= datetime.now()]
        removed = before - len(df)
        if removed > 0:
            changes.append(f'Removed {removed} future-dated transactions')
    
    return df, changes
