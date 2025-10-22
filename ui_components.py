# BingRewardSearch/ui_components.py

import customtkinter
from typing import Callable
from edge_profile import EdgeProfile

class LabeledSlider(customtkinter.CTkFrame):
    """A custom widget combining a label, a slider, and a value display."""
    def __init__(self, master, text: str, from_: int, to: int, step: int, initial_value: int, command: Callable[[int], None] = None):
        super().__init__(master, fg_color=("gray85","gray25"), corner_radius=6)
        self.command = command

        self.grid_columnconfigure(1, weight=1)

        self.label = customtkinter.CTkLabel(self, text=text)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.slider = customtkinter.CTkSlider(self, from_=from_, to=to, number_of_steps=(to - from_) // step, command=self._on_slider_change)
        self.slider.set(initial_value)
        self.slider.grid(row=1, column=0, padx=(5,2.5), pady=5, sticky="ew")

        self.value_label = customtkinter.CTkLabel(self, text=str(initial_value), width=30)
        self.value_label.grid(row=1, column=1, padx=(2.5,5), pady=5)

    def _on_slider_change(self, value):
        int_value = int(value)
        self.value_label.configure(text=str(int_value))
        if self.command:
            self.command(int_value)

    def get(self) -> int:
        return int(self.slider.get())

class ProfileRow(customtkinter.CTkFrame):
    """A custom widget to display a single profile's information and controls with hover effects."""
    # --- REVERTED: Removed on_default_search_toggle callback ---
    def __init__(self, master, profile: EdgeProfile, on_select: Callable, on_label_click: Callable, on_status_toggle: Callable):
        super().__init__(master, fg_color=("gray90","gray20"), corner_radius=6)
        
        self.profile = profile
        self.on_select = on_select             # Callback for checkbox toggle
        self.on_label_click = on_label_click   # Callback for label click
        self.on_status_toggle = on_status_toggle # Callback for status button

        # --- Grid Configuration ---
        self.grid_columnconfigure(1, weight=1)

        # --- Status Button (Top-Left) ---
        self.status_button = customtkinter.CTkButton(
            self, text=str(profile.index), width=30, height=30, 
            command=self._toggle_status, corner_radius=5
        )
        self.status_button.grid(row=0, column=0, padx=5, pady=(5, 0))
        self._update_status_color()

        # --- Checkbox (Bottom-Left) ---
        self.check_var = customtkinter.StringVar(value="on")
        self.checkbox = customtkinter.CTkCheckBox(
            self, text="", variable=self.check_var, onvalue="on", offvalue="off", 
            command=self._on_select_callback, width=30
        )
        self.checkbox.grid(row=1, column=0, padx=5, pady=(0, 5))

        # --- Profile Label (Top-Right) ---
        self.profile_font = customtkinter.CTkFont(weight="bold", slant="italic", underline=True, size=16)
        self.profile_label = customtkinter.CTkLabel(
            self, text=profile.full_name+" ", anchor="w", cursor="hand2", 
            font=self.profile_font, text_color="#00BFFF" # Light Blue
        )
        self.profile_label.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="ew")
        self.profile_label.bind("<Button-1>", lambda e: self.on_label_click(self.profile))
        self.profile_label.bind("<Enter>", lambda e: self.profile_label.configure(text_color="yellow"))
        self.profile_label.bind("<Leave>", lambda e: self.profile_label.configure(text_color="#00BFFF"))

        # --- Points Frame (Bottom-Right) ---
        self.points_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.points_frame.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="w")

        self.available_points_label = customtkinter.CTkLabel(
            self.points_frame, text="", text_color="#95bdef", font=customtkinter.CTkFont(weight="bold")
        )
        self.available_points_label.pack(side="left")
        
        self.separator_label = customtkinter.CTkLabel(self.points_frame, text="")
        self.separator_label.pack(side="left", padx=5)

        self.daily_progress_label = customtkinter.CTkLabel(self.points_frame, text="",text_color="#4ad342", font=customtkinter.CTkFont(weight="bold"))
        self.daily_progress_label.pack(side="left")
        
        # --- REMOVED: Level Up Frame ---


    def _on_select_callback(self):
        is_selected = self.check_var.get() == "on"
        self.on_select(self.profile, is_selected)

    def set_checked(self, is_checked: bool):
        self.check_var.set("on" if is_checked else "off")

    def update_points_display(self, points_data: dict):
        """Updates the labels with available points and daily progress."""
        available = points_data.get("available_points", "")
        daily = points_data.get("daily_progress", "")
        
        self.available_points_label.configure(text=available if available else "")

        if daily and ("Error" in daily or "N/A" in daily):
            self.daily_progress_label.configure(text=daily, text_color="orange")
        elif daily:
            self.daily_progress_label.configure(text=daily, text_color=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])
        else:
            self.daily_progress_label.configure(text="")
            
        if available and daily and "Fetching" not in daily and "N/A" not in daily and "Error" not in daily:
            self.separator_label.configure(text="|")
        else:
            self.separator_label.configure(text="")

    # --- REMOVED: update_level_up_display ---

    def _toggle_status(self):
        self.profile.status = "suspended" if self.profile.status == "active" else "active"
        self._update_status_color()
        self.on_status_toggle(self.profile)

    def _update_status_color(self):
        if self.profile.status == "active":
            self.status_button.configure(fg_color="green", hover_color="#006400")
        else:
            self.status_button.configure(fg_color="#E30B0B", hover_color="#CD853F")