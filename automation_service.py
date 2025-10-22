# BingRewardSearch/automation_service.py

import subprocess
import time
from typing import List, Callable, Optional, Dict, Tuple
import json
import os
import re
import random
import threading
import csv
from datetime import date

# PyAutoGUI Imports
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

from wonderwords import RandomWord
import wikipediaapi

from edge_profile import EdgeProfile
from logger import logger
import config

# --- Human-like Search Query Generator (Unchanged) ---
class SearchQueryGenerator:
    def __init__(self):
        self.random_word_gen = RandomWord()
        self.wiki_api = wikipediaapi.Wikipedia('BingRewardSearchBot (merci-k@example.com)', 'en')
        self.common_phrases = ["what is", "how to", "why is", "where is", "when did", "best way to", "recipe for", "news about", "weather in", "top 10", "reviews for", "compare", "deals for", "meaning of", "history of", "facts about"]
        logger.log("SearchQueryGenerator initialized.", "SYSTEM")
    def _get_simple_word(self) -> str: return self.random_word_gen.word()
    def _get_search_phrase(self) -> str: prefix = random.choice(self.common_phrases); suffix = self.random_word_gen.word(include_parts_of_speech=["nouns", "adjectives"]); return f"{prefix} {suffix}"
    def _get_wikipedia_topic(self) -> str:
        try:
            random_page = self.wiki_api.page(title=None, pageid=None, params={'generator': 'random', 'grnnamespace': 0, 'grnlimit': 1})
            if random_page and random_page.exists(): title = random_page.title;
            if len(title) > 8 and len(title) < 75 and ":" not in title: return title
        except Exception as e: logger.log(f"Error fetching Wikipedia title: {e}", "WARN")
        return self._get_simple_word()
    def get_search_term(self) -> str:
        search_type = random.choices(['phrase', 'simple_word', 'wikipedia_topic'], weights=[0.5, 0.3, 0.2], k=1)[0]
        if search_type == 'phrase': return self._get_search_phrase()
        elif search_type == 'wikipedia_topic': return self._get_wikipedia_topic()
        else: return self._get_simple_word()


