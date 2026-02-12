"""Three Statements Automation - Streamlit App (patched)
Focus:
- TB + GL must be treated as a set for generation.
- Validation section is always visible and detailed.
- Auto-fix is user-controlled (accept/reject) instead of silently applied.
- Demo controls:
  1) Download Sample Financial Model (SAMPLE_DEMO template)
  2) Download Sample Dataset (current loaded TB+GL as a zip)
  3) Load Random Sample Set (TB+GL together, matched years)
"""

import io
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

from validation import (
    validate_trial_balance,
    validate_gl_activity,
    apply_auto_fixes,
    validate_year0_opening_snapshot,
    add_year0_snapshot,
)
from mapping import map_accounts
from excel_writer import (
    calculate_3statements_from_tb_gl,
    calculate_financial_statements,
    write_financial_data_to_template,
    compute_reconciliation_checks,
)
from sample_data import get_sample_data_path, get_template_path


# ----------------------------
# Config / defaults
# ----------------------------
st.set_page_config(page_title="AI Accounting Agent", layout="wide")

AUTO_FIX_OPTIONS = [
    ("remove_missing_dates", "Remove rows with missing TxnDate"),
    ("remove_future_dates", "Remove rows with future TxnDate"),
    ("map_unclassified", "Map missing AccountNumber → 9999"),
    ("fix_account_numbers", "Convert negative AccountNumber → positive"),
    ("remove_duplicates", "Remove fully duplicate rows (safe)"),
]

UNIT_SCALE_OPTIONS = {
    "USD (no scaling)": 1,
    "USD thousands (÷ 1000)": 1000,
}

# Session state init
for k, default in {
    "tb_df": None,
    "gl_df": None,
    "tb_name": None,
    "gl_name": None,
    "tb_changes": [],
    "gl_changes": [],
    "validation_tb": [],
    "validation_gl": [],
    "selected_fixes": [],
    "unit_scale": 1000,
    "strict_mode": True,
    "template_type": "zero",  # 'zero' or 'demo'
    "dataset_source": None,  # 'random' or 'upload'
}.items():
    if k not in st.session_state:
        st.session_state[k] = default


def _issues_to_table(issues):
    """Compact table for issue list."""
    rows = []
    for it in issues:
        rows.append({
            "severity": it.get("severity", ""),
            "category": it.get("category", ""),
            "issue": it.get("issue", ""),
            "impact": it.get("impact", ""),
            "suggestion": it.get("suggestion", ""),
            "auto_fix": it.get("auto_fix", ""),
        })
    return pd.DataFrame(rows)


def _count_by_severity(issues):
    counts = {"Critical": 0, "Warning": 0, "Info": 0}
    for it in issues:
        sev = it.get("severity", "Info")
        if sev not in counts:
            counts[sev] = 0
        counts[sev] += 1
    return counts


def run_validation():
    """Run validations and store results in session state."""
    tb_df = st.session_state["tb_df"]
    gl_df = st.session_state["gl_df"]

    tb_issues = validate_trial_balance(tb_df) if tb_df is not None else []
    gl_issues = validate_gl_activity(gl_df) if gl_df is not None else []

    st.session_state["validation_tb"] = tb_issues
    st.session_state["validation_gl"] = gl_issues

    return tb_issues, gl_issues


def load_random_set():
    """Load matched TB + GL backup sets by choosing one year-range and loading both files."""
    year_ranges = [(2020, 2022), (2021, 2023), (2022, 2024), (2023, 2025), (2024, 2026)]
    import random
    y0, y1 = random.choice(year_ranges)
    tb_file = f"backup_tb_{y0}_{y1}.csv"
    gl_file = f"backup_gl_{y0}_{y1}_with_txnid.csv"

    tb_path = get_sample_data_path(tb_file)
    gl_path = get_sample_data_path(gl_file)

    tb_df = pd.read_csv(tb_path)
    gl_df = pd.read_csv(gl_path)

    st.session_state["tb_df"] = tb_df
    st.session_state["gl_df"] = gl_df
    st.session_state["tb_name"] = tb_file
    st.session_state["gl_name"] = gl_file
    st.session_state["tb_changes"] = []
    st.session_state["gl_changes"] = []
    st.session_state["dataset_source"] = "random"

    run_validation()


