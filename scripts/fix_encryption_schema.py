"""
Fix encryption schema - make value column nullable
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Make value column nullable
sql = "ALTER TABLE memories ALTER COLUMN value DROP NOT NULL;"

try:
    db.execute_write(sql, ())
    print("✅ Value column is now nullable")
except Exception as e:
    print(f"Error: {e}")
