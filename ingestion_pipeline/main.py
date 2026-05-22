import os
import sys
import pandas as pd
from parser import parse_line

def process_logs(input_filepath, output_dir, chunk_size=500):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_data = []
    complete_df = pd.DataFrame()
    total_processed = 0
    total_skipped = 0
    updates_count = 0

    print(f"Reading logs from: {input_filepath}")
    print(f"Saving DataFrame to: {output_dir}")

    with open(input_filepath, 'r') as f:
        for line in f:
            parsed = parse_line(line)
            if parsed is None:
                # Random noise skipped
                total_skipped += 1
                continue
                
            chunk_data.append(parsed)
            total_processed += 1

            if len(chunk_data) == chunk_size:
                new_df = pd.DataFrame(chunk_data)
                complete_df = pd.concat([complete_df, new_df], ignore_index=True) if not complete_df.empty else new_df
                chunk_data = []
                updates_count += 1

    # Process remaining
    if chunk_data:
        new_df = pd.DataFrame(chunk_data)
        complete_df = pd.concat([complete_df, new_df], ignore_index=True) if not complete_df.empty else new_df
        updates_count += 1

    print(f"Finished processing!")
    print(f"Total lines ingested into DataFrame: {total_processed}")
    print(f"Total lines skipped (random noise): {total_skipped}")
    print(f"Total DataFrame updates: {updates_count}")

    # Process and save complete DataFrame
    if not complete_df.empty:
        # Ensure correct string types for complete DataFrame too
        string_cols = ['raw_line', 'ip', 'method', 'path']
        for col in string_cols:
            if col in complete_df.columns:
                complete_df[col] = complete_df[col].astype("string")
                
        complete_output_path = os.path.join(output_dir, "complete_logs.pkl")
        complete_df.to_pickle(complete_output_path)
        print(f"\nSaved complete DataFrame to: {complete_output_path}")
        
        # Display analysis output to the console
        print("\n" + "=" * 50)
        print("RESULTANT DATAFRAME HEAD")
        print("=" * 50)
        print(complete_df.head(10))
        
        print("\n" + "=" * 50)
        print("RESULTANT DATAFRAME DESCRIPTION")
        print("=" * 50)
        print(complete_df.describe(include='all'))
        
        print("\n" + "=" * 50)
        print("RESULTANT DATAFRAME INFO")
        print("=" * 50)
        complete_df.info()
        print("=" * 50 + "\n")


if __name__ == "__main__":
    # Define paths relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_log = os.path.join(project_root, 'data', 'mock_server_logs.txt')
    out_dir = os.path.join(project_root, 'processed_data')
    
    if not os.path.exists(input_log):
        print(f"Error: Log file not found at {input_log}")
        sys.exit(1)
        
    process_logs(input_log, out_dir, chunk_size=500)
