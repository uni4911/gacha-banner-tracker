import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
IMAGES_DIR = DATA_DIR / "images"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Scheduler configuration
FETCH_INTERVAL_HOURS: int = int(os.getenv("FETCH_INTERVAL_HOURS", "6"))
RUN_SYNC_ON_STARTUP: bool = os.getenv("RUN_SYNC_ON_STARTUP", "false").lower() in ("true", "1", "yes")
DOWNLOAD_IMAGES_LOCALLY: bool = os.getenv("DOWNLOAD_IMAGES_LOCALLY", "true").lower() in ("true", "1", "yes")
ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
