"""
Test Suite for Three Statements Automation
Tests all core functionality
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from validation import (normalize_column_headers, check_required_columns,
                       validate_trial_balance, validate_gl_activity,
                       validate_common_issues, apply_auto_fixes)
from mapping import (map_account_by_name, map_account_by_range, map_accounts,
                    normalize_account_name, classify_accrued_liability)
from excel_writer import (find_row_by_label, is_formula_cell, 
                          calculate_financial_statements)


class TestColumnNormalization:
    """Test column header normalization"""
    
    def test_normalize_basic_columns(self):
        """Test basic column name normalization"""
        df = pd.DataFrame({
            'TXNDATE': [1, 2],
            'Account_Number': [100, 200],
            'account name': ['Cash', 'Revenue'],
            'DebiT': [100, 0],
            'CREDIT': [0, 100]
        })
        
        normalized = normalize_column_headers(df)
        
        assert 'TxnDate' in normalized.columns
        assert 'AccountNumber' in normalized.columns
        assert 'AccountName' in normalized.columns
        assert 'Debit' in normalized.columns
        assert 'Credit' in normalized.columns
    
    def test_normalize_with_variations(self):
        """Test normalization with column variations"""
        df = pd.DataFrame({
            'transaction_date': [1],
            'acct_num': [100],
            'description': ['Test'],
            'dr': [50],
            'cr': [50]
        })
        
        normalized = normalize_column_headers(df)
        
        assert 'TxnDate' in normalized.columns
        assert 'AccountNumber' in normalized.columns
        assert 'AccountName' in normalized.columns
        assert 'Debit' in normalized.columns
        assert 'Credit' in normalized.columns
    
    def test_extra_columns_preserved(self):
        """Test that extra columns are preserved"""
        df = pd.DataFrame({
            'TxnDate': [1],
            'AccountNumber': [100],
            'AccountName': ['Test'],
            'Debit': [50],
            'Credit': [50],
            'ExtraColumn': ['Extra']
        })
        
        normalized = normalize_column_headers(df)
        assert 'ExtraColumn' in normalized.columns


class TestRequiredColumns:
    """Test required column checking"""
    
    def test_all_required_present(self):
        """Test with all required columns"""
        df = pd.DataFrame({
            'TxnDate': [1],
            'AccountNumber': [100],
            'AccountName': ['Test'],
            'Debit': [50],
            'Credit': [50]
        })
        
        is_valid, missing = check_required_columns(df)
        assert is_valid
        assert len(missing) == 0
    
    def test_missing_columns(self):
        """Test with missing required columns"""
        df = pd.DataFrame({
            'TxnDate': [1],
            'AccountNumber': [100]
        })
        
        is_valid, missing = check_required_columns(df)
        assert not is_valid
        assert 'AccountName' in missing
        assert 'Debit' in missing
        assert 'Credit' in missing


class TestTrialBalanceValidation:
    """Test Trial Balance validation"""
    
    def test_balanced_tb(self):
        """Test TB that balances"""
        df = pd.DataFrame({
            'TxnDate': ['2023-12-31'] * 4,
            'AccountNumber': [1000, 2000, 4000, 5000],
            'AccountName': ['Cash', 'AP', 'Revenue', 'Expense'],
            'Debit': [100, 0, 0, 50],
            'Credit': [0, 50, 100, 0]
        })
        
        issues = validate_trial_balance(df)
        
        # Should have no balance issues
        balance_issues = [i for i in issues if i['category'] == 'Trial Balance']
        assert len(balance_issues) == 0
    
    def test_unbalanced_tb(self):
        """Test TB that doesn't balance"""
        df = pd.DataFrame({
            'TxnDate': ['2023-12-31'] * 3,
            'AccountNumber': [1000, 2000, 4000],
            'AccountName': ['Cash', 'AP', 'Revenue'],
            'Debit': [100, 0, 0],
            'Credit': [0, 50, 60]  # Unbalanced by 10
        })
        
        issues = validate_trial_balance(df, tolerance_abs=0.01)
        
        # Should have balance issues
        balance_issues = [i for i in issues if i['category'] == 'Trial Balance']
        assert len(balance_issues) > 0


