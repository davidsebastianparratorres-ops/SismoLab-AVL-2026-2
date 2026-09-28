import os
import sys

# Project root (parent of tests/) must be importable so `src.` imports work.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
