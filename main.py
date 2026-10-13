import os
import sys

if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(ROOT, "Code")
if getattr(sys, "frozen", False):
    CODE = getattr(sys, "_MEIPASS", ROOT)

os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, CODE)

from repository.connection import init_database
init_database()

from GUIManager import main

if __name__ == "__main__":
    main()
