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
        
        # Enumerate to get the index for each profile
        for index, (full_name, details) in enumerate(data.items()):
            email = extract_email_from_name(full_name)
            name_part_match = re.search(r'\((.*?)\)', full_name)
            name = name_part_match.group(1) if name_part_match else "Profile"
            
            # --- REVERTED to simple version ---
            status = details.get("status", "active")
            
            profiles.append(EdgeProfile(
                index=index + 1,  # Use a 1-based index for display
                name=name,
                email=email,
                cmd_arg=details["cmd"],
                status=status
            ))
        logger.log(f"Successfully loaded {len(profiles)} profiles.", "INFO")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.log(f"Error loading profiles: {e}", "ERROR")
    return profiles

def main():
    """The main entry point of the application."""
    logger.log("Application starting up.", "INFO")
    
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    profiles = load_profiles(config.PROFILES_JSON_PATH)
    automation_service = AutomationService()
    
    app = BingAutomatorApp(profiles, automation_service)
    app.run()
    logger.log("Application has been closed.", "INFO")

if __name__ == "__main__":
    main()