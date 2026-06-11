import subprocess
import sys
import os

def run_project_pipeline():
    # Sequence of scripts in the pipeline
    scripts = [
        "src/data_generator.py",
        "src/etl_pipeline.py",
        "src/db_loader.py",
        "src/alert_reporter.py"
    ]
    
    print("==================================================")
    print("STARTING END-TO-END MIS DASHBOARD PIPELINE RUN")
    print("==================================================")
    
    # Check if we are running in the correct directory
    if not os.path.exists("src/data_generator.py"):
        print("Error: Please run this script from the project root directory where 'src/' resides.")
        sys.exit(1)
        
    for script in scripts:
        print(f"\n[+] Executing: {script}")
        print("-" * 50)
        
        # Run script using the active Python executable
        result = subprocess.run([sys.executable, script])
        
        if result.returncode != 0:
            print(f"\n[-] Pipeline failed at step: {script} (Exit Code: {result.returncode})")
            sys.exit(1)
            
    print("\n==================================================")
    print("PIPELINE RUN COMPLETED SUCCESSFULLY!")
    print("All datasets generated, cleaned, loaded, and reports sent.")
    print("==================================================")

if __name__ == "__main__":
    run_project_pipeline()
