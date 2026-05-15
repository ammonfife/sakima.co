#!/usr/bin/env python3
"""Root-level shim — delegates to scripts/playwright_test.py"""
import subprocess, sys, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
sys.exit(subprocess.run([sys.executable, 'playwright_test.py'] + sys.argv[1:]).returncode)
