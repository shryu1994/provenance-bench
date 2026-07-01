"""Make both the repo root (for `provbench`) and the promptfoo bridge importable."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))   # promptfoo/tests
_PF = os.path.dirname(_HERE)                          # promptfoo
_ROOT = os.path.dirname(_PF)                          # repo root

for _p in (_PF, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
