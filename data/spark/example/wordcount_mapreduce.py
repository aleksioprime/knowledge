"""MapReduce на чистом Python: подсчёт слов в комментариях к задачам.

python wordcount_mapreduce.py
"""

from collections import defaultdict
from itertools import chain

# Каждый «узел» хранит свой кусок данных (в Hadoop — блок файла в HDFS)
splits = [
    ['Починить кран на кухне', 'Купить хлеб и молоко'],
    ['Починить велосипед', 'Сдать отчёт до пятницы'],
    ['Купить подарок', 'Починить кран в ванной'],
]


def map_phase(lines: list[str]) -> list[tuple[str, int]]:
    """map: каждый узел независимо превращает строки в пары (слово, 1)."""
    return [(word.lower(), 1) for line in lines for word in line.split()]


def shuffle_phase(mapped: list[list[tuple[str, int]]], reducers: int) -> list[dict[str, list[int]]]:
    """shuffle: пары с одинаковым ключом собираются на одном reducer — данные едут по сети."""
    buckets: list[dict[str, list[int]]] = [defaultdict(list) for _ in range(reducers)]
    for word, count in chain.from_iterable(mapped):
        buckets[hash(word) % reducers][word].append(count)
    return buckets


def reduce_phase(bucket: dict[str, list[int]]) -> dict[str, int]:
    """reduce: каждый reducer сворачивает список значений своего ключа."""
    return {word: sum(counts) for word, counts in bucket.items()}


mapped = [map_phase(split) for split in splits]          # параллельно на 3 узлах
buckets = shuffle_phase(mapped, reducers=2)              # обмен по сети
result = {}
for bucket in buckets:                                   # параллельно на 2 узлах
    result.update(reduce_phase(bucket))

print(sorted(result.items(), key=lambda item: (-item[1], item[0]))[:4])
# [('починить', 3), ('кран', 2), ('купить', 2), ('в', 1)]
