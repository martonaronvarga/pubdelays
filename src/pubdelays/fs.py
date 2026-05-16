"""Filesystem utilities for process-safe pipeline stages."""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path


@contextlib.contextmanager
def atomic_output_path(path: Path, *, mode: int = 0o644) -> Iterator[Path]:
    """Yield a temporary path and atomically replace ``path`` on success.

    The temporary file is created in the destination directory, so ``replace`` is
    atomic on POSIX filesystems when source and destination are on the same
    mount. The caller writes to the yielded path. On exception, the temporary
    file is removed and the old output remains untouched.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        yield tmp_path
        os.chmod(tmp_path, mode)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def complete_file(path: Path) -> bool:
    """Return true when ``path`` exists and is non-empty."""

    path = Path(path)
    return path.exists() and path.is_file() and path.stat().st_size > 0
