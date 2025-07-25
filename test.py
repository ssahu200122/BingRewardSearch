# test_points_fetcher.py
# A simple script to debug the Selenium point scraping feature.

import time
import os
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- IMPORTANT: EDIT THIS VALUE ---
# Find a valid profile name from your data.json file (e.g., "Default", "Profile 1")
# and put it here.
PROFILE_DIRECTORY_NAME = "Default"  # <<< EDIT THIS LINE

def fetch_points(profile_name: str):
    """Attempts to fetch points for a single, specified profile."""
    print(f"--- Starting test for profile: {profile_name} ---")
    driver = None
    try:
        # **FIX**: Force close any running Edge processes to prevent "user data directory in use" error.
        print("Attempting to close any running Microsoft Edge processes...")
        os.system("taskkill /F /IM msedge.exe > nul 2>&1")
        time.sleep(2) # Give a moment for processes to close

        # 1. Setup Selenium Driver based on the working script
        print("Setting up Edge driver from local msedgedriver.exe...")
        edge_options = EdgeOptions()
        
        # Using the exact, hardcoded paths that you confirmed are working
        user_data_dir = r"C:\Users\ssahu\AppData\Local\Microsoft\Edge\User Data"
        edge_options.add_argument(f"user-data-dir={user_data_dir}")
        edge_options.add_argument(f"profile-directory={profile_name}")
        
        # Adding the crucial options from your working script to avoid detection
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        
        # This assumes msedgedriver.exe is in the same folder as this script.
        service = EdgeService(executable_path="msedgedriver.exe")
        
        driver = webdriver.Edge(service=service, options=edge_options)
        print("Driver setup complete. Browser should open with your profile.")

        # 2. Navigate to Rewards Page
        print("Navigating to https://rewards.bing.com/ ...")
        driver.get("https://rewards.bing.com/pointsbreakdown")

        # 3. Wait for the points element to appear and be populated
        print("Waiting for points element to appear...")
        wait = WebDriverWait(driver, 20)

        # **MODIFIED SELECTOR**: Using a new, more accurate selector based on the provided HTML.
        # This looks for the <b> tag inside the span that contains the points info.
        points_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span[aria-label*='points this month'] b"))
        )
        print("Found the points container element.")

        # 4. Wait until the text inside the element contains a number.
        print("Waiting for points value to load...")
        wait.until(
            lambda d: re.search(r'\d', points_element.text)
        )
        print("Points value has loaded.")

        # 5. Extract and print the points
        points_text = points_element.text
        print(f"SUCCESS! Raw text from element: '{points_text}'")
        
        points_value = re.sub(r'\D', '', points_text)
        print(f"Extracted number: {points_value}")
        
        formatted_points = f"{int(points_value):,}"
        print(f"--- Test complete. Points found: {formatted_points} ---")

    except TimeoutException:
        print("\nERROR: Timed out. The script could not find the points element or the points value did not load in time.")
        print("This could be due to a slow internet connection, or Microsoft may have changed their website layout.")
    except (WebDriverException, ValueError) as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
    finally:
        if driver:
            print("Closing the browser.")
            driver.quit()

if __name__ == "__main__":
    fetch_points(PROFILE_DIRECTORY_NAME)