class TestGLActivityValidation:
    """Test GL Activity validation"""
    
    def test_gl_with_txnid_balanced(self):
        """Test GL with TransactionID that balances"""
        df = pd.DataFrame({
            'TxnDate': ['2023-01-01'] * 4,
            'TransactionID': ['TXN001', 'TXN001', 'TXN002', 'TXN002'],
            'AccountNumber': [1000, 4000, 1000, 2000],
            'AccountName': ['Cash', 'Revenue', 'Cash', 'AP'],
            'Debit': [100, 0, 0, 50],
            'Credit': [0, 100, 50, 0]
        })
        
        issues = validate_gl_activity(df)
        
        # Should have no critical balance issues
        critical = [i for i in issues if i['severity'] == 'Critical']
        balance_critical = [i for i in critical if 'balance' in i['issue'].lower()]
        assert len(balance_critical) == 0
    
    def test_gl_without_txnid(self):
        """Test GL without TransactionID"""
        df = pd.DataFrame({
            'TxnDate': ['2023-01-01'] * 3,
            'AccountNumber': [1000, 4000, 5000],
            'AccountName': ['Cash', 'Revenue', 'Expense'],
            'Debit': [100, 0, 50],
            'Credit': [0, 100, 50]
        })
        
        issues = validate_gl_activity(df)
        
        # Should have info about missing TransactionID
        info_issues = [i for i in issues if i['severity'] == 'Info']
        txnid_info = [i for i in info_issues if 'TransactionID' in i['issue']]
        assert len(txnid_info) > 0


class TestAccountMapping:
    """Test account mapping functionality"""
    
    def test_map_by_name_cash(self):
        """Test name-based mapping for cash"""
        assert map_account_by_name('Cash') == 'cash'
        assert map_account_by_name('Cash and Cash Equivalents') == 'cash'
        assert map_account_by_name('BANK ACCOUNT') == 'cash'
    
    def test_map_by_name_ar(self):
        """Test name-based mapping for AR"""
        assert map_account_by_name('Accounts Receivable') == 'accounts_receivable'
        assert map_account_by_name('A/R') == 'accounts_receivable'
        assert map_account_by_name('Trade Receivables') == 'accounts_receivable'
    
    def test_map_by_range(self):
        """Test range-based mapping"""
        assert map_account_by_range(1000) == 'cash'
        assert map_account_by_range(1100) == 'accounts_receivable'
        assert map_account_by_range(4000) == 'revenue'
        assert map_account_by_range(5000) == 'cogs'
    
    def test_classify_accrued_payroll(self):
        """Test accrued liability classification"""
        assert classify_accrued_liability('Accrued Payroll') == 'accrued_payroll'
        assert classify_accrued_liability('Accrued Wages') == 'accrued_payroll'
        assert classify_accrued_liability('Bonus Accrual') == 'accrued_payroll'
        assert classify_accrued_liability('Accrued Expenses') == 'other_current_liabilities'
    
    def test_full_mapping_dataframe(self):
        """Test mapping entire DataFrame"""
        df = pd.DataFrame({
            'AccountNumber': [1000, 1100, 4000, 5000],
            'AccountName': ['Cash', 'Accounts Receivable', 'Sales Revenue', 'COGS']
        })
        
        mapped = map_accounts(df)
        
        assert 'FSLI_Category' in mapped.columns
        assert mapped.loc[0, 'FSLI_Category'] == 'cash'
        assert mapped.loc[1, 'FSLI_Category'] == 'accounts_receivable'
        assert mapped.loc[2, 'FSLI_Category'] == 'revenue'
        assert mapped.loc[3, 'FSLI_Category'] == 'cogs'


class TestCommonIssuesValidation:
    """Test common data quality issues"""
    
    def test_missing_dates(self):
        """Test detection of missing dates"""
        df = pd.DataFrame({
            'TxnDate': [pd.NaT, '2023-01-01'],
            'AccountNumber': [1000, 1000],
            'AccountName': ['Cash', 'Cash'],
            'Debit': [100, 100],
            'Credit': [0, 0]
        })
        
        issues = validate_common_issues(df)
        
        missing_dates = [i for i in issues if 'missing dates' in i['issue'].lower()]
        assert len(missing_dates) > 0
        assert missing_dates[0]['total_affected'] == 1
    
    def test_duplicates(self):
        """Test detection of duplicates"""
        df = pd.DataFrame({
            'TxnDate': ['2023-01-01'] * 4,
            'TransactionID': ['TXN001', 'TXN001', 'TXN002', 'TXN002'],
            'AccountNumber': [1000, 1000, 1000, 1000],
            'AccountName': ['Cash'] * 4,
            'Debit': [100, 100, 50, 50],
            'Credit': [0, 0, 0, 0]
        })
        
        issues = validate_common_issues(df)
        
        duplicates = [i for i in issues if 'duplicate' in i['issue'].lower()]
        assert len(duplicates) > 0


