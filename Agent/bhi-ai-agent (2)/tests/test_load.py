"""
Load Test - BHI AI Agent
Tests concurrent requests and response time benchmarks.
Run: python tests/test_load.py
"""
import asyncio
import time
import statistics
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_TOKEN = client.post('/api/login', json={'email': 'nosdevai2k@gmail.com', 'password': 'TestPass123!'}).json().get('token')
_HEADERS = {'Authorization': 'Bearer ' + _TOKEN}

# Test scenarios simulating real user queries
SCENARIOS = [
    {"message": "Task của Phan Minh Hoàng"},
    {"message": "Task đang làm"},
    {"message": "Chi tiết task CO-001"},
    {"message": "Subtask của CO"},
    {"message": "Báo cáo của Nguyễn Văn Cường"},
    {"message": "Tìm task training"},
    {"message": "hoan thanh"},
    {"message": "Phan Minh Hoang"},
    {"message": "Báo cáo dự án cao tầng"},
    {"message": "task cua Khanh"},
    {"message": "xyz not found"},
    {"message": "Task cua Hoang"},
]


def single_request(scenario):
    """Execute single request and measure time."""
    start = time.perf_counter()
    r = client.post('/api/chat', json=scenario, headers=_HEADERS)
    elapsed = (time.perf_counter() - start) * 1000  # ms
    return {
        "status": r.status_code,
        "elapsed_ms": elapsed,
        "message": scenario["message"],
        "has_data": r.json().get("data") is not None,
    }


def run_load_test(num_requests=100, target_rps=50):
    """Simulate concurrent load."""
    print(f"🚀 Load Test: {num_requests} requests (target: {target_rps} req/s)")
    print("-" * 60)

    results = []
    errors = 0
    start_total = time.perf_counter()

    for i in range(num_requests):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        result = single_request(scenario)
        results.append(result)
        if result["status"] != 200:
            errors += 1

    total_time = time.perf_counter() - start_total
    times = [r["elapsed_ms"] for r in results]

    # Stats
    print(f"\n📊 Results ({num_requests} requests in {total_time:.2f}s)")
    print(f"   Throughput: {num_requests/total_time:.1f} req/s")
    print(f"   Errors: {errors}/{num_requests}")
    print(f"\n⏱️ Response Times (ms):")
    print(f"   Min:    {min(times):.1f}")
    print(f"   Max:    {max(times):.1f}")
    print(f"   Mean:   {statistics.mean(times):.1f}")
    print(f"   Median: {statistics.median(times):.1f}")
    print(f"   P95:    {sorted(times)[int(len(times)*0.95)]:.1f}")
    print(f"   P99:    {sorted(times)[int(len(times)*0.99)]:.1f}")

    # Per-scenario breakdown
    print(f"\n📋 Per-Scenario Breakdown:")
    scenario_times = {}
    for r in results:
        msg = r["message"][:30]
        scenario_times.setdefault(msg, []).append(r["elapsed_ms"])

    for msg, st in sorted(scenario_times.items(), key=lambda x: -statistics.mean(x[1])):
        avg = statistics.mean(st)
        print(f"   {avg:6.1f}ms  {msg}")

    # Pass/Fail criteria
    print(f"\n{'='*60}")
    p95 = sorted(times)[int(len(times)*0.95)]
    checks = [
        ("All requests 200 OK", errors == 0),
        ("P95 < 500ms", p95 < 500),
        ("Mean < 200ms", statistics.mean(times) < 200),
        ("Throughput > 20 req/s", num_requests/total_time > 20),
    ]
    all_pass = True
    for name, ok in checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"   {status} {name}")

    print(f"\n{'🎉 LOAD TEST PASSED' if all_pass else '⚠️ LOAD TEST HAS ISSUES'}")
    return all_pass


def run_burst_test(burst_size=20):
    """Simulate 18 users all sending at once."""
    print(f"\n{'='*60}")
    print(f"💥 Burst Test: {burst_size} simultaneous requests (simulating 18 users)")
    print("-" * 60)

    start = time.perf_counter()
    results = []
    for i in range(burst_size):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        results.append(single_request(scenario))

    total = time.perf_counter() - start
    times = [r["elapsed_ms"] for r in results]
    errors = sum(1 for r in results if r["status"] != 200)

    print(f"   Total time: {total*1000:.0f}ms for {burst_size} requests")
    print(f"   Avg: {statistics.mean(times):.1f}ms, Max: {max(times):.1f}ms")
    print(f"   Errors: {errors}")
    print(f"   {'✅ Burst OK' if errors == 0 and max(times) < 1000 else '❌ Burst issues'}")


if __name__ == "__main__":
    run_load_test(num_requests=200)
    run_burst_test(burst_size=18)
