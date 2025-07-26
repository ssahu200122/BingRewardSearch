# BingRewardSearch/config.py
import customtkinter
import os

# --- File Paths ---
PROFILES_JSON_PATH = "data.json"
LOG_FILE_PATH = "log.txt"
SETTINGS_JSON_PATH = "settings.json"
HISTORY_CSV_PATH = "progress_history.csv" # Path for the new history file

# The original script used a batch file for restarting. We'll define its expected path.
# It will check OneDrive desktop first, then local desktop.
HOME_DIR = os.path.expanduser('~')
RESTART_BATCH_FILE_ONEDRIVE = os.path.join(HOME_DIR, 'OneDrive', 'Desktop', 'bing.bat')
RESTART_BATCH_FILE_LOCAL = os.path.join(HOME_DIR, 'Desktop', 'bing.bat')

# app_width = 800
# app_height = 500

# screen_width = customtkinter.CTk().winfo_screenwidth()
# screen_height = customtkinter.CTk().winfo_screenheight()

#         # Position app at bottom right, accounting for taskbar (approx. 40px)
# x_coordinate = screen_width - app_width
# y_coordinate = screen_height - app_height - 40 
# --- Application Settings ---
APP_TITLE = "Bing Auto Search"
APP_GEOMETRY = "800x500"

# --- Automation Settings ---
# Delays are now ranges (min_seconds, max_seconds) for more human-like behavior.
WAIT_FOR_EDGE_LAUNCH = (3.5, 5.0)
ACTION_DELAY = (0.8, 1.5)
# **NEW**: A longer delay for small, targeted retry searches to ensure they register.
RETRY_ACTION_DELAY = (2.0, 3.0) 
BATCH_DELAY = (1.5, 2.5)
# Add a delay between individual key presses to simulate typing
KEY_PRESS_DELAY = (0.05, 0.15)
