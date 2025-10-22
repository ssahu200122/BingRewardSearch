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
from typing import List, Set, Dict, Callable
from datetime import date

from edge_profile import EdgeProfile
from automation_service import AutomationService
# --- MODIFIED: Import POINTS_COLORS and DEFAULT_COLORS ---
from ui_components import ProfileRow, LabeledSlider, POINTS_COLORS, DEFAULT_COLORS
from cmd_colors import colors
from logger import logger
import config

class BingAutomatorApp(customtkinter.CTk):
    """
    The main application class for the Bing Automator GUI.
    """
    def __init__(self, profiles: List[EdgeProfile], automation_service: AutomationService):
        super().__init__() # <-- This is the correct call

        self.profiles = profiles
        self.automation_service = automation_service
        # Ensure profiles list is not empty before creating set
        self.selected_profiles: Set[EdgeProfile] = set(self.profiles) if self.profiles else set()
        self.profile_widget_map: Dict[EdgeProfile, ProfileRow] = {}
        self.settings = self._load_settings() # Loads new delay settings
        self.stop_event = None
        self.selenium_lock = threading.Lock()

        self.left_frame_visible = True
        self.right_frame_visible = True
        self.top_frame_visible = True

        self.original_geometry = config.APP_GEOMETRY
        
        # --- NEW: Define point_brackets here ---
        self.point_brackets = {
            "<1k": (0, 1000), "1k": (1000, 2000), "2k": (2000, 3000),
            "3k": (3000, 4000), "4k": (4000, 5000), "5k": (5000, 6000),
            "6k": (6000, 7000), "7k+": (7000, float('inf'))
        }
        self.cat_labels = {} # Will be populated in _create_widgets
        self.cat_color_indicators = {} # Will be populated in _create_widgets

        self._configure_window()
        self._create_widgets() # Creates new points category labels with colors
        self._update_all_checkbox_text()

        self._update_points_category_display() # Initial category update

        self._load_and_display_initial_progress()

        self._start_scheduler_thread()

    def _load_settings(self) -> dict:
        try:
            with open(config.SETTINGS_JSON_PATH, 'r') as f:
                default_settings = {
                    "schedule_enabled": False,
                    "schedule_time": "08:00",
                    "post_search_delay_min": config.POST_SEARCH_DELAY[0],
                    "post_search_delay_max": config.POST_SEARCH_DELAY[1],
                    "scroll_delay_min": config.SCROLL_DELAY[0],
                    "scroll_delay_max": config.SCROLL_DELAY[1],
                    "mouse_move_duration_min": config.MOUSE_MOVE_DURATION[0],
                    "mouse_move_duration_max": config.MOUSE_MOVE_DURATION[1],
                    "key_press_delay_min": config.KEY_PRESS_DELAY[0],
                    "key_press_delay_max": config.KEY_PRESS_DELAY[1],
                    "smart_search_mode": True,
                }
                settings = json.load(f)
                updated = False
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                        updated = True

                if updated:
                    logger.log("Added default settings (including search mode) to settings.json.", "SYSTEM")
                    try:
                        with open(config.SETTINGS_JSON_PATH, 'w') as f_update:
                             json.dump(settings, f_update, indent=2)
                    except Exception:
                         pass

                return settings
        except (FileNotFoundError, json.JSONDecodeError):
            logger.log("settings.json not found or invalid. Using default settings.", "WARN")
            return {
                "schedule_enabled": False,
                "schedule_time": "08:00",
                "post_search_delay_min": config.POST_SEARCH_DELAY[0],
                "post_search_delay_max": config.POST_SEARCH_DELAY[1],
                "scroll_delay_min": config.SCROLL_DELAY[0],
                "scroll_delay_max": config.SCROLL_DELAY[1],
                "mouse_move_duration_min": config.MOUSE_MOVE_DURATION[0],
                "mouse_move_duration_max": config.MOUSE_MOVE_DURATION[1],
                "key_press_delay_min": config.KEY_PRESS_DELAY[0],
                "key_press_delay_max": config.KEY_PRESS_DELAY[1],
                "smart_search_mode": True,
            }

    def _save_settings(self):
        # Update settings dict from slider values before saving
        self.settings["post_search_delay_min"] = self.post_search_delay_slider.get_min()
        self.settings["post_search_delay_max"] = self.post_search_delay_slider.get_max()
        self.settings["scroll_delay_min"] = self.scroll_delay_slider.get_min()
        self.settings["scroll_delay_max"] = self.scroll_delay_slider.get_max()
        self.settings["mouse_move_duration_min"] = self.mouse_move_slider.get_min()
        self.settings["mouse_move_duration_max"] = self.mouse_move_slider.get_max()
        self.settings["key_press_delay_min"] = self.key_press_slider.get_min()
        self.settings["key_press_delay_max"] = self.key_press_slider.get_max()
        self.settings["smart_search_mode"] = self.search_mode_switch_var.get() == "on"

        try:
            with open(config.SETTINGS_JSON_PATH, 'w') as f:
                json.dump(self.settings, f, indent=2)
            # logger.log(f"Settings saved: {self.settings}", "SYSTEM") # Log less frequently
        except Exception as e:
            logger.log(f"Failed to save settings: {e}", "ERROR")

    # Range Slider Component
    class RangeSlider(customtkinter.CTkFrame):
        def __init__(self, master, text: str, min_val: float, max_val: float, step: float, initial_min: float, initial_max: float, command: Callable = None, value_format:str = "{:.2f}"):
            super().__init__(master, fg_color="transparent")
            self.command = command
            self.min_val = min_val
            self.max_val = max_val
            self.step = step
            self.value_format = value_format

            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)

            self.label = customtkinter.CTkLabel(self, text=text)
            self.label.grid(row=0, column=0, columnspan=2, padx=5, pady=(5,0), sticky="w")

            num_steps = int((max_val - min_val) / step) if step > 0 else 0

            self.slider_min = customtkinter.CTkSlider(self, from_=min_val, to=max_val, number_of_steps=num_steps, command=self._on_min_change)
            self.slider_min.set(initial_min)
            self.slider_min.grid(row=1, column=0, padx=(5, 2.5), pady=5, sticky="ew")

            self.slider_max = customtkinter.CTkSlider(self, from_=min_val, to=max_val, number_of_steps=num_steps, command=self._on_max_change)
            self.slider_max.set(initial_max)
            self.slider_max.grid(row=1, column=1, padx=(2.5, 5), pady=5, sticky="ew")

            self.value_label = customtkinter.CTkLabel(self, text=f"{self.value_format.format(initial_min)} - {self.value_format.format(initial_max)} s")
            self.value_label.grid(row=2, column=0, columnspan=2, padx=5, pady=(0,5))

            self._update_label()

        def _update_label(self):
            min_v = self.get_min()
            max_v = self.get_max()
            self.value_label.configure(text=f"{self.value_format.format(min_v)} - {self.value_format.format(max_v)} s")

        def _on_min_change(self, value):
            current_max = self.slider_max.get()
            if value >= current_max:
                new_min = max(self.min_val, current_max - self.step)
                self.slider_min.set(new_min)
            self._update_label()
            if self.command:
                self.command()

        def _on_max_change(self, value):
            current_min = self.slider_min.get()
            if value <= current_min:
                new_max = min(self.max_val, current_min + self.step)
                self.slider_max.set(new_max)
            self._update_label()
            if self.command:
                self.command()

        def get_min(self) -> float:
            val = self.slider_min.get()
            return round(val / self.step) * self.step if self.step > 0 else val

        def get_max(self) -> float:
            val = self.slider_max.get()
            return round(val / self.step) * self.step if self.step > 0 else val


    def _configure_window(self):
        self.title(config.APP_TITLE)
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        app_width_str, app_height_str = self.original_geometry.split('x')
        app_width = int(app_width_str)
        app_height = int(app_height_str)
        x_coordinate = screen_width - app_width - 230
        y_coordinate = screen_height - app_height - 180
        self.geometry(f"{app_width}x{app_height}+{x_coordinate}+{y_coordinate}")
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        self.top_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="nsew")
        self.top_frame.grid_columnconfigure(0, weight=7)
        self.top_frame.grid_columnconfigure(1, weight=3)
        self.top_frame.grid_rowconfigure(0, weight=1)
        self._create_left_frame()
        self._create_left_frame_collapsed()
        self.left_frame_collapsed.grid_remove()
        self._create_right_frame()
        self._create_right_frame_collapsed()
        self.right_frame_collapsed.grid_remove()

        self.bottom_frame = customtkinter.CTkFrame(self)
        self.bottom_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        action_frame = customtkinter.CTkFrame(self.bottom_frame)
        action_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        action_frame.grid_columnconfigure(4, weight=1)
        self.all_check_var = customtkinter.StringVar(value="on")
        self.all_checkbox = customtkinter.CTkCheckBox(action_frame, text="", variable=self.all_check_var, onvalue="on", offvalue="off", command=self._toggle_all_profiles)
        self.all_checkbox.grid(row=0, column=0, padx=5, pady=5)
        self.optionmenu_var = customtkinter.StringVar(value="Options")
        self.optionmenu = customtkinter.CTkOptionMenu(action_frame, variable=self.optionmenu_var, command=self._optionmenu_callback)
        self.optionmenu.grid(row=0, column=1, padx=5, pady=5)
        self._update_option_menu() # Update menu now adds profiles
        self.close_button = customtkinter.CTkButton(action_frame, text="Close Edge", command=self.automation_service.close_all_edge_windows, fg_color="green")
        self.close_button.grid(row=0, column=2, padx=5, pady=5)
        self.start_button = customtkinter.CTkButton(action_frame, text="Start Searches", command=self._start_automation_thread)
        self.start_button.grid(row=0, column=3, padx=5, pady=5)
        self.search_mode_switch_var = customtkinter.StringVar(value="on" if self.settings["smart_search_mode"] else "off")
        search_mode_switch = customtkinter.CTkSwitch(action_frame, text="Smart Search", variable=self.search_mode_switch_var, onvalue="on", offvalue="off", command=self._on_search_mode_toggle)
        search_mode_switch.grid(row=0, column=4, padx=10, pady=5, sticky="e")
        self.collapse_top_button = customtkinter.CTkButton(action_frame, text="▲", width=25, command=lambda: self._toggle_top_frame())
        self.collapse_top_button.grid(row=0, column=5, padx=5, pady=5)

        progress_frame = customtkinter.CTkFrame(self.bottom_frame, fg_color="transparent")
        progress_frame.grid(row=1, column=0, padx=5, pady=0, sticky="ew")
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

        bottom_info_frame = customtkinter.CTkFrame(self.bottom_frame, fg_color="transparent")
        bottom_info_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        bottom_info_frame.grid_columnconfigure(0, weight=1)

        self.status_label = customtkinter.CTkLabel(bottom_info_frame, text="Ready", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew")

        # Frame for Points Categories Legend
        self.points_category_frame = customtkinter.CTkFrame(bottom_info_frame, fg_color="transparent")
        self.points_category_frame.grid(row=0, column=1, sticky="e")

        label_width = 35 
        for cat_text, pt_range in self.point_brackets.items():
            item_frame = customtkinter.CTkFrame(self.points_category_frame, fg_color="transparent")
            item_frame.pack(side="left", padx=(5, 0))

            range_color = DEFAULT_COLORS
            for points_tuple, color_tuple in POINTS_COLORS.items():
                if points_tuple == pt_range:
                    range_color = color_tuple
                    break

            color_indicator = customtkinter.CTkFrame(item_frame, width=10, height=10, fg_color=range_color, border_width=1, border_color="gray50")
            color_indicator.pack(side="left")
            self.cat_color_indicators[cat_text] = color_indicator

            label = customtkinter.CTkLabel(item_frame, text=f"{cat_text}: 0", width=label_width, anchor="w")
            label.pack(side="left", padx=(2, 0))
            self.cat_labels[cat_text] = label

    def _on_search_mode_toggle(self):
        is_smart = self.search_mode_switch_var.get() == "on"
        mode_text = "Smart Search (Auto-complete)" if is_smart else "Default Search (Fixed count)"
        self._update_status(f"Search mode set to: {mode_text}")
        self._save_settings()

    def _create_left_frame(self):
        self.profile_frame = customtkinter.CTkFrame(self.top_frame)
        self.profile_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.profile_frame.grid_rowconfigure(1, weight=1)
        self.profile_frame.grid_columnconfigure(0, weight=1)
        left_header = customtkinter.CTkFrame(self.profile_frame)
        left_header.grid(row=0, column=0, sticky="ew")
        left_header.grid_columnconfigure(0, weight=1)
        left_title = customtkinter.CTkLabel(left_header, text="Profiles", font=customtkinter.CTkFont(weight="bold"))
        left_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        collapse_left_button = customtkinter.CTkButton(left_header, text="◄", width=25, command=lambda: self._toggle_left_frame())
        collapse_left_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        profile_content_frame = customtkinter.CTkFrame(self.profile_frame, fg_color="transparent")
        profile_content_frame.grid(row=1, column=0, sticky="nsew")
        profile_content_frame.grid_rowconfigure(1, weight=1)
        profile_content_frame.grid_columnconfigure(0, weight=1)
        search_frame = customtkinter.CTkFrame(profile_content_frame, corner_radius=8, border_width=1)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        search_frame.grid_columnconfigure(1, weight=1)
        search_icon_label = customtkinter.CTkLabel(search_frame, text="🔍", width=20, font=("Segoe UI Emoji", 16))
        search_icon_label.grid(row=0, column=0, padx=(10, 5), pady=5)
        self.search_var = customtkinter.StringVar()
        self.search_entry = customtkinter.CTkEntry(search_frame, placeholder_text="Search profiles...", textvariable=self.search_var, border_width=0, fg_color="transparent")
        self.search_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(0, 5))
        self.search_var.trace_add("write", self._filter_profiles)
        self.scrollable_frame = customtkinter.CTkScrollableFrame(profile_content_frame)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for profile in self.profiles:
            profile_widget = ProfileRow(
                self.scrollable_frame,
                profile,
                self._on_profile_select,
                self._on_profile_label_click
            )
            profile_widget.pack(fill="x", expand=True, padx=5, pady=2)
            self.profile_widget_map[profile] = profile_widget

    def _create_left_frame_collapsed(self):
        self.left_frame_collapsed = customtkinter.CTkFrame(self.top_frame)
        self.left_frame_collapsed.grid_columnconfigure(0, weight=1)
        left_title = customtkinter.CTkLabel(self.left_frame_collapsed, text="Profiles", font=customtkinter.CTkFont(weight="bold"))
        left_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        expand_left_button = customtkinter.CTkButton(self.left_frame_collapsed, text="►", width=25, command=lambda: self._toggle_left_frame())
        expand_left_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

    def _create_right_frame(self):
        self.controls_frame = customtkinter.CTkFrame(self.top_frame)
        self.controls_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.controls_frame.grid_rowconfigure(1, weight=1)
        self.controls_frame.grid_columnconfigure(0, weight=1)
        right_header = customtkinter.CTkFrame(self.controls_frame)
        right_header.grid(row=0, column=0, sticky="ew")
        right_header.grid_columnconfigure(0, weight=1)
        right_title = customtkinter.CTkLabel(right_header, text="Controls", font=customtkinter.CTkFont(weight="bold"))
        right_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        collapse_right_button = customtkinter.CTkButton(right_header, text="►", width=25, command=lambda: self._toggle_right_frame())
        collapse_right_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        self.controls_content_frame = customtkinter.CTkScrollableFrame(self.controls_frame)
        self.controls_content_frame.grid(row=1, column=0, sticky="nsew")
        self.controls_content_frame.grid_columnconfigure(0, weight=1)
        self.batch_slider = LabeledSlider(self.controls_content_frame, "Profiles per Batch:", 1, 15, 1, 8, command=self._update_option_menu)
        self.batch_slider.pack(fill="x", padx=10, pady=10, anchor="n")
        self.pc_slider = LabeledSlider(self.controls_content_frame, "PC Searches:", 0, 90, 3, 9)
        self.pc_slider.pack(fill="x", padx=10, pady=10, anchor="n")
        self.fetch_progress_button = customtkinter.CTkButton(self.controls_content_frame, text="Fetch All Points", command=self._start_fetch_progress_thread, fg_color="teal")
        self.fetch_progress_button.pack(fill="x", padx=10, pady=(0, 10))
        behavior_frame = customtkinter.CTkFrame(self.controls_content_frame)
        behavior_frame.pack(fill="x", padx=10, pady=10)
        behavior_title = customtkinter.CTkLabel(behavior_frame, text="Human Behavior Delays", font=customtkinter.CTkFont(weight="bold"))
        behavior_title.pack(padx=10, pady=(5, 10), anchor="w")
        self.post_search_delay_slider = self.RangeSlider(
            behavior_frame, text="Post-Search Pause (s):",
            min_val=0.0, max_val=15.0, step=0.1, # <-- Set min_val to 0.0
            initial_min=self.settings["post_search_delay_min"], initial_max=self.settings["post_search_delay_max"],
            command=self._save_settings
        )
        self.post_search_delay_slider.pack(fill="x", padx=10, pady=5)
        self.scroll_delay_slider = self.RangeSlider(
            behavior_frame, text="Scroll Action Pause (s):",
            min_val=0.0, max_val=5.0, step=0.1, # <-- Set min_val to 0.0
            initial_min=self.settings["scroll_delay_min"], initial_max=self.settings["scroll_delay_max"],
            command=self._save_settings
        )
        self.scroll_delay_slider.pack(fill="x", padx=10, pady=5)
        self.mouse_move_slider = self.RangeSlider(
            behavior_frame, text="Mouse Move Duration (s):",
            min_val=0.0, max_val=1.0, step=0.05, # <-- Set min_val to 0.0
            initial_min=self.settings["mouse_move_duration_min"], initial_max=self.settings["mouse_move_duration_max"],
            command=self._save_settings
        )
        self.mouse_move_slider.pack(fill="x", padx=10, pady=5)
        self.key_press_slider = self.RangeSlider(
            behavior_frame, text="Key Press Delay (s):",
            min_val=0.0, max_val=0.5, step=0.01, # <-- Set min_val to 0.0
            initial_min=self.settings["key_press_delay_min"], initial_max=self.settings["key_press_delay_max"],
            command=self._save_settings, value_format="{:.3f}"
        )
        self.key_press_slider.pack(fill="x", padx=10, pady=5)
        scheduler_frame = customtkinter.CTkFrame(self.controls_content_frame)
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
        theme_label = customtkinter.CTkLabel(self.controls_content_frame, text="Theme:")
        theme_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.theme_switcher = customtkinter.CTkSegmentedButton(self.controls_content_frame, values=["Light", "Dark", "System"], command=self._theme_switch_callback)
        self.theme_switcher.set("System")
        self.theme_switcher.pack(fill="x", padx=10, pady=(5, 10))

    def _create_right_frame_collapsed(self):
        self.right_frame_collapsed = customtkinter.CTkFrame(self.top_frame)
        self.right_frame_collapsed.grid_columnconfigure(0, weight=1)
        right_title = customtkinter.CTkLabel(self.right_frame_collapsed, text="Controls", font=customtkinter.CTkFont(weight="bold"))
        right_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        expand_right_button = customtkinter.CTkButton(self.right_frame_collapsed, text="◄", width=25, command=lambda: self._toggle_right_frame())
        expand_right_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

    def _toggle_left_frame(self):
        self.left_frame_visible = not self.left_frame_visible
        if self.left_frame_visible: self.left_frame_collapsed.grid_remove(); self.profile_frame.grid(); self.top_frame.grid_columnconfigure(0, weight=7)
        else: self.profile_frame.grid_remove(); self.left_frame_collapsed.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew"); self.top_frame.grid_columnconfigure(0, weight=0)

    def _toggle_right_frame(self):
        self.right_frame_visible = not self.right_frame_visible
        if self.right_frame_visible: self.right_frame_collapsed.grid_remove(); self.controls_frame.grid(); self.top_frame.grid_columnconfigure(1, weight=3)
        else: self.controls_frame.grid_remove(); self.right_frame_collapsed.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew"); self.top_frame.grid_columnconfigure(1, weight=0)

    def _toggle_top_frame(self):
        self.top_frame_visible = not self.top_frame_visible
        if self.top_frame_visible: self.top_frame.grid(); self.collapse_top_button.configure(text="▲"); self.grid_rowconfigure(0, weight=1); self.geometry(self.original_geometry)
        else: self.top_frame.grid_remove(); self.collapse_top_button.configure(text="▼"); self.grid_rowconfigure(0, weight=0); self.update_idletasks(); new_height = self.bottom_frame.winfo_reqheight() + 20; self.geometry(f"{self.winfo_width()}x{new_height}")

    def _scroll_to_profile(self, profile: EdgeProfile):
        widget_to_scroll_to = self.profile_widget_map.get(profile)
        if widget_to_scroll_to:
            self.update_idletasks()
            try:
                widget_y = widget_to_scroll_to.winfo_y()
                canvas_height = self.scrollable_frame._parent_canvas.winfo_height()
                widget_height = widget_to_scroll_to.winfo_height()
                scroll_to_y = widget_y - (canvas_height / 2) + (widget_height / 2)
                self.scrollable_frame._scroll_to_y(scroll_to_y)
            except Exception as e:
                try:
                    scrollable_content_height = self.scrollable_frame._parent_canvas.bbox("all")[3]
                    if scrollable_content_height > 0:
                        scroll_fraction = widget_y / scrollable_content_height
                        clamped_position = max(0.0, min(1.0, scroll_fraction))
                        self.scrollable_frame._parent_canvas.yview_moveto(clamped_position)
                except Exception as e_fallback:
                     logger.log(f"Error scrolling to profile (both methods failed): {e_fallback}", "WARN")

    def _update_points_category_display(self):
        counts = {key: 0 for key in self.point_brackets}; total_points = 0; profile_count = 0
        for profile in self.profiles:
            points = profile.available_points; total_points += points; profile_count += 1
            for key, (lower, upper) in self.point_brackets.items():
                if lower <= points < upper: counts[key] += 1; break
        for key, label in self.cat_labels.items():
            if label:
                label.configure(text=f"{key}: {counts.get(key, 0)}")

    def _save_all_profiles_to_json(self):
        all_profiles_data = {};
        for p in self.profiles: all_profiles_data[p.full_name] = p.to_dict()
        try:
            with open(config.PROFILES_JSON_PATH, 'w', encoding='utf-8') as f: json.dump(all_profiles_data, f, indent=2);
        except Exception as e: logger.log(f"Error saving profile data: {e}", "ERROR")

    def _load_and_display_initial_progress(self):
        todays_progress = self.automation_service.load_todays_progress_from_history()
        profile_email_map = {p.email: p for p in self.profiles}
        loaded_today = False
        for email, progress_data in todays_progress.items():
            profile = profile_email_map.get(email)
            if profile:
                widget = self.profile_widget_map.get(profile)
                if widget: widget.update_points_display(progress_data); loaded_today = True
        self._update_points_category_display()

    def _stop_automation(self):
        if self.stop_event: self._update_status("Stop signal sent. Finishing current action..."); self.stop_event.set(); self.start_button.configure(state="disabled"); self.fetch_progress_button.configure(state="disabled")

    def _start_automation_thread(self):
        self.stop_event = threading.Event(); profiles_to_run = sorted([p for p in self.selected_profiles], key=lambda p: p.index)
        if not profiles_to_run: self._update_status("No profiles selected. Nothing to do."); return
        self.start_button.configure(text="Stop", command=self._stop_automation, fg_color="red", hover_color="#C40000"); self.fetch_progress_button.configure(state="disabled")
        thread = threading.Thread(target=self._automation_worker, args=(profiles_to_run, self.stop_event), daemon=True); thread.start()

    def _automation_worker(self, profiles_to_run: List[EdgeProfile], stop_event: threading.Event):
        try:
            self.selenium_lock.acquire()
            todays_progress_history = self.automation_service.load_todays_progress_from_history()
            batch_size = self.batch_slider.get(); pc_searches_target = self.pc_slider.get() // 3; num_profiles = len(profiles_to_run)
            total_possible_searches = num_profiles * pc_searches_target
            if pc_searches_target == 0: self._update_status("PC searches set to 0. Skipping search task.");
            elif total_possible_searches == 0 and num_profiles > 0: self._update_status("Effective searches is 0 (check profile count).")
            elif num_profiles == 0: self._update_status("No profiles selected.")
            else:
                self.overall_progress_label.configure(text=f"0 / {total_possible_searches * 3} Points"); self.overall_progress_bar.set(0)
                self._update_status("Search Automation started..."); searches_completed_so_far = 0
                post_search_delay = (self.settings["post_search_delay_min"], self.settings["post_search_delay_max"])
                scroll_delay = (self.settings["scroll_delay_min"], self.settings["scroll_delay_max"])
                mouse_move_duration = (self.settings["mouse_move_duration_min"], self.settings["mouse_move_duration_max"])
                key_press_delay = (self.settings["key_press_delay_min"], self.settings["key_press_delay_max"])
                is_smart_mode = self.settings.get("smart_search_mode", True)

                for i in range(0, num_profiles, batch_size):
                    if stop_event.is_set(): break
                    batch = profiles_to_run[i:i + batch_size]; batch_num = (i // batch_size) + 1
                    self._update_status(f"Processing Batch {batch_num}...")
                    def create_progress_updater(searches_done_before_this_run, total_searches_in_run):
                        def update_progress_bars(searches_done_this_run, total_searches_this_run_param):
                            progress_val = (searches_done_this_run / total_searches_this_run_param) if total_searches_this_run_param > 0 else 0; self.batch_progress_bar.set(progress_val)
                            self.batch_progress_label.configure(text=f"{searches_done_this_run * 3} / {total_searches_this_run_param * 3} Points")
                            current_overall_searches = searches_done_before_this_run + searches_done_this_run
                            overall_progress_val = (current_overall_searches / total_possible_searches) if total_possible_searches > 0 else 0; self.overall_progress_bar.set(overall_progress_val)
                            self.overall_progress_label.configure(text=f"{current_overall_searches * 3} / {total_possible_searches * 3} Points")
                        return update_progress_bars

                    initial_searches_in_batch = pc_searches_target * len(batch) if pc_searches_target > 0 else 0
                    if initial_searches_in_batch > 0:
                        self.automation_service.run_search_session(profiles=batch, pc_searches=pc_searches_target, stop_event=stop_event, progress_callback=self._update_status, on_search_progress=create_progress_updater(searches_completed_so_far, initial_searches_in_batch), post_search_delay=post_search_delay, scroll_delay=scroll_delay, mouse_move_duration=mouse_move_duration, key_press_delay=key_press_delay)
                        searches_completed_so_far += initial_searches_in_batch

                    if is_smart_mode and not stop_event.is_set() and pc_searches_target > 0:
                        MAX_RETRIES = 5; profiles_to_verify = batch[:]
                        for retry_count in range(MAX_RETRIES):
                            if stop_event.is_set(): break
                            self._update_status(f"Batch {batch_num}: Verifying progress (Attempt {retry_count + 1})...")
                            profiles_to_retry = []; points_needed = []; batch_progress_data = {}
                            for profile in profiles_to_verify:
                                if stop_event.is_set(): break
                                self.after(0, self._scroll_to_profile, profile)
                                widget = self.profile_widget_map.get(profile); points_data = None; cached_data = todays_progress_history.get(profile.email)
                                if cached_data and cached_data.get("daily_progress"):
                                    try:
                                        progress_str = cached_data["daily_progress"]
                                        if "N/A" not in progress_str and "Error" not in progress_str:
                                            earned, max_pts = map(int, re.findall(r'\d+', progress_str))
                                            if earned >= max_pts:
                                                self._update_status(f"Skipping fetch for {profile.name}: Already completed.")
                                                points_data = cached_data
                                                if widget: self.after(0, widget.update_points_display, points_data)
                                    except (ValueError, IndexError):
                                        pass
                                if points_data is None:
                                    if widget: self.after(0, widget.update_points_display, {"daily_progress": "Fetching..."})
                                    points_data = self.automation_service.fetch_points_details(profile, stop_event, headless=True)
                                    if points_data:
                                         todays_progress_history[profile.email] = points_data
                                         try:
                                             cleaned_pts = points_data.get("available_points", "0").replace(",", "");
                                             if cleaned_pts.isdigit():
                                                 profile.available_points = int(cleaned_pts)
                                             else:
                                                 profile.available_points = 0
                                         except (ValueError, AttributeError):
                                             profile.available_points = 0
                                    if widget: self.after(0, widget.update_points_display, points_data)
                                batch_progress_data[profile] = points_data
                                progress_str = points_data.get("daily_progress") if points_data else None
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
                            if total_retry_searches > 0 :
                                 self.automation_service.run_search_session(
                                     profiles=profiles_to_retry, pc_searches=searches_for_next_cycle, stop_event=stop_event, use_retry_delay=use_slower_delay,
                                     progress_callback=self._update_status, on_search_progress=create_progress_updater(searches_completed_so_far, total_retry_searches),
                                     post_search_delay=post_search_delay, scroll_delay=scroll_delay, mouse_move_duration=mouse_move_duration, key_press_delay=key_press_delay
                                 )
                                 searches_completed_so_far += total_retry_searches
                            else:
                                self._update_status(f"Batch {batch_num}: No points needed for retry, skipping.")
                        else:
                            self._update_status(f"Batch {batch_num}: Max retries reached.")
                        
                        if not stop_event.is_set():
                            self._update_status(f"Batch {batch_num}: Saving final progress to history...")
                            if batch_progress_data:
                                for profile, points_data in batch_progress_data.items():
                                     if points_data and "Error" not in points_data.get("daily_progress", ""):
                                         self.automation_service.save_progress_to_history(profile, points_data)
                                         todays_progress_history[profile.email] = points_data
                                self.after(0, self._update_points_category_display)

                    elif not is_smart_mode:
                        self._update_status(f"Batch {batch_num}: Smart Search disabled, skipping point verification.")

                if not stop_event.is_set() and i + batch_size >= num_profiles:
                     if num_profiles > 0 and pc_searches_target > 0:
                          self._update_status(f"Search Automation Complete!")
                elif stop_event.is_set():
                     self._update_status("Search Automation Stopped by User.")

        except Exception as e:
            logger.log(f"Error in automation worker: {e}", "ERROR")
            self._update_status(f"Error occurred: {e}")
        finally:
            self.after(0, self._save_all_profiles_to_json) # Save profile points
            self.start_button.configure(text="Start Searches", command=self._start_automation_thread, state="normal", fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=customtkinter.ThemeManager.theme["CTkButton"]["hover_color"])
            self.fetch_progress_button.configure(state="normal")
            self.stop_event = None
            if self.selenium_lock.locked():
                 self.selenium_lock.release()

    def _start_fetch_progress_thread(self):
        self.stop_event = threading.Event()
        profiles_to_run = sorted(list(self.selected_profiles), key=lambda p: p.index)
        if not profiles_to_run: self._update_status("No profiles selected. Nothing to do."); return
        self.start_button.configure(state="disabled")
        self.fetch_progress_button.configure(text="Stop", command=self._stop_automation, fg_color="red", hover_color="#C40000")
        thread = threading.Thread(target=self._fetch_progress_worker, args=(profiles_to_run, self.stop_event), daemon=True)
        thread.start()

    def _fetch_progress_worker(self, profiles_to_run: List[EdgeProfile], stop_event: threading.Event):
        try:
            total_profiles = len(profiles_to_run)
            if total_profiles == 0: self._update_status("No profiles selected to fetch."); return
            self.selenium_lock.acquire()
            self._update_status("Fetching all points...")
            self.overall_progress_label.configure(text=f"0 / {total_profiles} Profiles"); self.overall_progress_bar.set(0)
            self.batch_progress_label.configure(text="N/A"); self.batch_progress_bar.set(0)
            todays_progress_history = self.automation_service.load_todays_progress_from_history()
            self.automation_service.close_all_edge_windows(); time.sleep(1)
            for i, profile in enumerate(profiles_to_run):
                if stop_event.is_set(): break
                self.after(0, self._scroll_to_profile, profile); widget = self.profile_widget_map.get(profile)
                cached_data = todays_progress_history.get(profile.email); is_complete = False
                if cached_data and cached_data.get("daily_progress"):
                    try:
                        progress_str = cached_data["daily_progress"]
                        if "N/A" not in progress_str and "Error" not in progress_str:
                            earned, max_pts = map(int, re.findall(r'\d+', progress_str))
                            if earned >= max_pts: is_complete = True
                    except (ValueError, IndexError): pass
                if is_complete:
                    self._update_status(f"Skipping fetch for {profile.name}: Already completed (from history).")
                    if widget and cached_data:
                         widget.update_points_display(cached_data)
                         try:
                             cleaned_pts = cached_data.get("available_points", "0").replace(",", "")
                             if cleaned_pts.isdigit(): profile.available_points = int(cleaned_pts)
                             else: profile.available_points = 0
                         except (ValueError, AttributeError): profile.available_points = 0
                else:
                    if widget: widget.update_points_display({"available_points": "Fetching...", "daily_progress": "Fetching..."})
                    points_data = self.automation_service.fetch_points_details(profile, stop_event, headless=True)
                    if points_data and widget:
                        widget.update_points_display(points_data)
                        try:
                            cleaned_pts = points_data.get("available_points", "0").replace(",", "")
                            if cleaned_pts.isdigit(): profile.available_points = int(cleaned_pts)
                            elif "Error" in cleaned_pts: profile.available_points = 0
                            else: profile.available_points = 0
                        except (ValueError, AttributeError): profile.available_points = 0
                        if "Error" not in points_data.get("daily_progress", ""): self.automation_service.save_progress_to_history(profile, points_data)
                self.overall_progress_bar.set((i + 1) / total_profiles); self.overall_progress_label.configure(text=f"{i + 1} / {total_profiles} Profiles")
            if stop_event.is_set(): self._update_status("Points fetching stopped by user.")
            else: self._update_status("Points fetching complete.")
        except Exception as e: logger.log(f"Error in fetch progress worker: {e}", "ERROR"); self._update_status(f"Error occurred during fetch: {e}")
        finally:
            self.after(0, self._update_points_category_display) # Update categories after fetching
            self.after(0, self._save_all_profiles_to_json) # Save fetched points
            self.start_button.configure(state="normal"); self.fetch_progress_button.configure(text="Fetch All Points", command=self._start_fetch_progress_thread, state="normal", fg_color="teal")
            self.stop_event = None;
            if self.selenium_lock.locked(): self.selenium_lock.release()

    def _scheduler_loop(self):
        self._setup_schedule()
        while True:
            schedule.run_pending()
            time.sleep(1)

    def _start_scheduler_thread(self):
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True); scheduler_thread.start()

    def _on_closing(self):
        if self.stop_event: self.stop_event.set()
        self._save_settings(); self._save_all_profiles_to_json(); self.destroy()

    def _toggle_schedule(self):
        self.settings["schedule_enabled"] = self.schedule_switch_var.get() == "on"; self._save_settings()
        status = "enabled" if self.settings["schedule_enabled"] else "disabled"
        self._update_status(f"Scheduler {status}. Will run daily at {self.settings['schedule_time']}."); self._setup_schedule()

    def _save_schedule_time(self, event=None):
        new_time = self.schedule_time_entry.get()
        if re.match(r"^\d{2}:\d{2}$", new_time): self.settings["schedule_time"] = new_time; self._save_settings(); self._update_status(f"Schedule time updated to {new_time}."); self._setup_schedule()
        else: self._update_status("Invalid time format. Please use HH:MM."); self.schedule_time_entry.delete(0, "end"); self.schedule_time_entry.insert(0, self.settings["schedule_time"])

    def _setup_schedule(self):
        schedule.clear()
        if self.settings["schedule_enabled"]: job_time = self.settings["schedule_time"]; schedule.every().day.at(job_time).do(self._run_scheduled_tasks); logger.log(f"Tasks scheduled to run daily at {job_time}.", "SYSTEM")

    def _run_scheduled_tasks(self):
        self._update_status(f"Running scheduled tasks for {time.strftime('%Y-%m-%d')}...")
        stop_event = threading.Event(); profiles_to_run = [p for p in self.profiles] # Run for all profiles
        def task_runner(): self._automation_worker(profiles_to_run, stop_event)
        runner_thread = threading.Thread(target=task_runner, daemon=True); runner_thread.start()

    def _filter_profiles(self, *args):
        search_term = self.search_var.get().lower()
        for widget in self.profile_widget_map.values():
            profile_name = widget.profile.full_name.lower()
            if search_term in profile_name:
                if not widget.winfo_ismapped(): widget.pack(fill="x", expand=True, padx=5, pady=2)
            else:
                if widget.winfo_ismapped(): widget.pack_forget()

    def _on_profile_select(self, profile: EdgeProfile, is_selected: bool):
        if is_selected: self.selected_profiles.add(profile)
        else: self.selected_profiles.discard(profile)
        self._update_all_checkbox_state()

    def _on_profile_label_click(self, profile: EdgeProfile): thread = threading.Thread(target=self.automation_service.open_single_profile_to_breakdown, args=(profile,), daemon=True); thread.start()

    def _toggle_all_profiles(self):
        is_all_selected = self.all_check_var.get() == "on"
        if is_all_selected: self.selected_profiles = set(self.profiles)
        else: self.selected_profiles.clear()
        for widget in self.profile_widget_map.values(): widget.set_checked(is_all_selected)
        self._update_all_checkbox_text()

    def _update_all_checkbox_state(self):
        if not self.profiles: # Handle no profiles loaded
             self.all_check_var.set("off")
        elif len(self.selected_profiles) == len(self.profiles):
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
        batch_options = [f"{i + 1}-{min(i + batch_size, num_profiles)}" for i in range(0, num_profiles, batch_size)]
        points_range_options = [ f"Select {k} Pts" for k in self.point_brackets.keys() ] # Use keys from dict
        standard_options = [ "Options", "Inverse Selection", "Selected Info", "Custom Range...", "--- Select Batches ---", *batch_options, "--- Select by Points ---", *points_range_options, "--- Utilities ---", "Auto-detect Profiles", "Open Log File", "Clear Log File", "View History", "Clear History File" ]
        self.optionmenu.configure(values=standard_options)

    def _optionmenu_callback(self, choice: str):
        if choice.startswith("---") or choice == "Options":
             self.optionmenu_var.set("Options")
             return

        selected_something = False

        if choice == "Inverse Selection":
            all_profiles_set = set(self.profiles)
            self.selected_profiles = all_profiles_set.difference(self.selected_profiles)
            selected_something = True
        elif choice == "Selected Info":
            info_text = f"--- {len(self.selected_profiles)} PROFILES SELECTED ---"
            print(info_text)
            logger.log(info_text, level="DEBUG")
            for p in sorted(list(self.selected_profiles), key=lambda x: x.full_name):
                print(p.full_name)
                logger.log(p.full_name, level="DEBUG")
            self.optionmenu_var.set("Options"); return
        elif choice == "Custom Range...":
            dialog = customtkinter.CTkInputDialog(text="Enter index range (e.g., 1-10):", title="Custom Index Range")
            input_str = dialog.get_input()
            if input_str:
                try:
                    start, end = map(int, input_str.split('-'))
                    start_idx = max(0, start - 1); end_idx = min(len(self.profiles), end)
                    if start_idx < end_idx :
                        self.selected_profiles = set(self.profiles[start_idx:end_idx])
                        selected_something = True
                        logger.log(f"Custom range {input_str} selected ({len(self.selected_profiles)} profiles).")
                    else:
                        self._update_status("Invalid range specified.")
                        logger.log(f"Invalid custom range input (bounds): {input_str}", level="WARN")
                except (ValueError, IndexError):
                    self._update_status("Invalid range format. Use start-end (e.g., 1-5).")
                    logger.log(f"Invalid custom range input (format): {input_str}", level="WARN")
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
        elif choice == "Clear History File":
            if self.automation_service.clear_history_file():
                self._update_status("History file has been cleared.")
                for widget in self.profile_widget_map.values(): widget.update_points_display({})
                for profile in self.profiles: profile.available_points = 0
                self._update_points_category_display()
                self._save_all_profiles_to_json()
            else:
                self._update_status("Could not clear history file. Check logs.")
        elif '-' in choice and 'Pts' not in choice: # Batch range
            try:
                start, end = map(int, choice.split('-'))
                start_idx = max(0, start - 1); end_idx = min(len(self.profiles), end)
                if start_idx < end_idx:
                    self.selected_profiles = set(self.profiles[start_idx : end_idx])
                    selected_something = True
                    logger.log(f"Batch range {choice} selected.")
                else:
                    self._update_status(f"Invalid batch range: {choice}")
            except (ValueError, IndexError):
                 self._update_status(f"Invalid batch range format: {choice}")
                 logger.log(f"Invalid batch range selection from menu: {choice}", level="WARN")
        elif choice.startswith("Select"): # Points range
             range_map = { f"Select {k} Pts": v for k, v in self.point_brackets.items() }
             selected_range = range_map.get(choice)
             if selected_range:
                 lower, upper = selected_range
                 self.selected_profiles = {p for p in self.profiles if lower <= p.available_points < upper}
                 selected_something = True
                 logger.log(f"Selected profiles in points range: {choice} ({len(self.selected_profiles)} found)")
                 self._update_status(f"Selected {len(self.selected_profiles)} profiles with {choice.replace('Select ','')}.")
             else:
                  self._update_status(f"Unrecognized points range: {choice}")
                  logger.log(f"Unrecognized points range selection: {choice}", level="WARN")
        else:
             self._update_status(f"Unrecognized option: {choice}")
             logger.log(f"Unrecognized option menu choice: {choice}", level="WARN")

        if selected_something:
            self._update_selection_ui()

        self.optionmenu_var.set("Options") # Reset dropdown text


    def _update_status(self, message: str):
        self.status_label.configure(text=message); logger.log(message)
        if "complete" in message.lower() or "success" in message.lower(): print(f"{colors.GREEN}{message}{colors.RESET}")
        elif "error" in message.lower() or "fail" in message.lower(): print(f"{colors.RED}{message}{colors.RESET}")
        else: print(message)

    def _theme_switch_callback(self, value: str):
        logger.log(f"Theme changed to {value}", level="SYSTEM"); customtkinter.set_appearance_mode(value.lower())
        for cat_text, pt_range in self.point_brackets.items():
            indicator = self.cat_color_indicators.get(cat_text)
            if indicator:
                range_color = DEFAULT_COLORS
                for points_tuple, color_tuple in POINTS_COLORS.items():
                    if points_tuple == pt_range: range_color = color_tuple; break
                indicator.configure(fg_color=range_color)


    def run(self):
        self.mainloop()