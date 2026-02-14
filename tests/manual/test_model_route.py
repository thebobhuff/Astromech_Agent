import requests
import time

print("Attempting to connect to backend...")
for i in range(5):
    try:
        resp = requests.get("http://localhost:8000/api/v1/models/")
        print(f"Status: {resp.status_code}")
        print(f"Content: {resp.text[:200]}")
        break
    except Exception as e:
        print(f"Attempt {i+1} failed: {e}")
        time.sleep(2)
