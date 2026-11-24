import os
import sys

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)
