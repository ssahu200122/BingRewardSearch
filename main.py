# BingRewardSearch/main.py

import customtkinter
import json
import re
from typing import List

from edge_profile import EdgeProfile
from automation_service import AutomationService
from app import BingAutomatorApp
from logger import logger
import config

def extract_email_from_name(full_name: str) -> str:
    """Extracts the email from a string like 'email@example.com (Name)'."""
    match = re.match(r"^\S+@\S+", full_name)
    return match.group(0) if match else "unknown@example.com"

def load_profiles(file_path: str) -> List[EdgeProfile]:
    """Loads Edge profiles from a JSON file and assigns an index."""
    logger.log(f"Loading profiles from {file_path}.", "INFO")
    profiles = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for index, (full_name, details) in enumerate(data.items()):
            email = extract_email_from_name(full_name)
            name_part_match = re.search(r'\((.*?)\)', full_name)
            name = name_part_match.group(1) if name_part_match else "Profile"

            # --- MODIFIED: Load points, remove status ---
            # status = details.get("status", "active") # <-- REMOVED
            available_points = details.get("available_points", 0) # <-- ADDED (Load saved points)

            profiles.append(EdgeProfile(
                index=index + 1,
                name=name,
                email=email,
                cmd_arg=details["cmd"],
                # status=status, # <-- REMOVED
                available_points=available_points # <-- ADDED
            ))
        logger.log(f"Successfully loaded {len(profiles)} profiles.", "INFO")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.log(f"Error loading profiles: {e}", "ERROR")
        # Try to recover by returning empty list or default profiles?
        # For now, just return empty on error.
        profiles = []
    except Exception as e:
        logger.log(f"Unexpected error loading profiles: {e}", "CRITICAL")
        profiles = [] # Ensure it returns a list

    return profiles

def main():
    """The main entry point of the application."""
    logger.log("Application starting up.", "INFO")

    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    profiles = load_profiles(config.PROFILES_JSON_PATH)
    # Handle case where loading failed completely
    if not profiles:
        logger.log("No profiles loaded. Exiting.", "CRITICAL")
        # Maybe show an error message GUI? For now, just exit.
        # Simple error popup:
        root = customtkinter.CTk()
        root.withdraw() # Hide main window
        customtkinter.CTkMessagebox(title="Error", message=f"Failed to load profiles from {config.PROFILES_JSON_PATH}. Please check the file exists and is valid.", icon="cancel")
        root.destroy()
        return # Exit if no profiles


    automation_service = AutomationService()

    app = BingAutomatorApp(profiles, automation_service)
    app.run()
    logger.log("Application has been closed.", "INFO")

if __name__ == "__main__":
    main()