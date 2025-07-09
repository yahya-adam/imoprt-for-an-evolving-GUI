import os
import sys
import platform
import ctypes


# Add the parent directory of src to sys.path
src_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(src_dir)
sys.path.insert(0, parent_dir)

from src.gui.main_window import main

if __name__ == "__main__":
    main()