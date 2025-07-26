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
    """Loads Edge profiles from a JSON file."""
    logger.log(f"Loading profiles from {file_path}.", "INFO")
    profiles = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for full_name, details in data.items():
            email = extract_email_from_name(full_name)
            name_part_match = re.search(r'\((.*?)\)', full_name)
            name = name_part_match.group(1) if name_part_match else "Profile"
            
            # Updated to load the status, defaulting to 'active' if not present
            status = details.get("status", "active")
            
            profiles.append(EdgeProfile(
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
    
    # Set the appearance mode
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    # Load profiles and initialize services
    profiles = load_profiles(config.PROFILES_JSON_PATH)
    automation_service = AutomationService()
    
    # Create and run the application
    app = BingAutomatorApp(profiles, automation_service)
    app.run()
    logger.log("Application has been closed.", "INFO")

if __name__ == "__main__":
    main()