class AutomationService:
    def __init__(self):
        self.query_generator = SearchQueryGenerator()
        self.active_drivers = []
        pyautogui.FAILSAFE = False
        self.screen_width, self.screen_height = pyautogui.size()

    def _setup_driver(self, profile: EdgeProfile, headless: bool = False) -> Optional[webdriver.Edge]:
        try:
            edge_options = EdgeOptions(); user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
            edge_options.add_argument(f"user-data-dir={user_data_dir}"); edge_options.add_argument(f"profile-directory={profile.cmd_arg.split('=')[1]}")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
            edge_options.add_argument(f'user-agent={user_agent}'); edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"]); edge_options.add_experimental_option('useAutomationExtension', False)
            edge_options.add_argument("--no-sandbox"); edge_options.add_argument("--disable-dev-shm-usage"); edge_options.add_argument("--disable-gpu")
            if headless: edge_options.add_argument("--headless"); edge_options.add_argument("--window-size=1920,1080"); logger.log("Headless mode enabled for Selenium points fetching.", "DEBUG")
            service = EdgeService(executable_path="msedgedriver.exe"); driver = webdriver.Edge(service=service, options=edge_options); return driver
        except Exception as e: logger.log(f"Failed to set up Selenium driver for {profile.name}: {e}", "ERROR"); return None

    def run_search_session(self, profiles: List[EdgeProfile], pc_searches: int, stop_event: threading.Event, use_retry_delay: bool = False, progress_callback: Optional[Callable[[str], None]] = None, on_search_progress: Optional[Callable[[int, int], None]] = None, post_search_delay: Tuple[float, float] = config.POST_SEARCH_DELAY, scroll_delay: Tuple[float, float] = config.SCROLL_DELAY, mouse_move_duration: Tuple[float, float] = config.MOUSE_MOVE_DURATION, key_press_delay: Tuple[float, float] = config.KEY_PRESS_DELAY):
        if pc_searches <= 0:
            if progress_callback: progress_callback("PC searches set to 0. Skipping.")
            return
        if progress_callback: progress_callback(f"Starting PyAutoGUI searches for {len(profiles)} profiles...")
        if stop_event.is_set(): return
        self._pyautogui_open_profiles(profiles); edge_windows = self._pyautogui_get_edge_windows()
        if not edge_windows:
            if progress_callback: progress_callback("Error: No Edge windows found for PC search.")
            self.close_all_edge_windows(); return
        total_searches_in_batch = pc_searches * len(edge_windows); searches_done_in_batch = 0
        try:
            for i in range(pc_searches):
                if stop_event.is_set(): return
                for window in edge_windows:
                    if stop_event.is_set(): return
                    search_term = self._pyautogui_perform_single_search(window, use_retry_delay, post_search_delay, scroll_delay, mouse_move_duration, key_press_delay)
                    if search_term and progress_callback: progress_callback(f"Search '{search_term}' ({i+1}/{pc_searches}) in window '{window.title}'")
                    searches_done_in_batch += 1
                    if on_search_progress: on_search_progress(searches_done_in_batch, total_searches_in_batch)
        finally:
            self._pyautogui_human_like_pause(*config.BATCH_DELAY); self.close_all_edge_windows()

    def fetch_points_details(self, profile: EdgeProfile, stop_event: threading.Event, headless: bool) -> Dict[str, Optional[str]]:
        if stop_event.is_set(): return {"available_points": None, "daily_progress": None}
        driver = self._setup_driver(profile, headless=headless)
        if not driver: return {"available_points": "Error", "daily_progress": "Error"}
        points_data = {"available_points": "N/A", "daily_progress": "N/A"}
        try:
            wait = WebDriverWait(driver, 20); driver.get("https://rewards.bing.com/")
            available_points_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mee-rewards-user-status-banner-balance p.pointsValue span")))
            points_data["available_points"] = available_points_element.text.strip()
            driver.get("https://rewards.bing.com/pointsbreakdown")
            progress_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#bingSearchDailyPoints p.c-caption-1")))
            wait.until(lambda d: re.search(r'\d+/\d+', progress_element.text))
            match = re.search(r'(\d+/\d+\s*pts)', progress_element.text.strip())
            if match: points_data["daily_progress"] = match.group(1)
            return points_data
        except TimeoutException: logger.log(f"Timeout fetching points for {profile.name}.", "WARN"); return points_data
        except (WebDriverException, ValueError) as e: logger.log(f"Error fetching points for {profile.name}: {e}", "ERROR"); return {"available_points": "Error", "daily_progress": "Error"}
        finally:
            if driver: driver.quit()

    def open_single_profile_to_breakdown(self, profile: EdgeProfile):
        logger.log(f"Manually opening points breakdown for {profile.name}", "INFO")
        self.close_all_edge_windows(); self._pyautogui_human_like_pause(0.5, 1)
        base_command = ["start", "msedge"]
        try:
            subprocess.Popen(base_command + [profile.cmd_arg], shell=True); self._pyautogui_human_like_pause(*config.WAIT_FOR_EDGE_LAUNCH)
            link = "https://rewards.bing.com/pointsbreakdown"; active_window = gw.getActiveWindow()
            if active_window and "Edge" in active_window.title:
                 pyautogui.hotkey('ctrl', 'l'); self._pyautogui_human_like_pause(0.3, 0.6)
                 pyautogui.write(link, interval=random.uniform(*config.KEY_PRESS_DELAY))
                 self._pyautogui_human_like_pause(0.2, 0.4); pyautogui.press('enter')
            else: logger.log(f"Could not activate Edge window for {profile.name} to navigate.", "WARN")
        except Exception as e: logger.log(f"Failed to open/navigate browser for {profile.name}: {e}", "ERROR")

    # --- History Methods (Unchanged) ---
    def save_progress_to_history(self, profile: EdgeProfile, points_data: Dict[str, str]):
        file_exists = os.path.isfile(config.HISTORY_CSV_PATH)
        try:
            with open(config.HISTORY_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f);
                if not file_exists: writer.writerow(["Date", "ProfileName", "Email", "AvailablePoints", "DailyProgress"])
                writer.writerow([date.today().isoformat(), profile.name, profile.email, points_data.get("available_points", "N/A"), points_data.get("daily_progress", "N/A")])
        except Exception as e: logger.log(f"Failed to write to history file: {e}", "ERROR")
    def open_history_file(self) -> bool:
        if os.path.exists(config.HISTORY_CSV_PATH):
            try: os.startfile(config.HISTORY_CSV_PATH); return True
            except Exception as e: logger.log(f"Failed to open history file: {e}", "ERROR"); return False
        else: logger.log(f"History file not found at {config.HISTORY_CSV_PATH}", "WARN"); return False
    def clear_history_file(self) -> bool:
        history_path = config.HISTORY_CSV_PATH
        if os.path.exists(history_path):
            try: os.remove(history_path); logger.log("History file cleared by user.", level="SYSTEM"); return True
            except OSError as e: logger.log(f"Failed to clear history file: {e}", level="ERROR"); return False
        else: logger.log("History file not found, nothing to clear.", level="INFO"); return True
    def load_todays_progress_from_history(self) -> Dict[str, Dict[str, str]]:
        todays_progress = {}; today_str = date.today().isoformat()
        if not os.path.exists(config.HISTORY_CSV_PATH):
            return todays_progress
        try:
            with open(config.HISTORY_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Date") == today_str:
                        email = row.get("Email")
                        if email: todays_progress[email] = {"available_points": row.get("AvailablePoints", "N/A"), "daily_progress": row.get("DailyProgress", "N/A")}
            if len(todays_progress) > 0: logger.log(f"Loaded {len(todays_progress)} progress records from today's history.", "INFO")
            else: logger.log("No progress records found for today in history.", "INFO")
        except FileNotFoundError: logger.log("History file not found during load.", "WARN")
        except Exception as e: logger.log(f"Failed to read or process history file: {e}", "ERROR")
        return todays_progress

    # --- PyAutoGUI Helper Methods (Unchanged) ---
    def _pyautogui_human_like_pause(self, min_seconds, max_seconds):
        if min_seconds > max_seconds: min_seconds = max_seconds
        time.sleep(random.uniform(min_seconds, max_seconds))
    def _pyautogui_random_mouse_move(self, mouse_move_duration: Tuple[float, float]):
        try:
            current_x, current_y = pyautogui.position(); offset_x = random.randint(-150, 150); offset_y = random.randint(-150, 150)
            new_x = max(0, min(self.screen_width - 1, current_x + offset_x)); new_y = max(0, min(self.screen_height - 1, current_y + offset_y))
            move_duration_value = random.uniform(*mouse_move_duration)
            pyautogui.moveTo(new_x, new_y, duration=move_duration_value, tween=pyautogui.easeOutQuad)
        except Exception as e: logger.log(f"Error during random mouse move: {e}", "WARN")
    def _pyautogui_random_scroll(self, scroll_delay: Tuple[float, float]):
        try:
            scroll_count = random.randint(1, 4)
            for _ in range(scroll_count):
                scroll_amount_units = random.randint(100, 300)
                pyautogui.scroll(scroll_amount_units if random.choice([True, False]) else -scroll_amount_units)
                self._pyautogui_human_like_pause(*scroll_delay)
        except Exception as e: logger.log(f"Error during random scroll: {e}", "WARN")
    def _pyautogui_open_profiles(self, profiles: List[EdgeProfile]):
        base_command = ["start", "msedge"]
        for profile in profiles: subprocess.Popen(base_command + [profile.cmd_arg], shell=True); self._pyautogui_human_like_pause(0.1, 0.4)
    def _pyautogui_get_edge_windows(self) -> List[gw.Win32Window]:
        self._pyautogui_human_like_pause(*config.WAIT_FOR_EDGE_LAUNCH)
        return [win for win in gw.getAllWindows() if "Edge" in win.title]
    def _pyautogui_perform_single_search(self, window: gw.Win32Window, use_retry_delay: bool, post_search_delay: Tuple[float, float], scroll_delay: Tuple[float, float], mouse_move_duration: Tuple[float, float], key_press_delay: Tuple[float, float]):
        action_delay_range = config.RETRY_ACTION_DELAY if use_retry_delay else config.ACTION_DELAY
        try:
            if not window.isActive: window.activate(); self._pyautogui_human_like_pause(0.1, 0.3)
            self._pyautogui_human_like_pause(*action_delay_range)
            if random.random() < 0.3: self._pyautogui_random_mouse_move(mouse_move_duration)
            pyautogui.hotkey('ctrl', 'l'); self._pyautogui_human_like_pause(0.3, 0.6)
            search_term = self.query_generator.get_search_term()
            type_interval = random.uniform(*key_press_delay); type_interval = max(0.001, type_interval)
            pyautogui.write(search_term, interval=type_interval)
            pyautogui.press('enter'); self._pyautogui_human_like_pause(*post_search_delay)
            if random.random() < 0.5: self._pyautogui_random_scroll(scroll_delay)
            elif random.random() < 0.2: self._pyautogui_random_mouse_move(mouse_move_duration)
            return search_term
        except gw.PyGetWindowException: logger.log(f"Window '{window.title}' closed during search.", "WARN"); return None
        except Exception as e: logger.log(f"Error during PyAutoGUI search: {e}", "ERROR"); return None

    # --- Shared and Utility Methods ---
    def close_all_edge_windows(self):
        subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.log("Forcefully closed all Edge processes.", "SYSTEM")

    # --- MODIFIED: Removed merging logic ---
    def get_and_save_edge_profiles(self) -> bool:
        """Detects all Edge profiles and overwrites data.json."""
        edge_user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
        local_state_path = os.path.join(edge_user_data_dir, "Local State")
        
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
        except FileNotFoundError:
            logger.log("Edge 'Local State' file not found.", level="ERROR")
            return False
        except Exception as e:
            logger.log(f"Error reading 'Local State' file: {e}", "ERROR")
            return False

        profile_info = local_state.get("profile", {})
        info_cache = profile_info.get("info_cache", {})
        profiles_order = profile_info.get("profiles_order", [])
        
        # This dictionary will contain ONLY the newly detected profiles
        profiles_data = {}
        
        for profile_id in profiles_order:
            profile_details = info_cache.get(profile_id)
            if not profile_details: continue
            
            full_name = f"{profile_details.get('user_name', '')} ({profile_details.get('shortcut_name', '')})"
            cmd_arg = f"--profile-directory={profile_id}"
            
            # Add the new profile with default values.
            # The 'available_points' will be 0 by default when loaded next.
            profiles_data[full_name] = {
                "cmd": cmd_arg
                # We no longer add status or points here
            }

        try:
            # Overwrite data.json with ONLY the newly detected profiles
            with open(config.PROFILES_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2)
            
            logger.log(f"Successfully OVERWRITTEN {config.PROFILES_JSON_PATH} with {len(profiles_data)} detected profiles.")
            return True
        except Exception as e:
            logger.log(f"Error saving profiles to JSON: {e}", level="ERROR")
            return False

    def restart_application(self):
        # ... (Unchanged) ...
        batch_file = None
        if os.path.exists(config.RESTART_BATCH_FILE_ONEDRIVE): batch_file = config.RESTART_BATCH_FILE_ONEDRIVE
        elif os.path.exists(config.RESTART_BATCH_FILE_LOCAL): batch_file = config.RESTART_BATCH_FILE_LOCAL
        if batch_file: logger.log(f"Restarting application via {batch_file}..."); os.system(f'start "" "{batch_file}"')
        else: logger.log("Could not find newBing.bat on OneDrive or Local Desktop.", level="ERROR")

    def open_log_file(self) -> bool:
        # ... (Unchanged) ...
        log_path = config.LOG_FILE_PATH
        if os.path.exists(log_path):
            try: os.startfile(log_path); return True
            except Exception as e: logger.log(f"Failed to open log file: {e}", level="ERROR"); return False
        else: logger.log(f"Attempted to open non-existent log file: {log_path}", level="WARN"); return False