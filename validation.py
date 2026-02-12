"""
Data Validation Module
Handles validation of Trial Balance and GL Activity data.

Notes:
- We always normalize headers first (case-insensitive + common aliases).
- We coerce TxnDate to datetime and numeric columns (Debit/Credit/AccountNumber/Balance)
  before running any comparisons/sums to avoid "str vs datetime" and "string sums" issues.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------

def _coerce_numeric_series(s: pd.Series) -> pd.Series:
    """
    Coerce a mixed-type numeric series (strings with commas, $ signs, parentheses) into floats.

    Examples supported:
      "1,234.56" -> 1234.56
      "$1,234"   -> 1234
      "(123)"    -> -123
      "  45 "    -> 45
    """
    if s is None:
        return s
    if not isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce")

    cleaned = s.copy()

    # Keep NaN as NaN, convert others to strings for cleaning
    cleaned = cleaned.astype("string")

    # Treat common null strings as <NA>
    cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})

    # Remove currency symbols and commas
    cleaned = cleaned.str.replace(r"[$,]", "", regex=True)

    # Handle parentheses as negative: (123.45) -> -123.45
    cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    # Remove whitespace
    cleaned = cleaned.str.replace(r"\s+", "", regex=True)

    return pd.to_numeric(cleaned, errors="coerce")


def normalize_column_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column headers: case-insensitive, trim spaces, accept common variations.

    Standard columns:
      TxnDate, AccountNumber, AccountName, Debit, Credit, TransactionID, Currency
    """
    df = df.copy()

    column_mappings = {
        "txndate": "TxnDate",
        "transaction_date": "TxnDate",
        "date": "TxnDate",
        "transdate": "TxnDate",

        "accountnumber": "AccountNumber",
        "account_number": "AccountNumber",
        "acct_num": "AccountNumber",
        "account": "AccountNumber",
        "acct": "AccountNumber",

        "accountname": "AccountName",
        "account_name": "AccountName",
        "acct_name": "AccountName",
        "description": "AccountName",

        "debit": "Debit",
        "dr": "Debit",

        "credit": "Credit",
        "cr": "Credit",

        "transactionid": "TransactionID",
        "transaction_id": "TransactionID",
        "txn_id": "TransactionID",
        "txnid": "TransactionID",
        "glid": "TransactionID",

        "currency": "Currency",
        "curr": "Currency",
    }

    normalized_cols = {}
    for col in df.columns:
        key = str(col).lower().strip().replace(" ", "_")
        normalized_cols[col] = column_mappings.get(key, col)

    return df.rename(columns=normalized_cols)


