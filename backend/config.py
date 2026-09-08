"""
TradeFusion AI - Config loader
Automatically loads .env file if present.
"""

import os
from pathlib import Path

def load_env():
    """Load variables from .env into environment."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[Config] Loaded .env from {env_path}")
        else:
            # Also try current working directory
            load_dotenv()
    except ImportError:
        print("[Config] python-dotenv not installed. Run: pip install python-dotenv")

# Load immediately on import
load_env()
