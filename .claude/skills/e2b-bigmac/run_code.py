#!/usr/bin/env python3
"""Root-level shim — delegates to scripts/run_code.py"""
import subprocess, sys, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
sys.exit(subprocess.run([sys.executable, 'run_code.py'] + sys.argv[1:]).returncode)
