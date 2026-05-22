import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px
import os

# Constants - dynamically compute the project root relative to the script location
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_FILE = PROJECT_ROOT / "processed_data" / "complete_logs.pkl"

st.set_page_config(page_title="On-Call Analytics Dashboard", page_icon="🚨", layout="wide")

@st.cache_data
def load_data():
    if DATA_FILE.exists():
        return pd.read_pickle(DATA_FILE)
    return None

def main():
    st.sidebar.title("Pipeline Health")
    
    df = load_data()
    
    if df is None:
        st.error("⚠️ Data checkpoints not found!")
        st.info("Please run the ingestion pipeline script first to generate `processed_data/complete_logs.pkl`.")
        st.stop()
        
    # --- A. SIDEBAR (Ingestion Health & Integrity Monitor) ---
    # We derive stats directly from the DataFrame since we don't have a separate metadata.json
    total_read = len(df)
    
    if 'is_corrupt' in df.columns:
        parsed_lines = len(df[~df['is_corrupt']])
        skipped_lines = len(df[df['is_corrupt']])
        anomalies_df = df[df['is_corrupt']]
    else:
        # Fallback if is_corrupt is not available
        parsed_lines = len(df)
        skipped_lines = 0
        anomalies_df = pd.DataFrame()
    
    st.sidebar.metric("Total Lines Read", f"{total_read:,}")
    st.sidebar.metric("Lines Successfully Parsed", f"{parsed_lines:,}")
    st.sidebar.metric(
        "Lines Skipped/Malformed", 
        f"{skipped_lines:,}", 
        delta=f"-{skipped_lines}" if skipped_lines > 0 else "0", 
        delta_color="inverse"
    )
    
    with st.sidebar.expander("View Raw Ingestion Anomalies"):
        if not anomalies_df.empty:
            # Show raw lines that were flagged as corrupt
            display_cols = ['raw_line']
            if 'status' in anomalies_df.columns: display_cols.append('status')
            if 'latency' in anomalies_df.columns: display_cols.append('latency')
            st.dataframe(anomalies_df[display_cols], use_container_width=True)
        else:
            st.success("No anomalies detected.")

    # Filter out corrupt lines for the main analytics
    valid_df = df[~df['is_corrupt']] if 'is_corrupt' in df.columns else df

    # --- B. MAIN PAGE: SECTION 1 (High-Level On-Call KPIs) ---
    st.title("🚨 System Telemetry Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    # 1. Total Request Volume (Valid requests)
    total_volume = len(valid_df)
    col1.metric("Total Request Volume", f"{total_volume:,}")
    
    # 2. Error Rate %
    if 'status' in valid_df.columns:
        valid_status = valid_df[valid_df['status'].notna()]
        if not valid_status.empty:
            errors = valid_status[valid_status['status'] >= 400]
            error_rate = (len(errors) / len(valid_status)) * 100
            col2.metric("Error Rate", f"{error_rate:.2f}%")
        else:
            col2.metric("Error Rate", "N/A")
    else:
        col2.metric("Error Rate", "N/A")
        
    # 3. Average Latency vs. P95 Latency
    if 'latency' in valid_df.columns:
        valid_latency = valid_df[valid_df['latency'].notna()]['latency']
        if not valid_latency.empty:
            avg_latency = valid_latency.mean()
            p95_latency = valid_latency.quantile(0.95)
            # Display Average Latency with P95 as a delta or help text
            col3.metric("Avg Latency (ms)", f"{avg_latency:.2f}", help=f"P95 Latency: {p95_latency:.2f} ms")
        else:
            col3.metric("Latency", "N/A")
    else:
         col3.metric("Latency", "N/A")
         
    st.markdown("---")
         
    # --- C. MAIN PAGE: SECTION 2 (Performance Bottlenecks) ---
    st.header("⏱️ Latency & Performance Analysis")
    
    if 'path' in valid_df.columns and 'latency' in valid_df.columns:
        # Top 10 Slowest Endpoints
        endpoint_stats = valid_df.groupby('path')['latency'].mean().reset_index()
        top_slowest = endpoint_stats.sort_values(by='latency', ascending=False).head(10)
        
        fig_latency = px.bar(
            top_slowest, 
            x='latency', 
            y='path', 
            orientation='h',
            title="Top 10 Slowest Endpoints (Avg Latency)",
            labels={'latency': 'Average Latency (ms)', 'path': 'Endpoint'},
            color='latency',
            color_continuous_scale='Reds'
        )
        fig_latency.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_latency, use_container_width=True)
    else:
        st.warning("Path or latency data is not available for performance analysis.")
        
    st.markdown("---")

    # --- D. MAIN PAGE: SECTION 3 (Traffic & Error Patterns) ---
    st.header("📊 Traffic Profiles")
    
    col_traffic, col_status = st.columns(2)
    
    with col_traffic:
        if 'timestamp' in valid_df.columns:
            # Ensure timestamp is datetime
            ts_data = valid_df.copy()
            if not pd.api.types.is_datetime64_any_dtype(ts_data['timestamp']):
                ts_data['timestamp'] = pd.to_datetime(ts_data['timestamp'], errors='coerce')
                
            # Drop rows with invalid timestamps for plotting
            ts_df = ts_data.dropna(subset=['timestamp'])
            if not ts_df.empty:
                volume_over_time = ts_df.set_index('timestamp').resample('1T').size().reset_index(name='requests')
                fig_time = px.line(
                    volume_over_time, 
                    x='timestamp', 
                    y='requests', 
                    title="Request Volume Over Time (per minute)"
                )
                st.plotly_chart(fig_time, use_container_width=True)
            else:
                st.warning("No valid timestamps available.")
        else:
            st.warning("Timestamp data not available.")
            
    with col_status:
        if 'status' in df.columns: # Use entire df to see the null statuses from corrupt rows if we want, or just valid_df
            # Handle float status codes (e.g., 200.0)
            status_series = df['status'].apply(lambda x: str(int(x)) if pd.notnull(x) and str(x).replace('.', '', 1).isdigit() else x)
            status_df = status_series.fillna("Unknown (-)").astype(str)
            status_counts = status_df.value_counts().reset_index()
            status_counts.columns = ['Status Code', 'Count']
            
            fig_status = px.pie(
                status_counts, 
                names='Status Code', 
                values='Count', 
                title="HTTP Status Code Distribution",
                hole=0.4
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.warning("Status code data not available.")

if __name__ == "__main__":
    main()
