import os
import subprocess
import pandas as pd
from pathlib import Path

def get_project_root():
    return Path(__file__).resolve().parent.parent

def load_data():
    project_root = get_project_root()
    data_path = project_root / 'processed_data' / 'complete_logs.pkl'
    
    if not data_path.exists():
        print("Data not found. Running ingestion pipeline...")
        ingestion_script = project_root / 'ingestion_pipeline' / 'main.py'
        
        # Make sure the script exists
        if not ingestion_script.exists():
            raise FileNotFoundError(f"Ingestion script not found at {ingestion_script}")
            
        # Run the ingestion script
        subprocess.run(['python', str(ingestion_script)], check=True, cwd=str(project_root))
        
        if not data_path.exists():
            raise FileNotFoundError(f"Pipeline finished but {data_path} still not found.")
            
    print(f"Loading data from {data_path}...")
    df = pd.read_pickle(str(data_path))
    return df
