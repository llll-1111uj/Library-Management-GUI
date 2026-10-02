import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(ROOT, "Code")

os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, CODE)

from GUIManager import main

if __name__ == "__main__":
    main()
