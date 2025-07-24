# BingRewardSearch/main.py

import json
import os
import re
from typing import List, Dict

from app import BingAutomatorApp
from automation_service import AutomationService
from edge_profile import EdgeProfile
from logger import logger # Import the logger instance
import config

def load_profiles_from_json(filepath: str) -> List[EdgeProfile]:
    """
    Loads profile data from a JSON file and returns a list of EdgeProfile objects.
    """
    if not os.path.exists(filepath):
        logger.log(f"The file '{filepath}' was not found.", level="ERROR")
        return []

    profiles_list = []
    profile_pattern = re.compile(r"^(.*) \((.*)\)$")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data: Dict[str, Dict[str, str]] = json.load(f)

        logger.log(f"Loading {len(data)} profiles from {filepath}.")
        for key, details in data.items():
            cmd_arg = details.get("cmd")
            if not cmd_arg:
                logger.log(f"Profile with key '{key}' is missing 'cmd' argument.", level="WARN")
                continue

            match = profile_pattern.match(key)
            if match:
                email, name = match.groups()
                profiles_list.append(EdgeProfile(name=name.strip(), email=email.strip(), cmd_arg=cmd_arg))
            else:
                logger.log(f"Could not parse profile key '{key}'. Using full key as email.", level="WARN")
                profiles_list.append(EdgeProfile(name="N/A", email=key, cmd_arg=cmd_arg))

    except json.JSONDecodeError as e:
        logger.log(f"Could not decode JSON from '{filepath}'. Error: {e}", level="ERROR")
    except Exception as e:
        logger.log(f"An unexpected error occurred while loading profiles: {e}", level="ERROR")

    return profiles_list

def main():
    """
    The main entry point of the application.
    """
    logger.log("Application starting up.")
    
    automation_service = AutomationService()
    profiles = load_profiles_from_json(config.PROFILES_JSON_PATH)

    if not profiles:
        logger.log("No profiles loaded. Exiting application.", level="ERROR")
        return

    logger.log(f"Successfully loaded {len(profiles)} profiles.")
    app = BingAutomatorApp(profiles=profiles, automation_service=automation_service)
    app.run()
    
    logger.log("Application has been closed.")

if __name__ == "__main__":
    main()
