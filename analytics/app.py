"""
On-Call Analytics Dashboard: Incident Triage & Observability
=============================================================
Reads processed log data from the ingestion pipeline and presents
actionable SRE metrics for rapid incident diagnosis.

Data sources (relative to project root):
  - processed_data/complete_logs.pkl   (Pandas DataFrame)
  - processed_data/metadata.json       (Ingestion stats & anomalies)
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_FILE = PROJECT_ROOT / "processed_data" / "complete_logs.pkl"
METADATA_FILE = PROJECT_ROOT / "processed_data" / "metadata.json"

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="On-Call Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# DATA LOADING (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_logs() -> pd.DataFrame | None:
    """Load the processed log DataFrame from the pickle checkpoint."""
    if not DATA_FILE.exists():
        return None
    df = pd.read_pickle(DATA_FILE)
    # Ensure timestamp is proper datetime (it already is, but safety first)
    if "timestamp" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


@st.cache_data
def load_metadata() -> dict | None:
    """Load the ingestion metadata JSON if available."""
    if not METADATA_FILE.exists():
        return None
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# METRIC HELPERS
# ---------------------------------------------------------------------------

def compute_error_rate(df: pd.DataFrame) -> float:
    """Percentage of 4xx/5xx responses among rows with a valid status code."""
    valid = df[df["status"].notna()]
    if valid.empty:
        return 0.0
    return (valid["status"] >= 400).mean() * 100


def compute_latency_percentiles(series: pd.Series) -> dict:
    """Return P50 / P90 / P99 from a latency Series (NaNs ignored)."""
    clean = series.dropna()
    if clean.empty:
        return {"P50": None, "P90": None, "P99": None}
    q = clean.quantile([0.50, 0.90, 0.99])
    return {"P50": q[0.50], "P90": q[0.90], "P99": q[0.99]}


def compute_blast_radius(df: pd.DataFrame) -> dict:
    """Unique IPs seeing 5xx vs total unique IPs."""
    total_ips = df["ip"].nunique()
    impacted = df[df["status"].ge(500)]["ip"].nunique()
    return {"impacted": impacted, "total": total_ips}


def compute_error_velocity(df: pd.DataFrame, bucket: str = "5min") -> dict:
    """
    Compare the error rate of the most recent time bucket against the
    historical baseline.  Returns the two rates and the %-point delta.
    """
    ts = df.set_index("timestamp")
    buckets = ts.resample(bucket)
    rates = buckets.apply(lambda g: (g["status"].ge(400).sum() / max(len(g), 1)) * 100)

    if len(rates) < 2:
        return {"latest": None, "baseline": None, "delta": 0.0}

    latest = rates.iloc[-1]
    baseline = rates.iloc[:-1].mean()
    delta = latest - baseline
    return {"latest": round(latest, 2), "baseline": round(baseline, 2), "delta": round(delta, 2)}


# ---------------------------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------------------------

def main():
    # ---- Load Data --------------------------------------------------------
    df = load_logs()
    meta = load_metadata()

    if df is None:
        st.error("Processed data not found.")
        st.info(
            "Run the ingestion pipeline first:\n\n"
            "```bash\ncd ingestion_pipeline && python main.py\n```\n\n"
            f"Expected file: `{DATA_FILE}`"
        )
        st.stop()

    # ---- Derive ingestion stats -------------------------------------------
    # If metadata.json exists, use it; otherwise derive from the DataFrame.
    if meta:
        stats = meta.get("stats", {})
        anomalies_list = meta.get("anomalies", [])
        total_read = stats.get("total", len(df))
        success_count = stats.get("success", int((~df["is_corrupt"]).sum()))
        skipped_count = stats.get("skipped", int(df["is_corrupt"].sum()))
    else:
        total_read = len(df)
        success_count = int((~df["is_corrupt"]).sum())
        skipped_count = int(df["is_corrupt"].sum())
        anomalies_list = []

    # Build an anomalies DataFrame from the corrupt rows so the sidebar
    # always has something to show even without metadata.json
    corrupt_df = df[df["is_corrupt"]].copy()

    # ---- Working set: non-corrupt rows ------------------------------------
    clean_df = df[~df["is_corrupt"]].copy()

    # ---- Pre-compute metrics -----------------------------------------------
    error_rate = compute_error_rate(clean_df)
    percentiles = compute_latency_percentiles(clean_df["latency"])
    blast = compute_blast_radius(clean_df)
    velocity = compute_error_velocity(clean_df)

    time_span = (clean_df["timestamp"].max() - clean_df["timestamp"].min()).total_seconds()
    rps = len(clean_df) / time_span if time_span > 0 else 0

    # ---- A. GLOBAL STATUS BANNER ------------------------------------------
    is_critical = error_rate > 5 or (velocity["delta"] is not None and velocity["delta"] > 20)
    if is_critical:
        st.error(
            "**CRITICAL:** "
            f"Error rate {error_rate:.1f}%"
            + (f", Error velocity spiked by {velocity['delta']:+.1f} pp" if velocity["delta"] and velocity["delta"] > 20 else "")
        )
    else:
        st.success("System operating within normal parameters")

    st.title("System Telemetry Dashboard")

    # ---- B. TRIAGE METRIC CARDS -------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Throughput",
        f"{len(clean_df):,} reqs",
        f"{rps:.1f} req/s",
    )
    c2.metric(
        "Error Rate (4xx + 5xx)",
        f"{error_rate:.2f}%",
    )
    c3.metric(
        "Blast Radius",
        f"{blast['impacted']:,} / {blast['total']:,} IPs",
        help="Unique IPs receiving 5xx server errors vs total unique IPs",
    )
    c4.metric(
        "P99 Latency",
        f"{percentiles['P99']:.0f} ms" if percentiles["P99"] else "N/A",
        help="99th-percentile latency: worst 1% of user experience",
    )

    st.markdown("---")

    # ---- C. DIAGNOSTIC TABS -----------------------------------------------
    tab_latency, tab_errors, tab_pipeline = st.tabs(
        ["Latency Analysis", "Error Hotspots", "Pipeline Integrity"]
    )

    # ── Tab 1: Latency Analysis ────────────────────────────────────────────
    with tab_latency:
        st.subheader("Latency Percentiles Over Time")

        ts_latency = clean_df.dropna(subset=["latency"]).set_index("timestamp")
        bucket_rule = "5min"  # sensible for ~24h of data

        p50 = ts_latency["latency"].resample(bucket_rule).quantile(0.50).rename("P50")
        p90 = ts_latency["latency"].resample(bucket_rule).quantile(0.90).rename("P90")
        p99 = ts_latency["latency"].resample(bucket_rule).quantile(0.99).rename("P99")

        pct_df = pd.concat([p50, p90, p99], axis=1).dropna().reset_index()

        fig_pct = go.Figure()
        fig_pct.add_trace(go.Scatter(x=pct_df["timestamp"], y=pct_df["P50"], name="P50 (Median)", line=dict(color="#22c55e", width=2)))
        fig_pct.add_trace(go.Scatter(x=pct_df["timestamp"], y=pct_df["P90"], name="P90", line=dict(color="#f59e0b", width=2)))
        fig_pct.add_trace(go.Scatter(x=pct_df["timestamp"], y=pct_df["P99"], name="P99", line=dict(color="#ef4444", width=2, dash="dot")))
        fig_pct.update_layout(
            xaxis_title="Time",
            yaxis_title="Latency (ms)",
            template="plotly_dark",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_pct, width="stretch")

        st.subheader("Top 10 Slowest Endpoints (P99 Latency)")
        p99_by_path = (
            clean_df.dropna(subset=["latency"])
            .groupby("path")["latency"]
            .quantile(0.99)
            .reset_index()
            .rename(columns={"latency": "p99_latency_ms"})
            .sort_values("p99_latency_ms", ascending=False)
            .head(10)
        )

        fig_ep = px.bar(
            p99_by_path,
            x="p99_latency_ms",
            y="path",
            orientation="h",
            labels={"p99_latency_ms": "P99 Latency (ms)", "path": "Endpoint"},
            color="p99_latency_ms",
            color_continuous_scale="Reds",
        )
        fig_ep.update_layout(
            yaxis={"categoryorder": "total ascending"},
            template="plotly_dark",
            height=400,
        )
        st.plotly_chart(fig_ep, width="stretch")

    # ── Tab 2: Error Hotspots ──────────────────────────────────────────────
    with tab_errors:
        st.subheader("Error Hotspot Matrix")

        err_df = clean_df[clean_df["status"].ge(400)].copy()

        # Interactive filters
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            methods = sorted(err_df["method"].dropna().unique())
            sel_methods = st.multiselect("Filter by HTTP Method", methods, default=methods)
        with filter_col2:
            range_opts = ["4xx (Client)", "5xx (Server)"]
            sel_ranges = st.multiselect("Filter by Status Range", range_opts, default=range_opts)

        # Apply filters
        mask = err_df["method"].isin(sel_methods)
        status_mask = pd.Series(False, index=err_df.index)
        if "4xx (Client)" in sel_ranges:
            status_mask |= err_df["status"].between(400, 499)
        if "5xx (Server)" in sel_ranges:
            status_mask |= err_df["status"].ge(500)
        mask &= status_mask

        filtered_err = err_df[mask]

        hotspot = (
            filtered_err.groupby(["path", "status"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        hotspot["status"] = hotspot["status"].astype(int).astype(str)

        st.dataframe(hotspot, width="stretch", height=450)

        # Visual heatmap
        if not hotspot.empty:
            st.subheader("Visual Heatmap")
            pivot = hotspot.pivot_table(index="path", columns="status", values="count", fill_value=0)
            fig_hm = px.imshow(
                pivot,
                labels=dict(x="Status Code", y="Endpoint", color="Count"),
                color_continuous_scale="YlOrRd",
                aspect="auto",
            )
            fig_hm.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig_hm, width="stretch")

    # ── Tab 3: Pipeline Integrity ──────────────────────────────────────────
    with tab_pipeline:
        st.subheader("Ingestion Health")

        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Total Lines Ingested", f"{total_read:,}")
        pc2.metric("Successfully Parsed", f"{success_count:,}")
        pc3.metric(
            "Skipped / Malformed",
            f"{skipped_count:,}",
            delta=f"-{skipped_count}" if skipped_count > 0 else "0",
            delta_color="inverse",
        )

        st.subheader("Ingestion Anomalies Log")

        # Prefer metadata.json anomalies if available; fall back to corrupt rows
        if anomalies_list:
            st.dataframe(pd.DataFrame(anomalies_list), width="stretch", height=400)
        elif not corrupt_df.empty:
            display_cols = ["raw_line", "status", "latency", "timestamp"]
            existing = [c for c in display_cols if c in corrupt_df.columns]
            show_df = corrupt_df[existing].copy()
            show_df.insert(0, "line_index", corrupt_df.index)
            # Truncate long raw lines for readability
            if "raw_line" in show_df.columns:
                show_df["raw_line"] = show_df["raw_line"].str.slice(0, 120)
            st.dataframe(show_df, width="stretch", height=400)
        else:
            st.success("No anomalies detected during ingestion.")

    # ---- SIDEBAR ----------------------------------------------------------
    with st.sidebar:
        st.title("Pipeline Health")
        st.metric("Total Lines", f"{total_read:,}")
        st.metric("Clean Rows", f"{success_count:,}")
        st.metric(
            "Corrupt Rows",
            f"{skipped_count:,}",
            delta=f"{skipped_count / total_read * 100:.1f}% of total" if total_read else "0",
            delta_color="inverse",
        )
        st.divider()

        st.subheader("Error Velocity")
        if velocity["latest"] is not None:
            st.metric(
                "Latest Bucket Error Rate",
                f"{velocity['latest']:.1f}%",
                delta=f"{velocity['delta']:+.1f} pp vs baseline",
                delta_color="inverse",
            )
            st.caption(f"Baseline (historical avg): {velocity['baseline']:.1f}%")
        else:
            st.info("Not enough time buckets to compute velocity.")

        st.divider()

        st.subheader("Latency Snapshot")
        for label, key in [("P50", "P50"), ("P90", "P90"), ("P99", "P99")]:
            val = percentiles[key]
            st.metric(label, f"{val:.0f} ms" if val else "N/A")

        st.divider()
        with st.expander("View Corrupt Row Samples"):
            if not corrupt_df.empty:
                st.dataframe(
                    corrupt_df[["raw_line"]].head(50),
                    width="stretch",
                )
            else:
                st.success("No corrupt rows.")


if __name__ == "__main__":
    main()
