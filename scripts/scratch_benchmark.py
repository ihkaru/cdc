import requests
import time

url = "http://127.0.0.1:8000/lookup/metadata"
payload = {"sso_username": "ihzakarunia@bps.go.id", "sso_password": "Fikrizaki2!"}

print("--- STARTING BENCHMARK ---")

# Run 1: Cold Start
print("\n[Run 1] Cold Start (Might trigger browser if cache empty)...")
start = time.perf_counter()
resp = requests.post(url, json=payload)
end = time.perf_counter()
print(f"Status: {resp.status_code}")
print(f"Time: {end - start:.4f}s")
if resp.status_code == 200:
    print(f"Metadata received: {str(resp.json())[:100]}...")

# Run 2: Warm Start
print("\n[Run 2] Warm Start (Should be FAST - HTTP only)...")
start = time.perf_counter()
resp = requests.post(url, json=payload)
end = time.perf_counter()
print(f"Status: {resp.status_code}")
print(f"Time: {end - start:.4f}s")
if resp.status_code == 200:
    print(f"Metadata received: {str(resp.json())[:100]}...")

print("\n--- BENCHMARK FINISHED ---")
