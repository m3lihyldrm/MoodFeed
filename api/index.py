import os
import sys
from pathlib import Path

# Add project root and backend directory to Python sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / 'backend'

for p in (str(ROOT_DIR), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('VERCEL', '1')

from backend.main import app

# Export ASGI application for Vercel Serverless Python runtime
handler = app
