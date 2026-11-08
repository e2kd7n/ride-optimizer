"""Run the Explore page's JavaScript unit tests (tests/js/*.test.js) under
pytest, so CI (which only runs pytest) covers them too. Skipped when node
isn't installed."""

import shutil
import subprocess
from pathlib import Path

import pytest

JS_TEST_DIR = Path(__file__).parent / "js"


@pytest.mark.unit
def test_explore_js_unit_tests():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    files = sorted(str(p) for p in JS_TEST_DIR.glob("*.test.js"))
    assert files, "no JS test files found"
    proc = subprocess.run(
        [node, "--test", *files],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, f"node --test failed:\n{proc.stdout}\n{proc.stderr}"
