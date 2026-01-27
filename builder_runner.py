import subprocess
import sys
import os

def run_powershell_script(script_name):
    """Runs a powershell script and checks for errors."""
    if not os.path.exists(script_name):
        print(f"Error: {script_name} not found in {os.getcwd()}")
        return False
    
    print(f"--- Executing {script_name} ---")
    try:
        # Use the exact string command line for true terminal-like execution
        cmd = f"powershell -ExecutionPolicy Bypass -File .\\{script_name}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            check=False 
        )
        if result.returncode != 0:
            print(f"Error: {script_name} exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"Exception while running {script_name}: {e}")
        return False

def main():
    # Ensure we are in the script's directory (usually the repo root)
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(application_path)
    print(f"Working directory: {os.getcwd()}")

    if not run_powershell_script("compile.ps1"):
        print("Compilation failed. Aborting run.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    if not run_powershell_script("run.ps1"):
        print("Run execution failed.")
        input("Press Enter to exit...")
        sys.exit(1)

    print("--- Done ---")
    # Optional: Keep window open if run from double-click
    # input("Press Enter to exit...")

if __name__ == "__main__":
    main()
