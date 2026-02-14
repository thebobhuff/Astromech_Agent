---
name: restart-system
description: Restarts the entire Astromech system (Backend API and Frontend). Use this when the system is unresponsive, after significant code changes, or when standard tools fail.
---

# Restart System

To restart the Astromech Backend and Frontend services, execute the following command in the **terminal**. This script will forcefully terminate existing processes on ports 13579 (API) and 24680 (Web), then launch new instances in separate console windows.

**Warning**: This will momentarily disconnect the agent.

```bash
python app/skills/self-maintenance/restart.py
```
