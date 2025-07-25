# BingRewardSearch/config.py

import os

# --- File Paths ---
PROFILES_JSON_PATH = "data.json"
LOG_FILE_PATH = "log.txt"
SETTINGS_JSON_PATH = "settings.json" # Path for schedule settings

# The original script used a batch file for restarting. We'll define its expected path.
# It will check OneDrive desktop first, then local desktop.
HOME_DIR = os.path.expanduser('~')
RESTART_BATCH_FILE_ONEDRIVE = os.path.join(HOME_DIR, 'OneDrive', 'Desktop', 'bing.bat')
RESTART_BATCH_FILE_LOCAL = os.path.join(HOME_DIR, 'Desktop', 'bing.bat')


# --- Application Settings ---
APP_TITLE = "Bing Auto Search"
APP_GEOMETRY = "800x500" # Increased height for scheduler

# --- Automation Settings ---
# Delays are now ranges (min_seconds, max_seconds) for more human-like behavior.
WAIT_FOR_EDGE_LAUNCH = (3.5, 5.0)
ACTION_DELAY = (0.8, 1.5)
BATCH_DELAY = (1.5, 2.5)
# Add a delay between individual key presses to simulate typing
KEY_PRESS_DELAY = (0.05, 0.15)
