# BingRewardSearch/app.py

import customtkinter
from PIL import Image
import threading
import math
import sys
import json
import time
import schedule
import re
from typing import List, Set, Dict

from edge_profile import EdgeProfile
from automation_service import AutomationService
from ui_components import ProfileRow, LabeledSlider
from cmd_colors import colors
from logger import logger
import config

class BingAutomatorApp(customtkinter.CTk):
    """
    The main application class for the Bing Automator GUI.
    """
    def __init__(self, profiles: List[EdgeProfile], automation_service: AutomationService):
        super().__init__()

        self.profiles = profiles
        self.automation_service = automation_service
        self.selected_profiles: Set[EdgeProfile] = set(self.profiles)
        self.profile_widget_map: Dict[EdgeProfile, ProfileRow] = {}
        self.settings = self._load_settings()
        self.stop_event = None
        self.selenium_lock = threading.Lock() # Lock to prevent concurrent Selenium tasks

        self._configure_window()
        self._create_widgets()
        self._update_all_checkbox_text()
        
        self._load_and_display_initial_progress()
        
        self._start_scheduler_thread()

    def _load_settings(self) -> dict:
        try:
            with open(config.SETTINGS_JSON_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.log("settings.json not found or invalid. Using default settings.", "WARN")
            return {"schedule_enabled": False, "schedule_time": "08:00"}

    def _save_settings(self):
        try:
            with open(config.SETTINGS_JSON_PATH, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.log(f"Settings saved: {self.settings}", "SYSTEM")
        except Exception as e:
            logger.log(f"Failed to save settings: {e}", "ERROR")

    def _configure_window(self):
        self.title(config.APP_TITLE)
        self.geometry(config.APP_GEOMETRY)
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        # --- Left Frame ---
        profile_frame = customtkinter.CTkFrame(self)
        profile_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        profile_frame.grid_rowconfigure(1, weight=1)
        profile_frame.grid_columnconfigure(0, weight=1)
        
        search_frame = customtkinter.CTkFrame(profile_frame, corner_radius=8)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        search_frame.grid_columnconfigure(1, weight=1)

        try:
            search_icon_image = customtkinter.CTkImage(Image.open("search_icon.png"), size=(20, 20))
            search_icon_label = customtkinter.CTkLabel(search_frame, image=search_icon_image, text="")
        except FileNotFoundError:
            logger.log("search_icon.png not found. Using emoji fallback.", level="WARN")
            search_icon_label = customtkinter.CTkLabel(search_frame, text="🔍", width=20, font=("Segoe UI Emoji", 16))
        search_icon_label.grid(row=0, column=0, padx=(10, 5), pady=5)

        self.search_var = customtkinter.StringVar()
        self.search_entry = customtkinter.CTkEntry(search_frame, placeholder_text="Search profiles...", textvariable=self.search_var, border_width=0, fg_color="transparent")
        self.search_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(0, 5))
        self.search_var.trace_add("write", self._filter_profiles)

        self.scrollable_frame = customtkinter.CTkScrollableFrame(profile_frame)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        for profile in self.profiles:
            profile_widget = ProfileRow(self.scrollable_frame, profile, self._on_profile_select, self._on_profile_label_click)
            profile_widget.pack(fill="x", expand=True, padx=5, pady=2)
            self.profile_widget_map[profile] = profile_widget

        # --- Right Frame ---
        controls_frame = customtkinter.CTkScrollableFrame(self)
        controls_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        controls_frame.grid_columnconfigure(0, weight=1)

        self.batch_slider = LabeledSlider(controls_frame, "Profiles per Batch:", 1, 15, 1, 4, command=self._update_option_menu)
        self.pc_slider = LabeledSlider(controls_frame, "PC Searches (x3 points):", 0, 34, 1, 34)
        self.batch_slider.pack(fill="x", padx=10, pady=10, anchor="n")
        self.pc_slider.pack(fill="x", padx=10, pady=10, anchor="n")

        self.daily_sets_button = customtkinter.CTkButton(controls_frame, text="Run Daily Sets", command=self._start_daily_sets_thread, fg_color="#FF8C00", hover_color="#FFA500")
        self.daily_sets_button.pack(fill="x", padx=10, pady=(10, 10))
        
        self.fetch_progress_button = customtkinter.CTkButton(controls_frame, text="Fetch Progress", command=self._start_fetch_progress_thread, fg_color="teal")
        self.fetch_progress_button.pack(fill="x", padx=10, pady=(0, 10))

        scheduler_frame = customtkinter.CTkFrame(controls_frame)
        scheduler_frame.pack(fill="x", padx=10, pady=10)
        scheduler_frame.grid_columnconfigure(1, weight=1)
        scheduler_title = customtkinter.CTkLabel(scheduler_frame, text="Daily Scheduler", font=customtkinter.CTkFont(weight="bold"))
        scheduler_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")
        self.schedule_switch_var = customtkinter.StringVar(value="on" if self.settings["schedule_enabled"] else "off")
        schedule_switch = customtkinter.CTkSwitch(scheduler_frame, text="Enable Schedule", variable=self.schedule_switch_var, onvalue="on", offvalue="off", command=self._toggle_schedule)
        schedule_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        schedule_time_label = customtkinter.CTkLabel(scheduler_frame, text="Run at (24h format):")
        schedule_time_label.grid(row=2, column=0, padx=10, pady=(0, 10))
        self.schedule_time_entry = customtkinter.CTkEntry(scheduler_frame, width=60)
        self.schedule_time_entry.insert(0, self.settings["schedule_time"])
        self.schedule_time_entry.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")
        self.schedule_time_entry.bind("<FocusOut>", self._save_schedule_time)
        self.schedule_time_entry.bind("<Return>", self._save_schedule_time)

        theme_label = customtkinter.CTkLabel(controls_frame, text="Theme:")
        theme_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.theme_switcher = customtkinter.CTkSegmentedButton(controls_frame, values=["Light", "Dark", "System"], command=self._theme_switch_callback)
        self.theme_switcher.set("System")
        self.theme_switcher.pack(fill="x", padx=10, pady=(5, 10))

        # --- Bottom Frame ---
        action_frame = customtkinter.CTkFrame(self)
        action_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        self.all_check_var = customtkinter.StringVar(value="on")
        self.all_checkbox = customtkinter.CTkCheckBox(action_frame, text="", variable=self.all_check_var, onvalue="on", offvalue="off", command=self._toggle_all_profiles)
        self.all_checkbox.grid(row=0, column=0, padx=5, pady=5)
        self.optionmenu_var = customtkinter.StringVar(value="Options")
        self.optionmenu = customtkinter.CTkOptionMenu(action_frame, variable=self.optionmenu_var, command=self._optionmenu_callback)
        self.optionmenu.grid(row=0, column=1, padx=5, pady=5)
        self._update_option_menu()
        self.close_button = customtkinter.CTkButton(action_frame, text="Close Edge", command=self.automation_service.close_all_edge_windows, fg_color="green")
        self.close_button.grid(row=0, column=2, padx=5, pady=5)
        self.start_button = customtkinter.CTkButton(action_frame, text="Start Searches", command=self._start_automation_thread)
        self.start_button.grid(row=0, column=3, padx=5, pady=5)
        
        # --- Progress and Status Frame ---
        progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)
        
        batch_label = customtkinter.CTkLabel(progress_frame, text="Batch:", width=50)
        batch_label.grid(row=0, column=0, padx=(5,0), pady=2, sticky="w")
        self.batch_progress_bar = customtkinter.CTkProgressBar(progress_frame)
        self.batch_progress_bar.set(0)
        self.batch_progress_bar.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.batch_progress_label = customtkinter.CTkLabel(progress_frame, text="0 / 0 Points", width=100, anchor="w")
        self.batch_progress_label.grid(row=0, column=2, padx=5, pady=2)

        overall_label = customtkinter.CTkLabel(progress_frame, text="Overall:", width=50)
        overall_label.grid(row=1, column=0, padx=(5,0), pady=2, sticky="w")
        self.overall_progress_bar = customtkinter.CTkProgressBar(progress_frame)
        self.overall_progress_bar.set(0)
        self.overall_progress_bar.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.overall_progress_label = customtkinter.CTkLabel(progress_frame, text="0 / 0 Points", width=100, anchor="w")
        self.overall_progress_label.grid(row=1, column=2, padx=5, pady=2)

        self.status_label = customtkinter.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

    def _load_and_display_initial_progress(self):
        todays_progress = self.automation_service.load_todays_progress_from_history()
        profile_email_map = {p.email: p for p in self.profiles}
        for email, progress_str in todays_progress.items():
            profile = profile_email_map.get(email)
            if profile:
                widget = self.profile_widget_map.get(profile)
                if widget:
                    widget.update_points(progress_str)

    def _stop_automation(self):
        if self.stop_event:
            self._update_status("Stop signal sent. Finishing current action...")
            self.stop_event.set()
            self.start_button.configure(state="disabled")
            self.daily_sets_button.configure(state="disabled")
            self.fetch_progress_button.configure(state="disabled")

    def _start_automation_thread(self):
        self.stop_event = threading.Event()
        self.start_button.configure(text="Stop", command=self._stop_automation, fg_color="red", hover_color="#C40000")
        self.daily_sets_button.configure(state="disabled")
        self.fetch_progress_button.configure(state="disabled")
        profiles_to_run = [p for p in self.profiles if p in self.selected_profiles]
        thread = threading.Thread(target=self._automation_worker, args=(profiles_to_run, self.stop_event), daemon=True)
        thread.start()

    def _automation_worker(self, profiles_to_run: List[EdgeProfile], stop_event: threading.Event):
        try:
            self.selenium_lock.acquire()
            batch_size = self.batch_slider.get()
            pc_searches_target = self.pc_slider.get() // 3
            num_profiles = len(profiles_to_run)
            
            total_possible_searches = num_profiles * pc_searches_target
            if total_possible_searches == 0:
                 self._update_status("No searches to perform.")
                 return

            self.overall_progress_label.configure(text=f"0 / {total_possible_searches * 3} Points")
            self.overall_progress_bar.set(0)
            self._update_status("Smart Search Automation started...")
            
            searches_completed_so_far = 0

            for i in range(0, num_profiles, batch_size):
                if stop_event.is_set(): break
                
                batch = profiles_to_run[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                self._update_status(f"Processing Batch {batch_num}...")

                def create_progress_updater(searches_done_before_this_run, total_searches_in_run):
                    def update_progress_bars(searches_done_this_run, total_searches_this_run_param):
                        # **FIX**: Use the correct variable name from the inner function's scope
                        self.batch_progress_bar.set(searches_done_this_run / total_searches_this_run_param)
                        self.batch_progress_label.configure(text=f"{searches_done_this_run * 3} / {total_searches_this_run_param * 3} Points")
                        
                        current_overall_searches = searches_done_before_this_run + searches_done_this_run
                        self.overall_progress_bar.set(current_overall_searches / total_possible_searches)
                        self.overall_progress_label.configure(text=f"{current_overall_searches * 3} / {total_possible_searches * 3} Points")
                    return update_progress_bars

                # --- Initial Search ---
                initial_searches_in_batch = pc_searches_target * len(batch)
                self.automation_service.run_search_session(
                    profiles=batch, 
                    pc_searches=pc_searches_target, 
                    stop_event=stop_event,
                    progress_callback=self._update_status,
                    on_search_progress=create_progress_updater(searches_completed_so_far, initial_searches_in_batch)
                )
                searches_completed_so_far += initial_searches_in_batch

                # --- Verify and Retry Loop ---
                MAX_RETRIES = 5
                profiles_to_verify = batch[:]
                for retry_count in range(MAX_RETRIES):
                    if stop_event.is_set(): break
                    
                    self._update_status(f"Batch {batch_num}: Verifying progress (Attempt {retry_count + 1})...")
                    
                    profiles_to_retry = []
                    points_needed = []
                    batch_progress_data = {}

                    for profile in profiles_to_verify:
                        if stop_event.is_set(): break
                        widget = self.profile_widget_map.get(profile)
                        if widget: self.after(0, widget.update_points, "Fetching...")
                        
                        progress_str = self.automation_service.fetch_daily_search_progress(profile, stop_event, headless=True)
                        batch_progress_data[profile] = progress_str
                        
                        if widget: self.after(0, widget.update_points, progress_str)

                        if progress_str and "N/A" not in progress_str and "Error" not in progress_str:
                            try:
                                earned, max_pts = map(int, re.findall(r'\d+', progress_str))
                                if earned < max_pts:
                                    profiles_to_retry.append(profile)
                                    points_needed.append(max_pts - earned)
                            except (ValueError, IndexError):
                                logger.log(f"Could not parse progress string: '{progress_str}'", "WARN")
                    
                    if not profiles_to_retry:
                        self._update_status(f"Batch {batch_num}: All points collected.")
                        break
                    
                    profiles_to_verify = profiles_to_retry[:]

                    max_points_needed = max(points_needed) if points_needed else 0
                    searches_for_next_cycle = math.ceil(max_points_needed / 3)
                    
                    use_slower_delay = len(profiles_to_retry) <= 2
                    
                    self._update_status(f"Batch {batch_num}: {len(profiles_to_retry)} profiles need more points. Retrying with {searches_for_next_cycle} searches...")
                    
                    total_retry_searches = searches_for_next_cycle * len(profiles_to_retry)
                    self.automation_service.run_search_session(
                        profiles=profiles_to_retry, 
                        pc_searches=searches_for_next_cycle, 
                        stop_event=stop_event, 
                        use_retry_delay=use_slower_delay,
                        progress_callback=self._update_status,
                        on_search_progress=create_progress_updater(searches_completed_so_far, total_retry_searches)
                    )
                    searches_completed_so_far += total_retry_searches

                else:
                    self._update_status(f"Batch {batch_num}: Max retries reached.")

                if not stop_event.is_set():
                    self._update_status(f"Batch {batch_num}: Saving final progress to history...")
                    for profile, progress_str in batch_progress_data.items():
                        if progress_str and "Error" not in progress_str and "N/A" not in progress_str:
                            self.automation_service.save_progress_to_history(profile, progress_str)

            if stop_event.is_set():
                self._update_status("Search Automation Stopped by User.")
            else:
                self._update_status(f"{colors.BG_BRIGHT_YELLOW}{colors.BLACK}{colors.BOLD} Search Automation Complete! {colors.RESET}")
        finally:
            self.start_button.configure(text="Start Searches", command=self._start_automation_thread, state="normal", fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=customtkinter.ThemeManager.theme["CTkButton"]["hover_color"])
            self.daily_sets_button.configure(state="normal")
            self.fetch_progress_button.configure(state="normal")
            self.stop_event = None
            self.selenium_lock.release()

    def _start_daily_sets_thread(self):
        self.stop_event = threading.Event()
        self.start_button.configure(state="disabled")
        self.daily_sets_button.configure(text="Stop", command=self._stop_automation, fg_color="red", hover_color="#C40000")
        self.fetch_progress_button.configure(state="disabled")
        profiles_to_run = [p for p in self.profiles if p in self.selected_profiles]
        thread = threading.Thread(target=self._daily_sets_worker, args=(profiles_to_run, self.stop_event), daemon=True)
        thread.start()

    def _daily_sets_worker(self, profiles_to_run: List[EdgeProfile], stop_event: threading.Event):
        try:
            self.selenium_lock.acquire()
            self._update_status("Daily Set Automation started...")
            total_profiles = len(profiles_to_run)
            self.overall_progress_label.configure(text=f"0 / {total_profiles} Profiles")
            self.overall_progress_bar.set(0)
            self.batch_progress_label.configure(text="N/A")
            self.batch_progress_bar.set(0)

            def update_daily_set_progress(profiles_done, total_profiles_to_do):
                self.overall_progress_bar.set(profiles_done / total_profiles_to_do)
                self.overall_progress_label.configure(text=f"{profiles_done} / {total_profiles_to_do} Profiles")
                self.batch_progress_bar.set(profiles_done / total_profiles_to_do)

            self.automation_service.run_daily_activities(profiles=profiles_to_run, stop_event=stop_event, headless=False, progress_callback=self._update_status, on_activity_progress=update_daily_set_progress)
            
            if stop_event.is_set():
                self._update_status("Daily Set Automation Stopped by User.")
            else:
                self._update_status(f"{colors.BG_BRIGHT_YELLOW}{colors.BLACK}{colors.BOLD} Daily Set Automation Complete! {colors.RESET}")
        finally:
            self.start_button.configure(state="normal")
            self.daily_sets_button.configure(text="Run Daily Sets", command=self._start_daily_sets_thread, state="normal", fg_color="#FF8C00", hover_color="#FFA500")
            self.fetch_progress_button.configure(state="normal")
            self.stop_event = None
            self.selenium_lock.release()

    def _start_fetch_progress_thread(self):
        self.stop_event = threading.Event()
        self.start_button.configure(state="disabled")
        self.daily_sets_button.configure(state="disabled")
        self.fetch_progress_button.configure(text="Stop", command=self._stop_automation, fg_color="red", hover_color="#C40000")
        profiles_to_run = [p for p in self.profiles if p in self.selected_profiles]
        thread = threading.Thread(target=self._fetch_progress_worker, args=(profiles_to_run, self.stop_event), daemon=True)
        thread.start()

    def _fetch_progress_worker(self, profiles_to_run: List[EdgeProfile], stop_event: threading.Event):
        try:
            self.selenium_lock.acquire()
            total_profiles = len(profiles_to_run)
            self._update_status("Fetching progress sequentially...")
            self.overall_progress_label.configure(text=f"0 / {total_profiles} Profiles")
            self.overall_progress_bar.set(0)
            self.batch_progress_label.configure(text="N/A")
            self.batch_progress_bar.set(0)

            self.automation_service.close_all_edge_windows()
            time.sleep(1)

            for i, profile in enumerate(profiles_to_run):
                if stop_event.is_set(): break
                
                widget = self.profile_widget_map.get(profile)
                if widget:
                    widget.update_points("Fetching...")

                progress = self.automation_service.fetch_daily_search_progress(profile, stop_event, headless=True)
                
                if progress is not None and widget:
                    widget.update_points(progress)
                    if "Error" not in progress and "N/A" not in progress:
                        self.automation_service.save_progress_to_history(profile, progress)
                
                self.overall_progress_bar.set((i + 1) / total_profiles)
                self.overall_progress_label.configure(text=f"{i + 1} / {total_profiles} Profiles")

            if stop_event.is_set():
                self._update_status("Progress fetching stopped by user.")
            else:
                self._update_status("Progress fetching complete.")
        finally:
            self.start_button.configure(state="normal")
            self.daily_sets_button.configure(state="normal")
            self.fetch_progress_button.configure(text="Fetch Progress", command=self._start_fetch_progress_thread, state="normal", fg_color="teal")
            self.stop_event = None
            self.selenium_lock.release()

    def _start_background_fetch_thread(self):
        thread = threading.Thread(target=self._background_fetch_worker, daemon=True)
        thread.start()

    def _background_fetch_worker(self):
        time.sleep(2)
        background_stop_event = threading.Event()
        main_thread = threading.main_thread()

        if not self.selenium_lock.acquire(blocking=False):
            logger.log("Could not acquire lock for background fetch; another task is running.", "INFO")
            return

        logger.log("Starting initial background progress fetch.", "INFO")
        try:
            for profile in self.profiles:
                if not main_thread.is_alive(): break

                widget = self.profile_widget_map.get(profile)
                if widget:
                    self.after(0, widget.update_points, "Fetching...")

                progress = self.automation_service.fetch_daily_search_progress(profile, background_stop_event, headless=True)
                
                if progress is not None and widget:
                    self.after(0, widget.update_points, progress)
        finally:
            logger.log("Background progress fetch finished.", "INFO")
            self.selenium_lock.release()

    # --- Other Methods ---
    def _scheduler_loop(self):
        self._setup_schedule()
        while True:
            schedule.run_pending()
            time.sleep(1)

    def _start_scheduler_thread(self):
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()

    def _on_closing(self):
        if self.stop_event: self.stop_event.set()
        self._save_settings()
        self.destroy()
        
    def _toggle_schedule(self):
        self.settings["schedule_enabled"] = self.schedule_switch_var.get() == "on"
        self._save_settings()
        status = "enabled" if self.settings["schedule_enabled"] else "disabled"
        self._update_status(f"Scheduler {status}. Will run daily at {self.settings['schedule_time']}.")
        self._setup_schedule()

    def _save_schedule_time(self, event=None):
        new_time = self.schedule_time_entry.get()
        if re.match(r"^\d{2}:\d{2}$", new_time):
            self.settings["schedule_time"] = new_time
            self._save_settings()
            self._update_status(f"Schedule time updated to {new_time}.")
            self._setup_schedule()
        else:
            self._update_status("Invalid time format. Please use HH:MM.")
            self.schedule_time_entry.delete(0, "end")
            self.schedule_time_entry.insert(0, self.settings["schedule_time"])

    def _setup_schedule(self):
        schedule.clear()
        if self.settings["schedule_enabled"]:
            job_time = self.settings["schedule_time"]
            schedule.every().day.at(job_time).do(self._run_scheduled_tasks)
            logger.log(f"Tasks scheduled to run daily at {job_time}.", "SYSTEM")

    def _run_scheduled_tasks(self):
        self._update_status(f"Running scheduled tasks for {time.strftime('%Y-%m-%d')}...")
        stop_event = threading.Event()
        def task_runner():
            self._automation_worker(list(self.selected_profiles), stop_event)
            if not stop_event.is_set():
                self._daily_sets_worker(list(self.selected_profiles), stop_event)
        runner_thread = threading.Thread(target=task_runner, daemon=True)
        runner_thread.start()

    def _filter_profiles(self, *args):
        search_term = self.search_var.get().lower()
        for widget in self.profile_widget_map.values():
            profile_name = widget.profile.full_name.lower()
            if search_term in profile_name:
                if not widget.winfo_ismapped():
                    widget.pack(fill="x", expand=True, padx=5, pady=2)
            else:
                if widget.winfo_ismapped():
                    widget.pack_forget()
    
    def _on_profile_select(self, profile: EdgeProfile, is_selected: bool):
        if is_selected:
            self.selected_profiles.add(profile)
        else:
            self.selected_profiles.discard(profile)
        self._update_all_checkbox_state()

    def _on_profile_label_click(self, profile: EdgeProfile):
        thread = threading.Thread(target=self.automation_service.open_single_profile_to_breakdown, args=(profile,), daemon=True)
        thread.start()

    def _toggle_all_profiles(self):
        is_all_selected = self.all_check_var.get() == "on"
        if is_all_selected:
            self.selected_profiles = set(self.profiles)
        else:
            self.selected_profiles.clear()
        for widget in self.profile_widget_map.values():
            widget.set_checked(is_all_selected)
        self._update_all_checkbox_text()

    def _update_all_checkbox_state(self):
        if len(self.selected_profiles) == len(self.profiles):
            self.all_check_var.set("on")
        else:
            self.all_check_var.set("off")
        self._update_all_checkbox_text()

    def _update_all_checkbox_text(self):
        self.all_checkbox.configure(text=f"All ({len(self.selected_profiles)}/{len(self.profiles)})")

    def _update_selection_ui(self):
        for widget in self.profile_widget_map.values():
            widget.set_checked(widget.profile in self.selected_profiles)
        self._update_all_checkbox_state()

    def _update_option_menu(self, value=None):
        batch_size = self.batch_slider.get()
        num_profiles = len(self.profiles)
        options = [f"{i}-{i + batch_size}" for i in range(0, num_profiles, batch_size)]
        full_options = ["Options", "Inverse Selection", "Selected Info", "Custom Range...", "Auto-detect Profiles", "Open Log File", "Clear Log File", "View History"] + options
        self.optionmenu.configure(values=full_options)

    def _optionmenu_callback(self, choice: str):
        if choice == "Inverse Selection":
            all_profiles_set = set(self.profiles)
            self.selected_profiles = all_profiles_set.difference(self.selected_profiles)
            self._update_selection_ui()
        elif choice == "Selected Info":
            info_text = f"--- {len(self.selected_profiles)} PROFILES SELECTED ---"
            print(info_text)
            logger.log(info_text, level="DEBUG")
            for p in sorted(list(self.selected_profiles), key=lambda x: x.full_name):
                print(p.full_name)
                logger.log(p.full_name, level="DEBUG")
        elif choice == "Custom Range...":
            dialog = customtkinter.CTkInputDialog(text="Enter range (e.g., 0-9):", title="Custom Range")
            input_str = dialog.get_input()
            if input_str:
                try:
                    start, end = map(int, input_str.split('-'))
                    self.selected_profiles = set(self.profiles[start:end+1])
                    self._update_selection_ui()
                    logger.log(f"Custom range {input_str} selected.")
                except (ValueError, IndexError):
                    self._update_status("Invalid range format. Use start-end.")
                    logger.log(f"Invalid custom range input: {input_str}", level="WARN")
        elif choice == "Auto-detect Profiles":
            self._update_status("Detecting profiles...")
            if self.automation_service.get_and_save_edge_profiles():
                self._update_status("Profiles saved. Restarting application...")
                self.automation_service.restart_application()
                sys.exit()
            else:
                self._update_status("Failed to detect and save profiles.")
        elif choice == "Open Log File":
            if self.automation_service.open_log_file():
                self._update_status("Opening log file...")
            else:
                self._update_status("Could not open log file. See log for details.")
        elif choice == "Clear Log File":
            logger.clear_log()
            self._update_status("Log file has been cleared.")
        elif choice == "View History":
            if self.automation_service.open_history_file():
                self._update_status("Opening history file...")
            else:
                self._update_status("Could not open history file. Fetch some progress first.")
        elif '-' in choice:
            try:
                start, end = map(int, choice.split('-'))
                self.selected_profiles = set(self.profiles[start:end])
                self._update_selection_ui()
                logger.log(f"Range {choice} selected.")
            except (ValueError, IndexError):
                 self._update_status(f"Invalid range: {choice}")
                 logger.log(f"Invalid range selection from menu: {choice}", level="WARN")
        self.optionmenu_var.set("Options")

    def _chech_checkbox_event(self):
        pass

    def _check_button_callback(self):
        self._update_status("This feature is disabled.")

    def _update_status(self, message: str):
        self.status_label.configure(text=message)
        logger.log(message)
        if "complete" in message.lower() or "success" in message.lower():
            print(f"{colors.GREEN}{message}{colors.RESET}")
        elif "error" in message.lower() or "fail" in message.lower():
            print(f"{colors.RED}{message}{colors.RESET}")
        else:
            print(message)

    def _update_batch_progress(self, value: float):
        self.batch_progress_bar.set(value)

    def _update_overall_progress(self, value: float):
        self.overall_progress_bar.set(value)

    def _theme_switch_callback(self, value: str):
        logger.log(f"Theme changed to {value}", level="SYSTEM")
        customtkinter.set_appearance_mode(value.lower())
        
    def run(self):
        self.mainloop()
