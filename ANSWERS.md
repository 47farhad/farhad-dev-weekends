# Data Ingestion and Log Analyzer Assessment

## Question 1: How to run

To spin up the project on a fresh machine, ensure you have **Python 3.10+** installed as a prerequisite.

1. **Install Dependencies:**
   Install the required libraries via a single command:

    ```bash
    pip install pandas streamlit plotly
    ```

2. **Execute the Pipeline Sequence:**
   Run the following sequence of commands to generate data, ingest it, and launch the dashboard:

    Generate the chaotic test data:

    ```bash
    python scripts/generate_logs.py
    ```

    Execute the resilient ingestion pipeline:

    ```bash
    python scripts/ingest_logs.py
    ```

    Launch the observability web UI:

    ```bash
    streamlit run app.py
    ```

## Question 2: Stack choice

**Why this stack:**
Python was selected for quick development, and since it has the pandas library which is great for handling data and I've used it before. Similarly I used streamlit for the dashboard as I'm familiar with it as well.

**What would be a worse choice and why:**
A fullstack application running the data ingestion on a separate backend would have been a bad choice. This project does not require such a client server architecture. Since the data is provided on the machine this is being run on, we can have a single system with all the features, eliminating any latencies or overheads.

## Question 3: One real edge case

**The Edge Case:**
A critical edge case handled successfully by the code occurs when parsing the latency column. The log lines contain variable time suffixes natively, mixing formats such as `142ms`, `0.142s`, and raw strings like `142`.

**The Handling:**
Inside `scripts/ingest_logs.py` (specifically within the `normalize_latency` function), the pipeline applies a resilient Regex wrapper to dynamically extract the raw numerical scale and the time suffix: `re.match(r"([\d\.]+)(ms|s)?", str(val))`. If the captured suffix matches `s`, the logic programmatically scales the floating-point number by `1000.0` to guarantee that the entire database column is cleanly normalized into milliseconds.

**What would happen without it:**
Without this exact handling, attempting to cast the raw string directly to an integer or float type would instantly trigger an unhandled `ValueError` when the parser encountered the 'ms' or 's' string tokens. This would crash the entire ingestion run mid-file, resulting in a total failure of the tool.

## Question 4: AI usage

**AI Assistance:**
Antigravity was used for majority of the development and low level implementations. However, all of the design and architectural choices were made by me. Such as what pipelines are gonna be here, what they're gonna do, what gets cached etc.

**What was changed and why:**
AI ran the whole pipeline every time the dashboard was to be opened up. I made it so there are 3 distinct modules (generation, ingestion, analytics) which store their progress (log file, df as pkl) after each step.
AI had some not so great project structure, fixed that as well to something I liked.
AI saved ingestion progress in chunks, I made it update the same pkl file every 500 lines. However thats the pkl ready for analytics, not a savepoint for the ingestion itself, as discussed in the limitation below

## Question 5: Honest gap

**The Gap:**
A genuine engineering limitation in the current iteration is that the ingestion pipeline performs its state-saving checkpoint _atomically_ at the very end of processing the log file. If the process is forcefully terminated or killed by an Out-Of-Memory (OOM) reaper at line 149,000 out of 150,000, all in-memory progress is lost, and the ingestion must restart entirely from line 1.

**The Solution:**
Given an additional 1 hour of development time, I would modify the line-by-line reader loop to utilize chunked streaming writes. Every 25,000 lines, the ingestion script would append the processed data batch to a local append-only Parquet file or store intermediary state markers. This enhancement would allow the ingestion tool to seamlessly resume from its last verified block offset upon a restart, rather than being forced to reprocess the entire historical log file from scratch.
