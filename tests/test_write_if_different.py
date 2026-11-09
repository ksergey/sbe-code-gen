import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPOT_SCHEMA = REPO_ROOT / 'resources' / 'spot_3_1.xml'

# Files are generated entirely deterministically (no date stamps), so a
# second run over an unmodified output must be byte-identical everywhere. To
# observe mtime.touch even when the filesystem resolves timestamps finer
# than the test can act, push every file's mtime far into the past before
# regenerating: a rewritten file then evidently differs from one skipped by
# the write-if-different check.
PAST_TIME_NS = int((time.time() - 10000) * 1e9)


def _generate(destination: Path) -> None:
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(SPOT_SCHEMA),
         '--destination', str(destination),
         '--generator', 'cpp-split'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)


def _touch_all_back_in_time(destination: Path) -> None:
    for path in destination.rglob('*'):
        if path.is_file():
            os.utime(path, ns=(PAST_TIME_NS, PAST_TIME_NS))


def test_regeneration_preserves_mtime_and_content_of_unchanged_files(tmp_path):
    destination = tmp_path / 'codec'
    _generate(destination)
    before = {p: p.read_bytes() for p in destination.rglob('*') if p.is_file()}
    _touch_all_back_in_time(destination)

    _generate(destination)

    for path in destination.rglob('*'):
        if path.is_file():
            assert path.stat().st_mtime_ns == PAST_TIME_NS, f'rewritten: {path}'
            assert path.read_bytes() == before[path], f'content changed: {path}'


def test_regeneration_rewrites_only_the_changed_file(tmp_path):
    destination = tmp_path / 'codec'
    _generate(destination)
    _touch_all_back_in_time(destination)
    victim = destination / 'schema.h'
    victim.write_bytes(b'hand-corrupted, not what the generator would emit')

    _generate(destination)

    assert victim.stat().st_mtime_ns > PAST_TIME_NS, 'corrupted file was not rewritten'
    assert victim.read_bytes() != b'hand-corrupted, not what the generator would emit'
    for path in destination.rglob('*'):
        if path.is_file() and path != victim:
            assert path.stat().st_mtime_ns == PAST_TIME_NS, f'rewritten: {path}'