def _normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers + coerce TxnDate and numeric columns used across validators."""
    df = normalize_column_headers(df)

    if "TxnDate" in df.columns:
        df["TxnDate"] = pd.to_datetime(df["TxnDate"], errors="coerce")

    for col in ["Debit", "Credit", "AccountNumber", "Balance"]:
        if col in df.columns:
            df[col] = _coerce_numeric_series(df[col])

    return df


def check_required_columns(df: pd.DataFrame, data_type: str = "GL") -> Tuple[bool, List[str]]:
    """Check if required columns are present (same requirements for TB and GL in this app)."""
    required = ["TxnDate", "AccountNumber", "AccountName", "Debit", "Credit"]
    missing = [c for c in required if c not in df.columns]
    return (len(missing) == 0), missing


def _tolerance(max_amount: float, tolerance_abs: float, tolerance_rel: float) -> float:
    return float(max(tolerance_abs, max_amount * tolerance_rel))


# -----------------------------
# TB validation
# -----------------------------

def validate_trial_balance(
    df: pd.DataFrame,
    tolerance_abs: float = 0.01,
    tolerance_rel: float = 0.0001
) -> List[Dict]:
    """
    Validate Trial Balance data.

    Requirements:
      - Must balance per period (TxnDate): sum(Debit) ≈ sum(Credit) within tolerance.
      - Overall totals should also balance.

    Returns: List[Dict] issues.
    """
    issues: List[Dict] = []

    if df is None or len(df) == 0:
        return issues

    df = _normalize_types(df)

    # Check required columns
    ok, missing = check_required_columns(df, "TB")
    if not ok:
        issues.append({
            "severity": "Critical",
            "category": "Missing Columns",
            "issue": f"Required columns missing: {', '.join(missing)}",
            "impact": "Cannot validate Trial Balance",
            "suggestion": "Ensure file has: TxnDate, AccountNumber, AccountName, Debit, Credit",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": 0,
        })
        return issues

    # Parsing issues (Debit/Credit not numeric)
    bad_amt = df["Debit"].isna() | df["Credit"].isna()
    bad_amt_count = int(bad_amt.sum())
    if bad_amt_count > 0:
        issues.append({
            "severity": "Warning",
            "category": "Parsing",
            "issue": f"{bad_amt_count} row(s) have non-numeric Debit/Credit after parsing",
            "impact": "TB balance checks may be unreliable for those rows",
            "suggestion": "Clean Debit/Credit formatting (remove $/commas/parentheses) or ensure valid numbers.",
            "auto_fix": "Attempted numeric coercion; remaining rows require upstream cleaning.",
            "affected_rows": df.loc[bad_amt].index.tolist()[:100],
            "total_affected": bad_amt_count,
        })

    # Drop rows without valid TxnDate (can't group by period)
    valid_date = df["TxnDate"].notna()
    if not valid_date.all():
        # We'll warn, but still validate remaining
        issues.append({
            "severity": "Warning",
            "category": "Missing Data",
            "issue": f"{int((~valid_date).sum())} row(s) have invalid/missing TxnDate",
            "impact": "Those rows are excluded from per-period TB balance checks",
            "suggestion": "Fix TxnDate formatting or remove invalid rows.",
            "auto_fix": None,
            "affected_rows": df.loc[~valid_date].index.tolist()[:100],
            "total_affected": int((~valid_date).sum()),
        })

    df_chk = df.loc[valid_date].copy()

    # Per-period balance
    grouped = df_chk.groupby("TxnDate", dropna=True).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    grouped["Difference"] = grouped["Debit"] - grouped["Credit"]
    grouped["Abs_Diff"] = grouped["Difference"].abs()
    grouped["Max_Amount"] = grouped[["Debit", "Credit"]].max(axis=1)
    grouped["Tol"] = grouped["Max_Amount"].apply(lambda x: _tolerance(x, tolerance_abs, tolerance_rel))

    unbalanced = grouped[grouped["Abs_Diff"] > grouped["Tol"]]
    if len(unbalanced) > 0:
        issues.append({
            "severity": "Critical",
            "category": "Trial Balance",
            "issue": f"TB does not balance for {len(unbalanced)} period(s)",
            "impact": "Financial statements will be inaccurate",
            "suggestion": "Review source data for these periods",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": int(len(unbalanced)),
            "sample_data": unbalanced[["TxnDate", "Debit", "Credit", "Difference"]].head(25),
            "detail": f"Periods out of balance: {unbalanced['TxnDate'].dt.strftime('%Y-%m-%d').tolist()}",
        })

    # Overall balance
    total_debit = float(df_chk["Debit"].sum(skipna=True))
    total_credit = float(df_chk["Credit"].sum(skipna=True))
    diff = abs(total_debit - total_credit)
    tol = _tolerance(max(total_debit, total_credit), tolerance_abs, tolerance_rel)

    if diff > tol:
        issues.append({
            "severity": "Critical",
            "category": "Trial Balance",
            "issue": f"Overall TB out of balance by ${diff:,.2f}",
            "impact": f"Total Debits: ${total_debit:,.2f} ≠ Total Credits: ${total_credit:,.2f}",
            "suggestion": "Review all entries / export settings from source system",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": 0,
        })

    return issues


# -----------------------------
# GL validation
# -----------------------------

def validate_gl_activity(
    df: pd.DataFrame,
    tolerance_abs: float = 0.01,
    tolerance_rel: float = 0.0001
) -> List[Dict]:
    """
    Validate GL Activity data.

    Requirements:
      - If TransactionID exists and is sufficiently populated: validate per transaction (Debit≈Credit).
      - Always validate overall totals.

    Returns: List[Dict] issues.
    """
    issues: List[Dict] = []

    if df is None or len(df) == 0:
        return issues

    df = _normalize_types(df)

    # Check required columns
    ok, missing = check_required_columns(df, "GL")
    if not ok:
        issues.append({
            "severity": "Critical",
            "category": "Missing Columns",
            "issue": f"Required columns missing: {', '.join(missing)}",
            "impact": "Cannot validate GL Activity",
            "suggestion": "Ensure file has: TxnDate, AccountNumber, AccountName, Debit, Credit",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": 0,
        })
        return issues

    # Parsing issues (Debit/Credit not numeric)
    bad_amt = df["Debit"].isna() | df["Credit"].isna()
    bad_amt_count = int(bad_amt.sum())
    if bad_amt_count > 0:
        issues.append({
            "severity": "Critical",
            "category": "Parsing",
            "issue": f"{bad_amt_count} row(s) have non-numeric Debit/Credit after parsing",
            "impact": "GL balancing checks may be invalid",
            "suggestion": "Clean Debit/Credit formatting (remove $/commas/parentheses) or ensure valid numbers.",
            "auto_fix": "Attempted numeric coercion; remaining rows require upstream cleaning.",
            "affected_rows": df.loc[bad_amt].index.tolist()[:100],
            "total_affected": bad_amt_count,
        })

    # Determine transaction-level capability
    has_txnid = "TransactionID" in df.columns
    if has_txnid:
        non_null_pct = float(df["TransactionID"].notna().sum()) / float(len(df))
        if non_null_pct < 0.5:
            issues.append({
                "severity": "Warning",
                "category": "Data Quality",
                "issue": f"TransactionID exists but only {non_null_pct:.0%} populated",
                "impact": "Transaction-level balancing disabled; using overall-file balancing only",
                "suggestion": "Provide TransactionID for most rows to enable stronger validation",
                "auto_fix": None,
                "affected_rows": [],
                "total_affected": 0,
            })
            has_txnid = False
    else:
        issues.append({
            "severity": "Info",
            "category": "Data Quality",
            "issue": "TransactionID column not found",
            "impact": "Transaction-level balancing unavailable; using overall-file balancing only",
            "suggestion": "Include TransactionID if you want per-transaction balancing checks",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": 0,
        })

    # Transaction-level balance check
    if has_txnid:
        txn_df = df[df["TransactionID"].notna()].copy()
        grouped = txn_df.groupby("TransactionID").agg({"Debit": "sum", "Credit": "sum"}).reset_index()
        grouped["Difference"] = grouped["Debit"] - grouped["Credit"]
        grouped["Abs_Diff"] = grouped["Difference"].abs()
        grouped["Max_Amount"] = grouped[["Debit", "Credit"]].max(axis=1)
        grouped["Tol"] = grouped["Max_Amount"].apply(lambda x: _tolerance(x, tolerance_abs, tolerance_rel))

        unbalanced = grouped[grouped["Abs_Diff"] > grouped["Tol"]]
        if len(unbalanced) > 0:
            issues.append({
                "severity": "Critical",
                "category": "Transaction Balance",
                "issue": f"{len(unbalanced)} transaction(s) do not balance",
                "impact": "Debits ≠ Credits for these transactions",
                "suggestion": "Fix the source transactions (or export logic) so each transaction nets to 0",
                "auto_fix": None,
                "affected_rows": [],
                "total_affected": int(len(unbalanced)),
                "sample_data": unbalanced.head(25)[["TransactionID", "Debit", "Credit", "Difference"]],
            })

    # Overall balance check
    total_debit = float(df["Debit"].sum(skipna=True))
    total_credit = float(df["Credit"].sum(skipna=True))
    diff = abs(total_debit - total_credit)
    tol = _tolerance(max(total_debit, total_credit), tolerance_abs, tolerance_rel)

    if diff > tol:
        # If we have txn-level data, we downgrade to Warning because txn-level already calls out exact problems.
        severity = "Warning" if has_txnid else "Critical"
        issues.append({
            "severity": severity,
            "category": "Overall Balance",
            "issue": f"Overall GL out of balance by ${diff:,.2f}",
            "impact": f"Total Debits: ${total_debit:,.2f} ≠ Total Credits: ${total_credit:,.2f}",
            "suggestion": "Check export completeness (missing lines) or parsing of Debit/Credit columns",
            "auto_fix": None,
            "affected_rows": [],
            "total_affected": 0,
        })

    return issues


# -----------------------------
# Common checks + Auto-fixes
# -----------------------------

def validate_common_issues(df: pd.DataFrame) -> List[Dict]:
    """
    Validate common data quality issues.

    - Missing dates
    - Missing account numbers
    - Invalid account numbers
    - Duplicates (TransactionID)
    - Future dates
    """
    issues: List[Dict] = []
    if df is None or len(df) == 0:
        return issues

    df = _normalize_types(df)

    # Missing dates
    if "TxnDate" in df.columns:
        missing_dates = df["TxnDate"].isna()
        if int(missing_dates.sum()) > 0:
            rows = df[missing_dates].index.tolist()
            issues.append({
                "severity": "Warning",
                "category": "Missing Data",
                "issue": f"{int(missing_dates.sum())} row(s) missing/invalid TxnDate",
                "impact": "Cannot determine period for those rows",
                "suggestion": "Fix TxnDate formatting or remove rows",
                "auto_fix": "remove_missing_dates",
                "affected_rows": rows[:100],
                "total_affected": len(rows),
            })

    # Missing / invalid account numbers
    if "AccountNumber" in df.columns:
        missing_acct = df["AccountNumber"].isna()
        if int(missing_acct.sum()) > 0:
            rows = df[missing_acct].index.tolist()
            issues.append({
                "severity": "Critical",
                "category": "Missing Data",
                "issue": f"{int(missing_acct.sum())} row(s) without AccountNumber",
                "impact": "Cannot map categories for those rows",
                "suggestion": "Provide AccountNumber or map to 9999 (Unclassified)",
                "auto_fix": "map_unclassified",
                "affected_rows": rows[:100],
                "total_affected": len(rows),
            })

        valid_accts = df["AccountNumber"].notna()
        invalid_acct = (df.loc[valid_accts, "AccountNumber"] < 0) | (df.loc[valid_accts, "AccountNumber"] > 99999)
        if int(invalid_acct.sum()) > 0:
            rows = df.loc[valid_accts].loc[invalid_acct].index.tolist()
            issues.append({
                "severity": "Critical",
                "category": "Data Quality",
                "issue": f"{int(invalid_acct.sum())} invalid AccountNumber value(s)",
                "impact": "Mapping errors likely",
                "suggestion": "Fix account numbers (no negatives; within expected range)",
                "auto_fix": "fix_account_numbers",
                "affected_rows": rows[:100],
                "total_affected": len(rows),
            })

    # Duplicates (TransactionID)
    if "TransactionID" in df.columns:
        duplicates = df.duplicated(subset=["TransactionID"], keep=False)
        if int(duplicates.sum()) > 0:
            rows = df[duplicates].index.tolist()
            issues.append({
                "severity": "Warning",
                "category": "Duplicates",
                "issue": f"{int(duplicates.sum())} duplicated TransactionID row(s)",
                "impact": "May double-count transactions",
                "suggestion": "Remove duplicate rows or fix TransactionID export",
                "auto_fix": "remove_duplicates",
                "affected_rows": rows[:100],
                "total_affected": len(rows),
            })

    # Future dates
    if "TxnDate" in df.columns:
        now = pd.Timestamp.now()
        future_dates = df["TxnDate"] > now
        if int(future_dates.sum()) > 0:
            rows = df[future_dates].index.tolist()
            issues.append({
                "severity": "Warning",
                "category": "Data Quality",
                "issue": f"{int(future_dates.sum())} future-dated row(s)",
                "impact": "May skew current period",
                "suggestion": "Correct dates or remove rows",
                "auto_fix": "remove_future_dates",
                "affected_rows": rows[:100],
                "total_affected": len(rows),
            })

    return issues


def apply_auto_fixes(df: pd.DataFrame, selected_fixes: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Apply selected auto-fixes to TB/GL data safely.
    Returns: (df_fixed, changes_log)
    """
    df = df.copy()
    df = _normalize_types(df)

    changes: List[str] = []

    # remove_missing_dates
    if "remove_missing_dates" in selected_fixes and "TxnDate" in df.columns:
        before = len(df)
        df = df[df["TxnDate"].notna()]
        removed = before - len(df)
        if removed > 0:
            changes.append(f"Removed {removed} rows with missing/invalid TxnDate")

    # remove_future_dates
    if "remove_future_dates" in selected_fixes and "TxnDate" in df.columns:
        before = len(df)
        now = pd.Timestamp.now()
        df = df[df["TxnDate"] <= now]
        removed = before - len(df)
        if removed > 0:
            changes.append(f"Removed {removed} rows with future TxnDate")

    # map_unclassified
    if "map_unclassified" in selected_fixes and "AccountNumber" in df.columns:
        missing = df["AccountNumber"].isna()
        count = int(missing.sum())
        if count > 0:
            df.loc[missing, "AccountNumber"] = 9999
            changes.append(f"Mapped {count} missing AccountNumber to 9999 (Unclassified)")

    # fix_account_numbers (convert negative to positive)
    if "fix_account_numbers" in selected_fixes and "AccountNumber" in df.columns:
        neg = df["AccountNumber"].notna() & (df["AccountNumber"] < 0)
        count = int(neg.sum())
        if count > 0:
            df.loc[neg, "AccountNumber"] = df.loc[neg, "AccountNumber"].abs()
            changes.append(f"Converted {count} negative AccountNumber value(s) to positive")

    # remove_duplicates (TransactionID)
    if "remove_duplicates" in selected_fixes and "TransactionID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["TransactionID"], keep="first")
        removed = before - len(df)
        if removed > 0:
            changes.append(f"Removed {removed} duplicate TransactionID row(s) (kept first)")

    return df, changes


