"""Игрушечное LSM-дерево: memtable, WAL, SSTable, bloom-фильтр и компакция.

python tiny_lsm.py
"""

import hashlib
import json
import tempfile
from pathlib import Path

TOMBSTONE = None  # удалённый ключ: значение-«надгробие», а не стирание на месте


class Bloom:
    """Битовая маска: «точно нет» или «возможно есть»."""

    def __init__(self, size: int = 1024, hashes: int = 3):
        self.size, self.hashes, self.bits = size, hashes, 0

    def _positions(self, key: str):
        for i in range(self.hashes):
            yield int(hashlib.md5(f'{i}:{key}'.encode()).hexdigest(), 16) % self.size

    def add(self, key: str) -> None:
        for pos in self._positions(key):
            self.bits |= 1 << pos

    def might_contain(self, key: str) -> bool:
        return all(self.bits >> pos & 1 for pos in self._positions(key))


class LSM:
    def __init__(self, folder: Path, memtable_limit: int = 3):
        self.folder, self.limit = folder, memtable_limit
        self.wal = (folder / 'wal.log').open('a')
        self.memtable: dict[str, str | None] = {}
        self.sstables: list[tuple[Path, Bloom]] = []  # от старых к новым
        self.files_read = 0

    def put(self, key: str, value: str | None) -> None:
        self.wal.write(json.dumps([key, value]) + '\n')  # сначала журнал — переживём падение
        self.wal.flush()
        self.memtable[key] = value
        if len(self.memtable) >= self.limit:
            self.flush()

    def delete(self, key: str) -> None:
        self.put(key, TOMBSTONE)

    def flush(self) -> None:
        """Memtable → новый отсортированный неизменяемый файл (SSTable)."""
        path = self.folder / f'sst_{len(self.sstables):03}.json'
        self._write_sstable(path, dict(sorted(self.memtable.items())))
        self.memtable.clear()
        self.wal.truncate(0)

    def _write_sstable(self, path: Path, rows: dict) -> None:
        path.write_text(json.dumps(rows, ensure_ascii=False))
        bloom = Bloom()
        for key in rows:
            bloom.add(key)
        self.sstables.append((path, bloom))

    def get(self, key: str) -> str | None:
        if key in self.memtable:
            return self.memtable[key]
        for path, bloom in reversed(self.sstables):  # новые файлы важнее старых
            if not bloom.might_contain(key):
                continue
            self.files_read += 1
            rows = json.loads(path.read_text())
            if key in rows:
                return rows[key]
        return None

    def compact(self) -> None:
        """Сливает все SSTable в одну: остаётся последняя версия, надгробия выбрасываются."""
        merged: dict = {}
        for path, _ in self.sstables:
            merged.update(json.loads(path.read_text()))
            path.unlink()
        self.sstables = []
        self._write_sstable(self.folder / 'sst_compacted.json',
                            {k: v for k, v in sorted(merged.items()) if v is not TOMBSTONE})


with tempfile.TemporaryDirectory() as tmp:
    db = LSM(Path(tmp))
    for i in range(1, 10):
        db.put(f'task:{i}', 'new')
    db.put('task:1', 'done')
    db.delete('task:2')
    db.put('task:3', 'review')

    print('файлы:', sorted(p.name for p in Path(tmp).glob('sst_*')))
    print('task:1 =', db.get('task:1'), '| task:2 =', db.get('task:2'), '| task:3 =', db.get('task:3'))

    db.files_read = 0
    for i in range(100, 200):
        db.get(f'task:{i}')  # ключей нет нигде
    print('поиск 100 отсутствующих ключей прочитал файлов:', db.files_read, 'из', 100 * len(db.sstables))

    db.compact()
    print('после компакции:', sorted(p.name for p in Path(tmp).glob('sst_*')),
          json.loads(next(Path(tmp).glob('sst_*')).read_text()))
