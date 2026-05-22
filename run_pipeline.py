import subprocess
import sys
import os

def run_step(command, description):
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Executing: {' '.join(command)}")
    print(f"{'='*60}\n")
    
    try:
        # Run the command and wait for it to complete
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Step failed: {description}")
        print(f"Command returned non-zero exit status: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n[INFO] Process interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    # Ensure we are executing from the root of the project
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("Starting End-to-End Pipeline...")

    # Step 1: Data Generation
    generate_script = os.path.join("scripts", "generate_logs.py")
    run_step(
        [sys.executable, generate_script],
        "Data Generation"
    )

    # Step 2: Data Ingestion
    ingestion_script = os.path.join("ingestion_pipeline", "main.py")
    run_step(
        [sys.executable, ingestion_script],
        "Data Ingestion"
    )

    # Step 3: Analytics Dashboard
    dashboard_script = os.path.join("analytics", "app.py")
    run_step(
        [sys.executable, "-m", "streamlit", "run", dashboard_script],
        "Analytics Dashboard"
    )

if __name__ == "__main__":
    main()
