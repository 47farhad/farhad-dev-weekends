import os
import sys
import pandas as pd
from parser import parse_line

def process_logs(input_filepath, output_dir, chunk_size=500):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_data = []
    all_data = []
    chunk_index = 1
    total_processed = 0
    total_skipped = 0

    print(f"Reading logs from: {input_filepath}")
    print(f"Saving DataFrames to: {output_dir}")

    with open(input_filepath, 'r') as f:
        for line in f:
            parsed = parse_line(line)
            if parsed is None:
                # Random noise skipped
                total_skipped += 1
                continue
                
            chunk_data.append(parsed)
            all_data.append(parsed)
            total_processed += 1

            if len(chunk_data) == chunk_size:
                save_chunk(chunk_data, output_dir, chunk_index)
                chunk_index += 1
                chunk_data = []

    # Save remaining
    if chunk_data:
        save_chunk(chunk_data, output_dir, chunk_index)

    print(f"Finished processing!")
    print(f"Total lines ingested into DataFrames: {total_processed}")
    print(f"Total lines skipped (random noise): {total_skipped}")
    print(f"Total DataFrame chunks generated: {chunk_index if chunk_data else chunk_index - 1}")

    # Build and save complete DataFrame
    if all_data:
        complete_df = pd.DataFrame(all_data)
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


def save_chunk(data, output_dir, chunk_index):
    df = pd.DataFrame(data)
    
    # Ensure correct types or consistency where needed.
    # Latency and Status can sometimes be strings or objects due to None/missing values,
    # but pandas handles this gracefully.
    
    output_path = os.path.join(output_dir, f"chunk_{chunk_index:04d}.pkl")
    df.to_pickle(output_path)


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
