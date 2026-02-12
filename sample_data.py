"""
Sample Data Handler Module
Manages sample data loading for demo buttons
"""

import pandas as pd
import os
import random
from typing import Tuple, Optional


def get_sample_data_path(filename: str) -> str:
    """
    Get full path to sample data file
    
    Args:
        filename: Name of sample data file
    
    Returns:
        Full path to file
    """
    # Try multiple possible locations
    base_dir = os.path.dirname(__file__)

    possible_paths = [
        os.path.join(base_dir, filename),
        os.path.join(base_dir, 'assets', 'sample_data', filename),

        os.path.join('assets', 'sample_data', filename),
        os.path.join('accounting_app', 'assets', 'sample_data', filename),
        os.path.join('/home/claude/accounting_app', 'assets', 'sample_data', filename),
        filename,  # Current directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError(f"Sample data file not found: {filename}")


def load_sample_tb() -> pd.DataFrame:
    """
    Load sample Trial Balance data
    
    Returns:
        DataFrame with sample TB data
    """
    try:
        path = get_sample_data_path('sample_tb.csv')
        df = pd.read_csv(path)
        return df
    except Exception as e:
        raise Exception(f"Error loading sample TB: {str(e)}")


def load_sample_gl(with_txnid: bool = True) -> pd.DataFrame:
    """
    Load sample GL Activity data
    
    Args:
        with_txnid: Whether to load version with TransactionID
    
    Returns:
        DataFrame with sample GL data
    """
    try:
        filename = 'sample_gl_with_txnid.csv' if with_txnid else 'sample_gl_no_txnid.csv'
        path = get_sample_data_path(filename)
        df = pd.read_csv(path)
        return df
    except Exception as e:
        raise Exception(f"Error loading sample GL: {str(e)}")



def load_random_backup_tb():
    """Load one of the 3-year backup Trial Balance (BS snapshot) datasets."""
    backup_files = [
        'backup_tb_2020_2022.csv',
        'backup_tb_2021_2023.csv',
        'backup_tb_2022_2024.csv',
        'backup_tb_2023_2025.csv',
        'backup_tb_2024_2026.csv',
    ]
    selected_file = random.choice(backup_files)
    df = pd.read_csv(get_sample_data_path(selected_file))
    return df, selected_file

def load_random_backup_gl() -> Tuple[pd.DataFrame, str]:
    """
    Load a random backup GL dataset
    
    Returns:
        (DataFrame, dataset_name)
    """
    backup_files = [
        'backup_gl_2020_2022_with_txnid.csv',
        'backup_gl_2021_2023_with_txnid.csv',
        'backup_gl_2022_2024_with_txnid.csv',
        'backup_gl_2023_2025_with_txnid.csv',
        'backup_gl_2024_2026_with_txnid.csv',
    ]
    
    # Randomly select one
    selected_file = random.choice(backup_files)
    
    try:
        path = get_sample_data_path(selected_file)
        df = pd.read_csv(path)
        
        # Extract year range from filename
        dataset_name = selected_file.replace('backup_gl_', '').replace('.csv', '')
        
        return df, dataset_name
    except Exception as e:
        raise Exception(f"Error loading random backup GL: {str(e)}")


def get_template_path(template_type: str = 'zero') -> str:
    base_dir = os.path.dirname(__file__)
    """
    Get path to Excel template
    
    Args:
        template_type: 'zero' for processing template, 'demo' for sample
    
    Returns:
        Full path to template file
    """
    if template_type == 'zero':
        filename = 'Financial_Model_TEMPLATE_ZERO_USD_thousands_GAAP.xlsx'
    else:
        filename = 'Financial_Model_SAMPLE_DEMO_USD_thousands_GAAP.xlsx'
    
    possible_paths = [
        os.path.join(base_dir, filename),
        os.path.join(base_dir, 'assets', 'sample_data', filename),

        os.path.join('assets', 'templates', filename),
        os.path.join('accounting_app', 'assets', 'templates', filename),
        os.path.join('/home/claude/accounting_app', 'assets', 'templates', filename),
        filename,
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError(f"Template file not found: {filename}")


def list_available_datasets() -> dict:
    """
    List all available sample datasets
    
    Returns:
        Dict with dataset information
    """
    datasets = {
        'trial_balance': {
            'file': 'sample_tb.csv',
            'description': 'Sample Trial Balance (2023-2024)',
            'has_txnid': False,
            'available': False
        },
        'gl_with_txnid': {
            'file': 'sample_gl_with_txnid.csv',
            'description': 'Sample GL Activity with TransactionID (2023-2024)',
            'has_txnid': True,
            'available': False
        },
        'gl_no_txnid': {
            'file': 'sample_gl_no_txnid.csv',
            'description': 'Sample GL Activity without TransactionID (2023-2024)',
            'has_txnid': False,
            'available': False
        },
        'backups': {
            'files': [
                'backup_gl_2020_2021_with_txnid.csv',
                'backup_gl_2021_2022_with_txnid.csv',
                'backup_gl_2022_2024_no_txnid.csv',
                'backup_gl_2023_2024_with_txnid.csv',
                'backup_gl_2024_2026_no_txnid.csv',
            ],
            'description': '5 backup GL datasets for stress testing',
            'available': False
        }
    }
    
    # Check which files exist
    try:
        get_sample_data_path('sample_tb.csv')
        datasets['trial_balance']['available'] = True
    except:
        pass
    
    try:
        get_sample_data_path('sample_gl_with_txnid.csv')
        datasets['gl_with_txnid']['available'] = True
    except:
        pass
    
    try:
        get_sample_data_path('sample_gl_no_txnid.csv')
        datasets['gl_no_txnid']['available'] = True
    except:
        pass
    
    backup_count = 0
    for backup in datasets['backups']['files']:
        try:
            get_sample_data_path(backup)
            backup_count += 1
        except:
            pass
    
    datasets['backups']['available'] = backup_count > 0
    datasets['backups']['count'] = backup_count
    
    return datasets
