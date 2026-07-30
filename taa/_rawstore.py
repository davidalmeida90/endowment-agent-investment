"""
PRIVATE. Raw data store for the Ashcroft study.

Nothing in this package may import this module except taa.pitdata (for reads)
and taa.datapull (for writes and network fetches). That restriction is enforced
at runtime by inspecting the calling module, and again statically by
tests/test_lookahead.py, which walks the import graph of the whole package.

The point of the split is that a raw series carries no as-of date. Anything
that can read one can read the future. So exactly one module is allowed to,
and that module (taa.pitdata) applies the as-of gate to every value it hands
back. Analysis code has no route to this file.
"""

from __future__ import annotations

import inspect
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config

# Flipping this to False removes the wall. tests/mutation_test.py does exactly
# that in a sandbox copy and asserts the test suite goes red. If the suite
# stays green with this False, the tests were never testing anything.
_GUARD_ENABLED = True

_READERS = ("taa.pitdata",)
_WRITERS = ("taa.datapull",)

USER_AGENT = "Ashcroft-Endowment-TAA-Study/1.0 (public data only)"


class RawAccessViolation(RuntimeError):
    """Raised when a module that is not taa.pitdata tries to read raw data."""


def _module_file(dotted: str) -> str:
    """
    Resolve an allowed module to the file it lives in, alongside this one.

    The caller is identified by file rather than by __name__ because __name__
    is "__main__" whenever a module is run with  python -m , and a guard that
    keys on __name__ therefore blocks the study's own ingestion layer while
    letting a module imported under an alias through. Identifying by file is
    both stricter and correct under -m. It also survives being copied into a
    sandbox, which is how tests/mutation_test.py exercises this guard.
    """
    return str((Path(__file__).resolve().parent / f"{dotted.split('.')[-1]}.py"))


def _calling_frame() -> tuple[str, str]:
    """Return (module name, absolute file) of the first frame outside this module."""
    here = str(Path(__file__).resolve())
    for frame in inspect.stack()[2:]:
        f = frame.frame.f_globals.get("__file__", "")
        try:
            f = str(Path(f).resolve()) if f else ""
        except OSError:
            f = ""
        if f != here:
            return frame.frame.f_globals.get("__name__", "<unknown>"), f
    return "<unknown>", ""


def _guard(allowed: tuple[str, ...], verb: str) -> None:
    if not _GUARD_ENABLED:
        return
    name, path = _calling_frame()
    permitted = {_module_file(a) for a in allowed}
    if path not in permitted:
        raise RawAccessViolation(
            f"module {name!r} ({path or 'no file'}) attempted to {verb} raw data "
            f"directly. Only {allowed} may do so. Historical data is read through "
            f"taa.pitdata.as_of(<date>), which applies the point-in-time gate."
        )


# --------------------------------------------------------------------------
# Cache layout
# --------------------------------------------------------------------------
def _path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_")
    return config.RAW / f"{safe}.csv"


def _meta_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_")
    return config.RAW / f"{safe}.meta.json"


def exists(key: str) -> bool:
    return _path(key).exists()


# --------------------------------------------------------------------------
# Reads — taa.pitdata only
# --------------------------------------------------------------------------
def read(key: str) -> str:
    _guard(_READERS, "read")
    p = _path(key)
    if not p.exists():
        raise FileNotFoundError(
            f"raw series {key!r} is not in the cache. Run  py -3 -m taa.datapull  first."
        )
    return p.read_text(encoding="utf-8")


def read_meta(key: str) -> dict:
    _guard(_READERS, "read")
    p = _meta_path(key)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def catalogue() -> list[str]:
    _guard(_READERS, "read")
    return sorted(p.stem for p in config.RAW.glob("*.csv"))


# --------------------------------------------------------------------------
# Writes and network — taa.datapull only
# --------------------------------------------------------------------------
def write(key: str, text: str, meta: dict | None = None) -> None:
    _guard(_WRITERS, "write")
    _path(key).write_text(text, encoding="utf-8")
    if meta is not None:
        meta = dict(meta)
        meta["pulled_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _meta_path(key).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def http_get(url: str, retries: int = 3, timeout: int = 45) -> str:
    _guard(_WRITERS, "fetch")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} attempts: {url}: {last}")