def validate_year0_opening_snapshot(tb_df: pd.DataFrame, statement_years: int = 3) -> List[str]:
    """
    Strict-mode validation: require an opening-balance Year0 snapshot in TB.

    Expectation:
      - Statement years are the latest `statement_years` years present in the dataset.
      - Year0 is (first statement year - 1) and must be present in TB.
      - TB can include monthly snapshots; we only require at least one TxnDate in Year0.
    """
    issues: List[str] = []
    if tb_df is None or len(tb_df) == 0:
        return ["TB: empty (cannot validate Year0 opening snapshot)"]

    df = _normalize_types(tb_df)

    if "TxnDate" not in df.columns:
        return ["TB: missing TxnDate column (cannot validate Year0 opening snapshot)"]

    df = df[df["TxnDate"].notna()].copy()
    if df.empty:
        return ["TB: TxnDate column has no valid dates (cannot validate Year0 opening snapshot)"]

    years = sorted(df["TxnDate"].dt.year.unique())
    if len(years) < statement_years + 1:
        return [f"TB: only {len(years)} year(s) found; expected at least {statement_years}+1 (includes Year0) in strict mode"]

    stmt_years = years[-int(statement_years):]
    year0 = int(stmt_years[0]) - 1
    if year0 not in years:
        issues.append(f"TB: missing Year0 opening snapshot year {year0}. Add prior-year year-end snapshot (at least one row dated in {year0}).")

    return issues
