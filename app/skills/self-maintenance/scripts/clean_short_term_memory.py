#!/usr/bin/env python
"""
Scheduled Task: CleanShortTermMemory
Description: Clean up short-term memory older than 2 hours.
"""
import sys
import asyncio
from datetime import timedelta

# Ensure app modules are discoverable
sys.path.insert(0, r"F:\Projects\Astromech")

from app.memory.short_term import ShortTermMemoryManager

def main():
    """Clean up short-term memories older than 2 hours."""
    manager = ShortTermMemoryManager()
    
    # Clean memories older than 2 hours
    cutoff = timedelta(hours=2)
    manager.cleanup_expired(older_than_timedelta=cutoff)
    
    print("✅ Short-term memory cleanup completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
