#!/usr/bin/env python
"""Run project optimization scripts for AI assistant and translation."""
import subprocess
import sys

scripts = ["fix_ai_assistant.py", "optimize_ai_translation.py"]

for script in scripts:
    print(f"\n[+] Running {script} ...")
    try:
        result = subprocess.run([sys.executable, script], check=False)
        if result.returncode != 0:
            print(f"[-] {script} exited with code {result.returncode}")
    except FileNotFoundError:
        print(f"[-] {script} not found")

print("\nOptimization finished.")