class TestAutoFixes:
    """Test auto-fix functionality"""
    
    def test_remove_missing_dates(self):
        """Test removing rows with missing dates"""
        df = pd.DataFrame({
            'TxnDate': [pd.NaT, '2023-01-01', pd.NaT],
            'AccountNumber': [1000, 1000, 1000],
            'AccountName': ['Cash'] * 3,
            'Debit': [100, 100, 100],
            'Credit': [0, 0, 0]
        })
        
        fixed, changes = apply_auto_fixes(df, ['remove_missing_dates'])
        
        assert len(fixed) == 1
        assert not fixed['TxnDate'].isna().any()
    
    def test_map_unclassified(self):
        """Test mapping missing account numbers"""
        df = pd.DataFrame({
            'TxnDate': ['2023-01-01'] * 2,
            'AccountNumber': [1000, np.nan],
            'AccountName': ['Cash', 'Unknown'],
            'Debit': [100, 100],
            'Credit': [0, 0]
        })
        
        fixed, changes = apply_auto_fixes(df, ['map_unclassified'])
        
        assert not fixed['AccountNumber'].isna().any()
        assert fixed.loc[1, 'AccountNumber'] == 9999


class TestFinancialStatements:
    """Test financial statement calculation"""
    
    def test_basic_income_statement(self):
        """Test basic income statement calculation"""
        df = pd.DataFrame({
            'TxnDate': ['2023-12-31'] * 4,
            'AccountNumber': [4000, 5000, 6000, 6500],
            'AccountName': ['Revenue', 'COGS', 'Salaries', 'Tax Expense'],
            'Debit': [0, 300, 100, 20],
            'Credit': [1000, 0, 0, 0],
            'FSLI_Category': ['revenue', 'cogs', 'marketing_admin', 'tax_expense']
        })
        
        df['TxnDate'] = pd.to_datetime(df['TxnDate'])
        
        financial_data = calculate_financial_statements(df, is_trial_balance=True)
        
        assert 2023 in financial_data
        assert financial_data[2023]['revenue'] == 1000
        assert financial_data[2023]['cogs'] == 300
        assert financial_data[2023]['marketing_admin'] == 100
        assert financial_data[2023]['tax_expense'] == 20


class TestHeaderOrderIndependence:
    """Test that column order doesn't matter"""
    
    def test_shuffled_columns(self):
        """Test with shuffled column order"""
        df = pd.DataFrame({
            'Credit': [100, 0],
            'AccountName': ['Revenue', 'Cash'],
            'TxnDate': ['2023-01-01', '2023-01-01'],
            'Debit': [0, 100],
            'AccountNumber': [4000, 1000]
        })
        
        normalized = normalize_column_headers(df)
        is_valid, missing = check_required_columns(normalized)
        
        assert is_valid
        assert len(missing) == 0


class TestMultiYearHandling:
    """Test multi-year data handling"""
    
    def test_single_year(self):
        """Test with single year of data"""
        df = pd.DataFrame({
            'TxnDate': ['2023-12-31'] * 2,
            'AccountNumber': [4000, 5000],
            'AccountName': ['Revenue', 'COGS'],
            'Debit': [0, 500],
            'Credit': [1000, 0],
            'FSLI_Category': ['revenue', 'cogs']
        })
        
        df['TxnDate'] = pd.to_datetime(df['TxnDate'])
        
        financial_data = calculate_financial_statements(df, is_trial_balance=True)
        
        assert len(financial_data) == 1
        assert 2023 in financial_data
    
    def test_three_years(self):
        """Test with three years of data"""
        df = pd.DataFrame({
            'TxnDate': ['2023-12-31', '2023-12-31', '2024-12-31', '2024-12-31', 
                       '2025-12-31', '2025-12-31'],
            'AccountNumber': [4000, 5000] * 3,
            'AccountName': ['Revenue', 'COGS'] * 3,
            'Debit': [0, 500, 0, 600, 0, 700],
            'Credit': [1000, 0, 1200, 0, 1400, 0],
            'FSLI_Category': ['revenue', 'cogs'] * 3
        })
        
        df['TxnDate'] = pd.to_datetime(df['TxnDate'])
        
        financial_data = calculate_financial_statements(df, is_trial_balance=True)
        
        assert len(financial_data) == 3
        assert 2023 in financial_data
        assert 2024 in financial_data
        assert 2025 in financial_data


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
