from time import perf_counter
from cracker_core import md5_of, crack_range

target = md5_of("0500000000")
t0 = perf_counter()
number = crack_range(target, 0, 50_000)   # 50 001 candidates
print(f"{number=}")
print(perf_counter() - t0, "seconds")
