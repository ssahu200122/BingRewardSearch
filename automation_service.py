# BingRewardSearch/automation_service.py

import subprocess
import time
from typing import List, Callable, Optional, Dict
import json
import os
import re
import random
import threading
import csv
from datetime import date

# PyAutoGUI Imports for reverted search logic
import pyautogui
import pygetwindow as gw

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# webdriver-manager is no longer used.
from wonderwords import RandomWord

from edge_profile import EdgeProfile
from logger import logger
import config

class AutomationService:
    """
    Handles all browser automation tasks.
    Uses PyAutoGUI for searches and Selenium for daily activities and point scraping.
    """

    def __init__(self):
        self.random_word_generator = RandomWord()
        self.active_drivers = [] # List to keep track of manually opened drivers

    def _setup_driver(self, profile: EdgeProfile, headless: bool = False) -> Optional[webdriver.Edge]:
        """
        Sets up and returns a Selenium WebDriver instance using the manual driver path.
        Can be configured to run in headless mode.
        """
        try:
            edge_options = EdgeOptions()
            
            user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
            edge_options.add_argument(f"user-data-dir={user_data_dir}")
            edge_options.add_argument(f"profile-directory={profile.cmd_arg.split('=')[1]}")
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
            edge_options.add_argument(f'user-agent={user_agent}')
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option('useAutomationExtension', False)
            
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--disable-gpu")

            if headless:
                logger.log("Headless mode enabled for this Selenium session.", "DEBUG")
                edge_options.add_argument("--headless")
                edge_options.add_argument("--window-size=1920,1080")

            service = EdgeService(executable_path="msedgedriver.exe")
            
            driver = webdriver.Edge(service=service, options=edge_options)
            return driver
        except Exception as e:
            logger.log(f"Failed to set up Selenium driver for {profile.name}: {e}", "ERROR")
            return None

    # --- Search and Daily Set Methods ---
    def run_search_session(self, profiles: List[EdgeProfile], pc_searches: int, stop_event: threading.Event, progress_callback: Optional[Callable[[str], None]] = None, on_search_progress: Optional[Callable[[int, int], None]] = None):
        if pc_searches <= 0:
            if progress_callback: progress_callback("PC searches set to 0. Skipping.")
            return

        if progress_callback: progress_callback(f"Starting PyAutoGUI searches for {len(profiles)} profiles...")
        if stop_event.is_set(): return
        
        self._pyautogui_open_profiles(profiles)
        edge_windows = self._pyautogui_get_edge_windows()

        if not edge_windows:
            if progress_callback: progress_callback("Error: No Edge windows found for PC search.")
            self.close_all_edge_windows()
            return

        total_searches_in_batch = pc_searches * len(edge_windows)
        searches_done_in_batch = 0

        try:
            for i in range(pc_searches):
                if stop_event.is_set(): return
                for window in edge_windows:
                    if stop_event.is_set(): return
                    
                    search_term = self._pyautogui_perform_single_search(window)
                    if search_term and progress_callback:
                        progress_callback(f"Search '{search_term}' ({i+1}/{pc_searches}) in window '{window.title}'")
                    
                    searches_done_in_batch += 1
                    if on_search_progress:
                        on_search_progress(searches_done_in_batch, total_searches_in_batch)
        finally:
            time.sleep(random.uniform(*config.BATCH_DELAY))
            self.close_all_edge_windows()

    def run_daily_activities(self, profiles: List[EdgeProfile], stop_event: threading.Event, headless: bool, progress_callback: Optional[Callable[[str], None]] = None, on_activity_progress: Optional[Callable[[int, int], None]] = None):
        if progress_callback: progress_callback("Starting Daily Activities...")
        total_profiles = len(profiles)
        for i, profile in enumerate(profiles):
            if stop_event.is_set(): return
            if progress_callback: progress_callback(f"Processing activities for {profile.name}...")
            
            driver = self._setup_driver(profile, headless=headless)
            if not driver:
                if on_activity_progress: on_activity_progress(i + 1, total_profiles)
                continue
            try:
                if stop_event.is_set(): return
                driver.get("https://rewards.bing.com/")
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Daily set')]")))
                activity_elements = driver.find_elements(By.XPATH, "//*[@data-task-id and .//*[contains(@class, 'points-text')]]")
                if not activity_elements:
                    if progress_callback: progress_callback(f"No activities found for {profile.name}. Might be complete.")
                    continue
                if progress_callback: progress_callback(f"Found {len(activity_elements)} activities for {profile.name}.")
                main_window_handle = driver.current_window_handle
                for index in range(len(activity_elements)):
                    if stop_event.is_set(): break
                    try:
                        activities = driver.find_elements(By.XPATH, "//*[@data-task-id and .//*[contains(@class, 'points-text')]]")
                        activity = activities[index]
                        activity.click()
                        time.sleep(random.uniform(2, 4))
                        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                        new_window_handle = [handle for handle in driver.window_handles if handle != main_window_handle][0]
                        driver.switch_to.window(new_window_handle)
                        try:
                            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "quiz-start-btn"))).click()
                        except TimeoutException:
                            pass
                        for _ in range(10):
                            if stop_event.is_set(): break
                            try:
                                options = driver.find_elements(By.XPATH, "//*[@role='button' and not(@disabled)]")
                                if options:
                                    random.choice(options).click()
                                    time.sleep(random.uniform(1, 2))
                                else:
                                    break
                            except Exception:
                                break
                        driver.close()
                        driver.switch_to.window(main_window_handle)
                        time.sleep(random.uniform(1, 2))
                    except Exception as e:
                        logger.log(f"Error with activity {index} for {profile.name}: {e}", "WARN")
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(main_window_handle)
            except TimeoutException:
                 logger.log(f"Could not find the 'Daily set' container for {profile.name}. Page may have changed.", "ERROR")
            finally:
                if on_activity_progress: on_activity_progress(i + 1, total_profiles)
                if driver: 
                    driver.quit()

    def fetch_daily_search_progress(self, profile: EdgeProfile, stop_event: threading.Event, headless: bool) -> Optional[str]:
        if stop_event.is_set(): return None
        
        driver = self._setup_driver(profile, headless=headless)
        if not driver:
            return "Error"

        try:
            driver.get("https://rewards.bing.com/pointsbreakdown")
            wait = WebDriverWait(driver, 20)
            
            progress_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#bingSearchDailyPoints p.c-caption-1"))
            )
            
            wait.until(lambda d: re.search(r'\d+/\d+', progress_element.text))

            progress_text = progress_element.text.strip()
            
            match = re.search(r'(\d+/\d+\s*pts)', progress_text)
            if match:
                return match.group(1)
            else:
                return "N/A"

        except TimeoutException:
            logger.log(f"Could not find daily search progress for {profile.name}.", "WARN")
            return "N/A"
        except (WebDriverException, ValueError) as e:
            logger.log(f"An error occurred while fetching progress for {profile.name}: {e}", "ERROR")
            return "Error"
        finally:
            if driver:
                driver.quit()

    def open_single_profile_to_breakdown(self, profile: EdgeProfile):
        logger.log(f"Manually opening points breakdown for {profile.name}", "INFO")
        self.close_all_edge_windows()
        time.sleep(1)
        driver = self._setup_driver(profile, headless=False)
        if not driver:
            return
        try:
            driver.get("https://rewards.bing.com/pointsbreakdown")
            self.active_drivers.append(driver)
        except WebDriverException as e:
            logger.log(f"Failed to open browser for {profile.name}: {e}", "ERROR")

    # --- History Methods ---
    def save_progress_to_history(self, profile: EdgeProfile, progress_str: str):
        file_exists = os.path.isfile(config.HISTORY_CSV_PATH)
        try:
            with open(config.HISTORY_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Date", "ProfileName", "Email", "Progress"])
                writer.writerow([date.today().isoformat(), profile.name, profile.email, progress_str])
        except Exception as e:
            logger.log(f"Failed to write to history file: {e}", "ERROR")

    def open_history_file(self) -> bool:
        if os.path.exists(config.HISTORY_CSV_PATH):
            try:
                os.startfile(config.HISTORY_CSV_PATH)
                return True
            except Exception as e:
                logger.log(f"Failed to open history file: {e}", "ERROR")
                return False
        else:
            logger.log(f"History file not found at {config.HISTORY_CSV_PATH}", "WARN")
            return False

    def load_todays_progress_from_history(self) -> Dict[str, str]:
        todays_progress = {}
        today_str = date.today().isoformat()
        if not os.path.exists(config.HISTORY_CSV_PATH):
            return todays_progress
        try:
            with open(config.HISTORY_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Date") == today_str:
                        email = row.get("Email")
                        progress = row.get("Progress")
                        if email and progress:
                            todays_progress[email] = progress
            logger.log(f"Loaded {len(todays_progress)} progress records from today's history.", "INFO")
        except Exception as e:
            logger.log(f"Failed to read history file: {e}", "ERROR")
        return todays_progress

    # --- PyAutoGUI Helper Methods ---
    def _pyautogui_open_profiles(self, profiles: List[EdgeProfile]):
        base_command = ["start", "msedge"]
        for profile in profiles:
            subprocess.Popen(base_command + [profile.cmd_arg], shell=True)
            time.sleep(random.uniform(0.1, 0.4))

    def _pyautogui_get_edge_windows(self) -> List[gw.Win32Window]:
        time.sleep(random.uniform(*config.WAIT_FOR_EDGE_LAUNCH))
        return [win for win in gw.getAllWindows() if "Edge" in win.title]

    def _pyautogui_perform_single_search(self, window: gw.Win32Window):
        try:
            if not window.isActive:
                window.activate()
            time.sleep(random.uniform(*config.ACTION_DELAY))
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(random.uniform(0.3, 0.6))
            search_term = self.random_word_generator.word()
            for char in search_term:
                pyautogui.write(char)
                time.sleep(random.uniform(*config.KEY_PRESS_DELAY))
            pyautogui.press('enter')
            time.sleep(random.uniform(*config.ACTION_DELAY))
            return search_term
        except gw.PyGetWindowException:
            logger.log(f"Could not perform search. Window '{window.title}' may have been closed.", "WARN")
            return None

    # --- Shared and Utility Methods ---
    def close_all_edge_windows(self):
        for driver in self.active_drivers:
            try:
                driver.quit()
            except Exception:
                pass
        self.active_drivers.clear()
        subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.log("Forcefully closed all Edge processes via UI button.", "SYSTEM")

    def get_and_save_edge_profiles(self) -> bool:
        edge_user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
        local_state_path = os.path.join(edge_user_data_dir, "Local State")
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
        except FileNotFoundError:
            logger.log("Edge 'Local State' file not found.", level="ERROR")
            return False
        profile_info = local_state.get("profile", {})
        info_cache = profile_info.get("info_cache", {})
        profiles_order = profile_info.get("profiles_order", [])
        profiles_data = {}
        for profile_id in profiles_order:
            profile_details = info_cache.get(profile_id)
            if not profile_details: continue
            full_name = f"{profile_details.get('user_name', '')} ({profile_details.get('shortcut_name', '')})"
            cmd_arg = f"--profile-directory={profile_id}"
            profiles_data[full_name] = {"cmd": cmd_arg}
        try:
            with open(config.PROFILES_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2)
            logger.log(f"Successfully saved {len(profiles_data)} profiles to {config.PROFILES_JSON_PATH}")
            return True
        except Exception as e:
            logger.log(f"Error saving profiles to JSON: {e}", level="ERROR")
            return False

    def restart_application(self):
        batch_file = None
        if os.path.exists(config.RESTART_BATCH_FILE_ONEDRIVE):
            batch_file = config.RESTART_BATCH_FILE_ONEDRIVE
        elif os.path.exists(config.RESTART_BATCH_FILE_LOCAL):
            batch_file = config.RESTART_BATCH_FILE_LOCAL
        if batch_file:
            logger.log(f"Restarting application via {batch_file}...")
            os.system(f'start "" "{batch_file}"')
        else:
            logger.log("Could not find newBing.bat on OneDrive or Local Desktop.", level="ERROR")

    def open_log_file(self) -> bool:
        log_path = config.LOG_FILE_PATH
        if os.path.exists(log_path):
            try:
                os.startfile(log_path)
                return True
            except Exception as e:
                logger.log(f"Failed to open log file: {e}", level="ERROR")
                return False
        else:
            logger.log(f"Attempted to open non-existent log file: {log_path}", level="WARN")
            return False
