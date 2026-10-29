"""Сжатие колонок журнала событий задач: delta, double-delta, RLE, словарь + LZ4/ZSTD.

uv run --with zstandard==0.25.0 --with lz4==4.4.5 python column_compression.py
"""

import random
import time
from array import array
from collections.abc import Iterable

import lz4.frame
import zstandard

ROWS = 1_000_000
STATUSES = ['new', 'in_progress', 'review', 'done', 'cancelled']


def delta_encode(values: list[int]) -> list[int]:
    return [values[0]] + [cur - prev for prev, cur in zip(values, values[1:])]


def delta_decode(deltas: list[int]) -> list[int]:
    values, total = [], 0
    for d in deltas:
        total += d
        values.append(total)
    return values


def rle_encode(values: Iterable[str]) -> list[tuple[str, int]]:
    runs: list[tuple[str, int]] = []
    for value in values:
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))
    return runs


def rle_decode(runs: list[tuple[str, int]]) -> list[str]:
    return [value for value, count in runs for _ in range(count)]


def int64(values: list[int]) -> bytes:
    return array('q', values).tobytes()


def zstd(data: bytes, level: int = 3) -> bytes:
    return zstandard.ZstdCompressor(level=level).compress(data)


def lz4f(data: bytes) -> bytes:
    return lz4.frame.compress(data)


def report(title: str, raw: int, variants: dict[str, bytes]) -> None:
    print(f'\n{title}: сырые данные {raw / 1024:,.0f} КБ')
    for name, packed in variants.items():
        size = f'{len(packed) / 1024:,.0f} КБ' if len(packed) >= 1024 else f'{len(packed)} байт'
        print(f'  {name:<24} {size:>12}   x{raw / len(packed):,.1f}')


random.seed(42)

# Время событий в миллисекундах: поток идёт по порядку, между событиями 0–200 мс
start_ms = 1_793_000_000_000
created = [start_ms]
for _ in range(ROWS - 1):
    created.append(created[-1] + random.randint(0, 200))

assert delta_decode(delta_encode(created)) == created
raw_ts = int64(created)
deltas = delta_encode(created)
double = delta_encode(deltas)
report('Время события (int64, мс)', len(raw_ts), {
    'lz4': lz4f(raw_ts),
    'zstd': zstd(raw_ts),
    'delta + lz4': lz4f(int64(deltas)),
    'delta + zstd': zstd(int64(deltas)),
    'double-delta + zstd': zstd(int64(double)),
})

# Метрика с почти ровным шагом: снимок раз в секунду с дрожанием ±2 мс
ticks = [start_ms + i * 1000 + random.randint(-2, 2) for i in range(ROWS)]
raw_ticks = int64(ticks)
report('Время снимка метрики (шаг 1 с)', len(raw_ticks), {
    'zstd': zstd(raw_ticks),
    'delta + zstd': zstd(int64(delta_encode(ticks))),
    'double-delta + zstd': zstd(int64(delta_encode(delta_encode(ticks)))),
})

# Статус задачи: строки с малым числом различных значений
status_by_time = random.choices(STATUSES, weights=[30, 25, 10, 30, 5], k=ROWS)
status_sorted = sorted(status_by_time)
raw_status = '\n'.join(status_by_time).encode()

codes = {s: i for i, s in enumerate(STATUSES)}
dict_codes = bytes(codes[s] for s in status_by_time)  # 1 байт на строку вместо ~6

runs_sorted = rle_encode(status_sorted)
assert rle_decode(runs_sorted) == status_sorted
runs_random = rle_encode(status_by_time)
rle_bytes = b''.join(bytes([codes[s]]) + n.to_bytes(4, 'little') for s, n in runs_random)
rle_sorted_bytes = b''.join(bytes([codes[s]]) + n.to_bytes(4, 'little') for s, n in runs_sorted)

report('Статус задачи (строки)', len(raw_status), {
    'lz4': lz4f(raw_status),
    'zstd': zstd(raw_status),
    'словарь (1 байт)': dict_codes,
    'словарь + zstd': zstd(dict_codes),
    'RLE (по времени)': rle_bytes,
    'RLE (отсортировано)': rle_sorted_bytes,
})
print(f'  серий RLE: по времени {len(runs_random):,}, после сортировки {len(runs_sorted)}')

# Скорость: сжатие и распаковка 8 МБ колонки времени
for name, pack, unpack in [
    ('lz4', lz4f, lz4.frame.decompress),
    ('zstd -3', zstd, zstandard.ZstdDecompressor().decompress),
    ('zstd -19', lambda d: zstd(d, 19), zstandard.ZstdDecompressor().decompress),
]:
    t0 = time.perf_counter()
    packed = pack(raw_ts)
    t1 = time.perf_counter()
    unpack(packed)
    t2 = time.perf_counter()
    print(f'{name:<9} сжатие {(t1 - t0) * 1000:7.1f} мс, распаковка {(t2 - t1) * 1000:5.1f} мс, '
          f'размер {len(packed) / 1024:,.0f} КБ')
