#!/usr/bin/env python3
"""
Claude Code hook — macOS sound alert on Notification events.
Reads stdin (required by CC hooks) and plays a system sound.
"""
import os
import sys
import json

# Consume stdin (required by CC hooks)
try:
    json.load(sys.stdin)
except Exception:
    pass

os.system("afplay /System/Library/Sounds/Glass.aiff")
