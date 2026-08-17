"""conftest.py — pytest configuration for vadachain backend tests."""
import sys
import os

# Add the vadachain root to sys.path so `backend.*` imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
