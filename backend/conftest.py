"""
Root conftest.py to ensure proper Python path setup for tests.
"""
import sys
import os

# Add the backend directory to Python path so 'app' module can be imported
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