def dataset_zip_bytes(tb_df: pd.DataFrame, gl_df: pd.DataFrame, tb_name: str, gl_name: str) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(tb_name or "tb.csv", tb_df.to_csv(index=False))
        zf.writestr(gl_name or "gl.csv", gl_df.to_csv(index=False))
    bio.seek(0)
    return bio.read()


# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.header("Demo")

    # A1) Download sample financial model (demo template)
    demo_template_path = get_template_path("demo")
    try:
        with open(demo_template_path, "rb") as f:
            st.download_button(
                "Download Sample Financial Model",
                data=f.read(),
                file_name="Financial_Model_SAMPLE_DEMO_USD_thousands_GAAP.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    except Exception as e:
        st.caption(f"Could not load demo template: {e}")

    # A3) Load random sample set (TB+GL together)
    if st.button("Load Random Sample Set (TB + GL, 3 years)"):
        load_random_set()

    # A2) Download current dataset (TB+GL zip)
    if st.session_state["tb_df"] is not None and st.session_state["gl_df"] is not None:
        zbytes = dataset_zip_bytes(
            st.session_state["tb_df"],
            st.session_state["gl_df"],
            st.session_state["tb_name"] or "tb.csv",
            st.session_state["gl_name"] or "gl.csv",
        )
        st.download_button(
            "Download Sample Dataset (TB + GL)",
            data=zbytes,
            file_name="sample_dataset_tb_gl.zip",
            mime="application/zip",
        )
    else:
        st.caption("Load a dataset first to enable dataset download.")

    st.divider()
    st.header("Inputs")

    tb_up = st.file_uploader("Upload TB (CSV)", type=["csv"], key="tb_uploader")
    gl_up = st.file_uploader("Upload GL (CSV)", type=["csv"], key="gl_uploader")

    if tb_up is not None:
        st.session_state["tb_df"] = pd.read_csv(tb_up)
        st.session_state["tb_name"] = getattr(tb_up, "name", "tb.csv")
        st.session_state["tb_changes"] = []
        st.session_state["dataset_source"] = "upload"
        run_validation()

    if gl_up is not None:
        st.session_state["gl_df"] = pd.read_csv(gl_up)
        st.session_state["gl_name"] = getattr(gl_up, "name", "gl.csv")
        st.session_state["gl_changes"] = []
        st.session_state["dataset_source"] = "upload"
        run_validation()

    st.divider()
    st.header("Settings")

    # Unit scale (you asked for 2-level, not free numeric)
    unit_label = st.radio("Unit scale (divide by)", list(UNIT_SCALE_OPTIONS.keys()), index=1)
    st.session_state["unit_scale"] = UNIT_SCALE_OPTIONS[unit_label]

    st.session_state["strict_mode"] = st.checkbox("Strict mode", value=st.session_state["strict_mode"])

    # Template type kept but tucked away (you said the picker isn't very useful)
    with st.expander("Advanced: template selection"):
        template_label = st.radio("Excel template", ["ZERO (processing)", "SAMPLE (demo)"], index=0)
        st.session_state["template_type"] = "zero" if template_label.startswith("ZERO") else "demo"


# ----------------------------
# Main UI
# ----------------------------
st.title("AI Accounting Agent — GL → 3-Statement Demo")

tb_df = st.session_state["tb_df"]
gl_df = st.session_state["gl_df"]

col1, col2 = st.columns(2)
with col1:
    st.subheader("Trial Balance (TB)")
    if tb_df is None:
        st.info("No TB loaded yet.")
    else:
        st.caption(f"Loaded: {st.session_state['tb_name']}")
        st.dataframe(tb_df.head(20), use_container_width=True)

with col2:
    st.subheader("General Ledger (GL)")
    if gl_df is None:
        st.info("No GL loaded yet.")
    else:
        st.caption(f"Loaded: {st.session_state['gl_name']}")
        st.dataframe(gl_df.head(20), use_container_width=True)


# ----------------------------
# Validation + auto-fix (this is the section you said must NOT disappear)
# ----------------------------
tb_issues = st.session_state.get("validation_tb", []) or []
gl_issues = st.session_state.get("validation_gl", []) or []

tb_counts = _count_by_severity(tb_issues)
gl_counts = _count_by_severity(gl_issues)

banner_parts = []
if tb_df is not None:
    banner_parts.append(f"TB [Critical]: {tb_counts.get('Critical',0)} [Warning]: {tb_counts.get('Warning',0)} [Info]: {tb_counts.get('Info',0)}")
if gl_df is not None:
    banner_parts.append(f"GL [Critical]: {gl_counts.get('Critical',0)} [Warning]: {gl_counts.get('Warning',0)} [Info]: {gl_counts.get('Info',0)}")

if banner_parts:
    st.warning("Validation issues found: " + " | ".join(banner_parts))

with st.expander("Validation details", expanded=True):
    # TB
    st.markdown("### Trial Balance (TB)")
    if tb_df is None:
        st.caption("No TB loaded.")
    elif not tb_issues:
        st.success("No TB validation issues.")
    else:
        st.dataframe(_issues_to_table(tb_issues), use_container_width=True)
        for idx, it in enumerate(tb_issues[:20], start=1):
            with st.expander(f"TB Issue {idx}: {it.get('issue','')}"):
                st.markdown(f"**Severity:** {it.get('severity','')}  |  **Category:** {it.get('category','')}")
                if it.get("impact"): st.markdown(f"**Impact:** {it.get('impact')}")
                if it.get("suggestion"): st.markdown(f"**Suggestion:** {it.get('suggestion')}")
                if it.get("auto_fix"): st.markdown(f"**Auto-fix option:** `{it.get('auto_fix')}`")
                if "sample_data" in it and it["sample_data"] is not None:
                    st.dataframe(it["sample_data"], use_container_width=True)

    st.divider()

    # GL
    st.markdown("### General Ledger (GL)")
    if gl_df is None:
        st.caption("No GL loaded.")
    elif not gl_issues:
        st.success("No GL validation issues.")
    else:
        st.dataframe(_issues_to_table(gl_issues), use_container_width=True)
        for idx, it in enumerate(gl_issues[:20], start=1):
            with st.expander(f"GL Issue {idx}: {it.get('issue','')}"):
                st.markdown(f"**Severity:** {it.get('severity','')}  |  **Category:** {it.get('category','')}")
                if it.get("impact"): st.markdown(f"**Impact:** {it.get('impact')}")
                if it.get("suggestion"): st.markdown(f"**Suggestion:** {it.get('suggestion')}")
                if it.get("auto_fix"): st.markdown(f"**Auto-fix option:** `{it.get('auto_fix')}`")
                if "sample_data" in it and it["sample_data"] is not None:
                    st.dataframe(it["sample_data"], use_container_width=True)

    st.divider()

    # Auto-fix controls (accept/reject)
    st.markdown("### Auto-fix (accept/reject)")
    detected_fixes = sorted({it.get("auto_fix") for it in (tb_issues + gl_issues) if it.get("auto_fix")})
    if not detected_fixes:
        st.caption("No auto-fixes suggested by the current validation results.")
    else:
        fix_labels = {code: label for code, label in AUTO_FIX_OPTIONS}
        default_selected = [f for f in detected_fixes if f != "remove_duplicates"]  # safer default
        selected = st.multiselect(
            "Select fixes to apply",
            options=detected_fixes,
            default=default_selected,
            format_func=lambda x: f"{x} — {fix_labels.get(x, '')}",
        )

        cA, cB = st.columns([1, 1])
        with cA:
            if st.button("Apply selected fixes"):
                if tb_df is not None:
                    fixed, changes = apply_auto_fixes(tb_df, selected_fixes=selected)
                    st.session_state["tb_df"] = fixed
                    st.session_state["tb_changes"] = changes
                if gl_df is not None:
                    fixed, changes = apply_auto_fixes(gl_df, selected_fixes=selected)
                    st.session_state["gl_df"] = fixed
                    st.session_state["gl_changes"] = changes
                run_validation()
                st.success("Applied selected fixes and re-ran validation.")
        with cB:
            if st.button("Re-run validation"):
                run_validation()
                st.info("Re-ran validation.")

        if st.session_state.get("tb_changes"):
            st.caption("TB auto-fixes applied:")
            st.write(st.session_state["tb_changes"])
        if st.session_state.get("gl_changes"):
            st.caption("GL auto-fixes applied:")
            st.write(st.session_state["gl_changes"])


# ----------------------------
# Generation
# ----------------------------
st.divider()
st.header("Generate Outputs")

strict_mode = st.session_state["strict_mode"]

if st.button("Generate 3-Statement Outputs", type="primary"):
    # Require TB + GL as a set for generation
    if tb_df is None or gl_df is None:
        st.error("TB and GL must be loaded as a set to generate the 3-statement output.")
        st.stop()

    # Strict mode gate: fail if any Critical issues remain
    tb_issues, gl_issues = run_validation()
    crit = [it for it in (tb_issues + gl_issues) if it.get("severity") == "Critical"]
    if strict_mode and crit:
        st.error("Strict mode: Critical validation issues must be resolved before generation. See Validation details above.")
        st.stop()

    # Year0 strict requirement
    if strict_mode:
        year0_issues = validate_year0_opening_snapshot(tb_df, statement_years=3)
        if year0_issues:
            # If the dataset came from the built-in random demo/backups, we can create an internal Year0 snapshot
            # (you asked for Year0 to exist for internal use). For user uploads, we do NOT synthesize Year0.
            if st.session_state.get("dataset_source") == "random":
                tb_fixed, msg = add_year0_snapshot(tb_df, statement_years=3)
                st.session_state["tb_df"] = tb_fixed
                tb_df = tb_fixed
                st.info(msg)
                run_validation()
                year0_issues = validate_year0_opening_snapshot(tb_df, statement_years=3)

            if year0_issues:
                st.error("Strict mode: Year0 opening snapshot requirement failed:\n" + "\n".join(year0_issues))
                st.stop()

    # Map accounts
    tb_mapped = map_accounts(tb_df)
    gl_mapped = map_accounts(gl_df)

    # Compute 3-statement data
    financial_data = calculate_3statements_from_tb_gl(tb_mapped, gl_mapped)

    # Write to template
    template_path = get_template_path(st.session_state["template_type"])
    out_bytes = write_financial_data_to_template(
        template_path=template_path,
        financial_data=financial_data,
        unit_scale=float(st.session_state["unit_scale"]),
    )

    # Persist output so Streamlit reruns don’t lose it
    st.session_state["last_excel_bytes"] = out_bytes.getvalue()

    # Build a simple preview (accounts on left, years on top) + include check rows
    try:
        years_all = sorted(financial_data.keys())
        stmt_years = years_all[1:] if len(years_all) > 1 else years_all
        preview_df = pd.DataFrame({y: financial_data[y] for y in stmt_years})
        checks = compute_reconciliation_checks(financial_data)
        preview_df.loc["CHECK_balance_sheet (should be 0)"] = [checks.get(y, {}).get("balance_sheet_check", 0.0) for y in stmt_years]
        preview_df.loc["CHECK_cashflow (should be 0)"] = [checks.get(y, {}).get("cashflow_check", 0.0) for y in stmt_years]
        st.session_state["preview_df"] = preview_df
    except Exception:
        st.session_state["preview_df"] = None

    st.success("Generated Excel output.")
    st.download_button(
        "Download Excel Output",
        data=out_bytes.getvalue(),
        file_name="3statement_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# Persisted output preview / download (survives reruns)
if st.session_state.get("last_excel_bytes"):
    st.download_button(
        "Download Excel Output (last run)",
        data=st.session_state["last_excel_bytes"],
        file_name="3statement_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_last_excel",
    )

if st.session_state.get("preview_df") is not None:
    st.subheader("3-Statement Output Preview")
    st.dataframe(st.session_state["preview_df"], use_container_width=True)