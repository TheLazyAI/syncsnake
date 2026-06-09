import os
import sys
import time
import subprocess
import argparse
from datetime import datetime, timedelta

STATUS_FILE = "runner_status.json"

def run_agent():
    """Spins up the deep research agent as a sub-process."""
    print(f"[{datetime.now().isoformat()}] Waking up research agent...")
    
    # Prefer a venv inside the project directory, fall back to sys.executable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_venv_python = os.path.join(script_dir, "venv", "bin", "python")
    venv_python = local_venv_python
    cfg_file = os.path.join(script_dir, "venv", "pyvenv.cfg")

    venv_accessible = False
    try:
        if os.path.exists(venv_python) and os.access(venv_python, os.X_OK) and os.path.exists(cfg_file):
            with open(cfg_file, "r") as f:
                f.read(1)
            venv_accessible = True
    except Exception:
        pass
        
    if not venv_accessible:
        local_venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python")
        try:
            local_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "pyvenv.cfg")
            if os.path.exists(local_venv) and os.access(local_venv, os.X_OK) and os.path.exists(local_cfg):
                with open(local_cfg, "r") as f:
                    f.read(1)
                venv_python = local_venv
            else:
                venv_python = sys.executable
        except Exception:
            venv_python = sys.executable
            
    agent_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape_agent.py")
    
    # Copy env and clean virtual env parameters if falling back to avoid EPERM on outer venv files
    sub_env = os.environ.copy()
    if venv_python != local_venv_python or not venv_accessible:
        sub_env.pop("VIRTUAL_ENV", None)
        sub_env.pop("__PYVENV_LAUNCHER__", None)
        if "PATH" in sub_env:
            parts = sub_env["PATH"].split(os.pathsep)
            exclude_dirs = set()
            active_venv = os.environ.get("VIRTUAL_ENV")
            if active_venv:
                exclude_dirs.add(os.path.normpath(os.path.join(active_venv, "bin")).lower())
            cleaned_parts = [p for p in parts if os.path.normpath(p).lower() not in exclude_dirs]
            sub_env["PATH"] = os.pathsep.join(cleaned_parts)
            
    try:
        # Run agent script as a subprocess and wait for completion
        result = subprocess.run([venv_python, agent_script, "--non-interactive"], env=sub_env, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{datetime.now().isoformat()}] Research agent completed successfully.")
            return True, result.stdout
        else:
            print(f"[{datetime.now().isoformat()}] Research agent failed with exit code {result.returncode}.")
            print("Errors:", result.stderr)
            return False, result.stderr
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Error executing research agent: {e}")
        return False, str(e)

def update_status(last_run_success, last_run_time, next_run_time):
    """Updates the local runner status file."""
    status = {
        "last_run_success": last_run_success,
        "last_run_time": last_run_time.isoformat(),
        "next_run_time": next_run_time.isoformat(),
        "pid": os.getpid()
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def start_scheduler(interval_hours):
    """Runs a persistent scheduling loop in the background."""
    print(f"Starting background research scheduler. Run interval: every {interval_hours} hours.")
    print("To stop this scheduler, kill this process or delete runner_status.json.")
    
    import json # Import here to ensure availability
    
    while True:
        last_run_time = datetime.now()
        success, output = run_agent()
        
        next_run_time = last_run_time + timedelta(hours=interval_hours)
        update_status(success, last_run_time, next_run_time)
        
        sleep_seconds = interval_hours * 3600
        print(f"Sleeping for {interval_hours} hours. Next run scheduled at {next_run_time.isoformat()}.")
        time.sleep(sleep_seconds)

def generate_launchd_plist():
    """Generates a macOS launchd PLIST file content for the user."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    runner_script = os.path.join(script_dir, "periodic_runner.py")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.music.synclicensing.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>{runner_script}</string>
        <string>--run-now</string>
    </array>
    <key>StartInterval</key>
    <integer>86400</integer> <!-- Runs every day (86400 seconds) -->
    <key>WorkingDirectory</key>
    <string>{script_dir}</string>
    <key>StandardOutPath</key>
    <string>{script_dir}/runner_output.log</string>
    <key>StandardErrorPath</key>
    <string>{script_dir}/runner_error.log</string>
</dict>
</plist>
"""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.music.synclicensing.agent.plist")
    print("\n=== NATIVE MACOS BACKGROUND EXECUTION ===")
    print("You can set up this research agent to run automatically every day in the background on your Mac.")
    print("To do so, save the following content into:")
    print(f"  {plist_path}")
    print("\n----------------- PLIST FILE CONTENT -----------------")
    print(plist_content)
    print("------------------------------------------------------")
    print("\nThen load it with:")
    print("  launchctl load ~/Library/LaunchAgents/com.music.synclicensing.agent.plist")
    print("-----------------------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Periodic background runner for Sync Licensing Deep Research Agent.")
    parser.add_argument("--run-now", action="store_true", help="Execute the research agent once immediately and exit.")
    parser.add_argument("--daemon", type=float, help="Start scheduler running every N hours in background.")
    parser.add_argument("--setup-launchd", action="store_true", help="Generate macOS launchd config and instructions.")
    
    args = parser.parse_args()
    
    if args.run_now:
        run_agent()
    elif args.daemon:
        start_scheduler(args.daemon)
    elif args.setup_launchd:
        generate_launchd_plist()
    else:
        parser.print_help()
