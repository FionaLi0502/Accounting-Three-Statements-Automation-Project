PACKAGE v5 (clean backups + true Trial Balance style)

Goal: sample datasets should NOT trigger any required fixes. They should be immediately usable for end-to-end runs.

Key change vs v4:
- TB files are now true Trial Balance style per period:
  For each (PeriodEnd, Account), EITHER Debit > 0 OR Credit > 0 (never both).
  This matches typical real-world TB exports and avoids “both debit & credit” validation issues.

SAMPLE DATA (PRIMARY)
- sample_tb.csv  : Trial Balance by month-end (net; single-sided). No TransactionID.
- sample_gl_with_txnid.csv : GL Activity with Journal Entry ID (TransactionID present and balanced per JE).
- sample_gl_no_txnid.csv   : GL Activity without TransactionID.

RANDOM TEST DATASETS (used by “Load Random Test Dataset”)
For each year range we include:
GL:
- backup_gl_<YYYY_YYYY>_with_txnid.csv  (TransactionID behaves like Journal Entry ID; all JEs balance)
- backup_gl_<YYYY_YYYY>_no_txnid.csv    (no TransactionID column)

TB:
- backup_tb_<YYYY_YYYY>.csv (month-end TB, net single-sided)

Validation expectation:
- No invalid/missing TxnDate.
- Currency = USD only (strict mode friendly).
- No negative Debit/Credit.
- No rows with both Debit and Credit > 0 (TB and GL).
- TB balances each period.
- GL balances overall.
- If TransactionID exists and is populated, each TransactionID group balances.

Column matching rule for app:
- Match by header name (case-insensitive), NOT column order.
- Extra columns ignored.
- Missing required columns -> warnings/critical depending on whether generation is possible.
