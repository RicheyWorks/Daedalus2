#!/usr/bin/env python3
"""
Daedalus Generator Benchmark Tool
Runs all registered generators and reports timing + stats.
"""

import requests
import time
import json
from typing import List, Dict

API_BASE = "http://localhost:8080/api"

def benchmark_generator(generator_id: str, sizes: List[int] = [25, 50, 100]) -> Dict:
    results = []
    for size in sizes:
        start = time.time()
        try:
            resp = requests.post(f"{API_BASE}/maze/generate", json={
                "generatorId": generator_id,
                "rows": size,
                "cols": size
            }, timeout=30)
            elapsed = (time.time() - start) * 1000
            if resp.ok:
                data = resp.json()
                results.append({
                    "size": size,
                    "time_ms": round(elapsed, 1),
                    "id": data.get("id")
                })
            else:
                results.append({"size": size, "error": resp.text})
        except Exception as e:
            results.append({"size": size, "error": str(e)})
    return {"generator": generator_id, "results": results}

def main():
    print("Daedalus Generator Benchmark\n")
    
    # Get list of generators
    try:
        algos = requests.get(f"{API_BASE}/algorithms").json()
        generators = [g["id"] for g in algos.get("generators", [])]
    except:
        generators = ["recursive-backtracker", "prims", "kruskals", "lightning", "hilbert-curve"]
    
    print(f"Testing {len(generators)} generators...\n")
    
    for gen_id in generators[:8]:  # Limit for speed
        result = benchmark_generator(gen_id)
        print(f"{gen_id}:")
        for r in result["results"]:
            if "error" in r:
                print(f"  {r['size']}x{r['size']}: ERROR - {r['error']}")
            else:
                print(f"  {r['size']}x{r['size']}: {r['time_ms']}ms")
        print()

if __name__ == "__main__":
    main()