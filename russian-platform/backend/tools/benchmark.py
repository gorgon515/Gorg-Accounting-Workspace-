"""Performance benchmark: measures every major endpoint against the
Phase 3/4 latency budgets and prints a markdown table.

Usage (server must be running with a seeded DB):
    python -m tools.benchmark [base_url]
"""
import statistics
import sys
import time

import httpx

BUDGETS_MS = {
    "/api/v1/vocabulary?q=dom": 30,       # dictionary search budget
    "/api/v1/reviews/queue": 50,          # review answer budget proxy
    "/api/v1/lessons/courses": 150,
    "/api/v1/grammar/topics": 150,
    "/api/v1/library/texts": 150,
    "/api/v1/exams/level/A1": 150,
    "/api/v1/analytics/dashboard": 150,
    "/api/v1/analytics/trends": 150,
    "/api/v1/account/search?q=погода": 150,
    "/api/v1/gamification/quests": 150,
}
RUNS = 5


def main(argv: list[str]) -> int:
    base = argv[0] if argv else "http://localhost:8000"
    client = httpx.Client(base_url=base, timeout=30)

    register = client.post("/api/v1/auth/register", json={
        "email": f"bench{int(time.time())}@example.com",
        "password": "benchmark123", "display_name": "Bench",
    })
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rows = []
    all_ok = True
    for path, budget in BUDGETS_MS.items():
        client.get(path, headers=headers)  # warm-up (connection, caches)
        samples = []
        for _ in range(RUNS):
            start = time.perf_counter()
            response = client.get(path, headers=headers)
            samples.append((time.perf_counter() - start) * 1000)
            assert response.status_code == 200, f"{path}: {response.status_code}"
        median = statistics.median(samples)
        ok = median <= budget
        all_ok &= ok
        rows.append((path, median, budget, ok))

    print("| Endpoint | median ms | budget ms | status |")
    print("|---|---|---|---|")
    for path, median, budget, ok in rows:
        print(f"| {path} | {median:.1f} | {budget} | {'✅' if ok else '❌ OVER'} |")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
