# farhad-dev-weekends

This project is a complete end-to-end log data processing and analytics pipeline. It generates sample server logs, ingests and parses them into structured data, and provides an interactive dashboard for telemetry and analysis.

## Getting Started

Follow these steps to set up and run the project from scratch.

### 1. Install Dependencies

Ensure you have Python installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Run the Pipeline

The easiest way to run the entire project is using the included master script. This script will sequentially run the log generation, process the data via the ingestion pipeline, and launch the analytics dashboard.

```bash
python run_pipeline.py
```

---

## Modules Overview

If you prefer to run or interact with the components individually, the project is structured into three distinct modules.

### 1. Data Generation (`scripts/`)
This module is responsible for generating mock server logs, including simulated noise, anomalies, and variable latency.
* **Run manually:** `python scripts/generate_logs.py`
* **Output:** The generated log files are saved to the `data/` directory.

### 2. Data Ingestion (`ingestion_pipeline/`)
This module scans the `data/` directory for log files, parses the raw text, filters out malformed lines, and structures the valid entries into an aggregated pandas DataFrame.
* **Run manually:** `python ingestion_pipeline/main.py`
* **Output:** The structured DataFrame is saved into the `processed_data/` directory (e.g., `complete_logs.pkl`).
* **Bring Your Own Data:** You can place your own custom log files directly into the `data/` folder! The ingestion pipeline will automatically pick them up and process all log files present in that directory.

### 3. Analytics Dashboard (`analytics/`)
A Streamlit web application that reads the processed DataFrame and visualizes key SRE metrics such as throughput, latency percentiles, and error hotspots.
* **Run manually:** `streamlit run analytics/app.py`
