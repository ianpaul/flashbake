"""
conftest.py - pytest configuration for the Flashbake test suite.

Sets up the Python path so tests can import flashbake and test helpers
regardless of how pytest is invoked (from the project root or the test dir).
"""
import sys
from pathlib import Path

# Add the flashbake source tree to the import path
_src = Path(__file__).parent.parent / 'src'
_test = Path(__file__).parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
if str(_test) not in sys.path:
    sys.path.insert(0, str(_test))
