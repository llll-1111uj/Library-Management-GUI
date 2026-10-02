import os
import sys

_CODE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CODE_DIR)
for _p in (_ROOT_DIR, _CODE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
