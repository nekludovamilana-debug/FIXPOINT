"""Simple response-time sampler for the public pages of a running project.
Usage: python scripts_benchmark.py http://127.0.0.1:8000/ 20
"""
import statistics
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000/').rstrip('/')
count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
paths = ['/', '/accounts/login/']
for path in paths:
    samples = []
    failures = 0
    for _ in range(max(1, count)):
        started = time.perf_counter()
        try:
            request = Request(base + path, headers={'User-Agent': 'RepairWorkshop-Benchmark/1.0'})
            with urlopen(request, timeout=10) as response:
                response.read(1024)
        except (URLError, TimeoutError):
            failures += 1
        else:
            samples.append(time.perf_counter() - started)
    if samples:
        ordered = sorted(samples)
        p95 = ordered[min(len(ordered) - 1, int(len(ordered) * .95))]
        print(f'{path}: среднее={statistics.mean(samples):.3f} c, p95={p95:.3f} c, запросов={len(samples)}, ошибок={failures}')
    else:
        print(f'{path}: нет успешных ответов, ошибок={failures}')
