# BingRewardSearch/ui_components.py

import customtkinter
from typing import Callable
from edge_profile import EdgeProfile

# --- NEW: Define CONTRASTING color ranges ---
# Colors chosen for better contrast
# (Light Mode Color, Dark Mode Color)
POINTS_COLORS = {
    (7000, float('inf')): ("#FF4500", "#191970"), # OrangeRed / Crimson
    (6000, 7000): ("#FFD700", "#006400"), # Gold / DarkGoldenrod
    (5000, 6000): ("#ADFF2F", "#ff0000"), # GreenYellow / DarkOliveGreen
    (4000, 5000): ("#40E0D0", "#ffd700"), # Turquoise / LightSeaGreen
    (3000, 4000): ("#1E90FF", "#00ff00"), # DodgerBlue / MediumBlue
    (2000, 3000): ("#DA70D6", "#00ffff"), # Orchid / DarkOrchid
    (1000, 2000): ("#F4A460", "#ff00ff"), # SandyBrown / SaddleBrown
    (0, 1000): ("#D3D3D3", "#ffb6c1")  # LightGray / DimGray
}
# Define default theme colors to match the lowest bracket
DEFAULT_COLORS = ("#D3D3D3", "#696969") # LightGray / DimGray

class LabeledSlider(customtkinter.CTkFrame):
    # ... (LabeledSlider class unchanged) ...
    def __init__(self, master, text: str, from_: int, to: int, step: int, initial_value: int, command: Callable[[int], None] = None):
        super().__init__(master, fg_color=("gray85","gray25"), corner_radius=6)
        self.command = command; self.grid_columnconfigure(1, weight=1)
        self.label = customtkinter.CTkLabel(self, text=text); self.label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.slider = customtkinter.CTkSlider(self, from_=from_, to=to, number_of_steps=(to - from_) // step, command=self._on_slider_change); self.slider.set(initial_value)
        self.slider.grid(row=1, column=0, padx=(5,2.5), pady=5, sticky="ew")
        self.value_label = customtkinter.CTkLabel(self, text=str(initial_value), width=30); self.value_label.grid(row=1, column=1, padx=(2.5,5), pady=5)
    def _on_slider_change(self, value):
        int_value = int(value); self.value_label.configure(text=str(int_value));
        if self.command:
            self.command(int_value)
    def get(self) -> int: return int(self.slider.get())


class ProfileRow(customtkinter.CTkFrame):
    """A custom widget to display a single profile's information and controls."""
    def __init__(self, master, profile: EdgeProfile, on_select: Callable, on_label_click: Callable):
        initial_color = self._get_color_for_points(profile.available_points)
        super().__init__(master, fg_color=initial_color, corner_radius=6) # Set initial color

        self.profile = profile
        self.on_select = on_select
        self.on_label_click = on_label_click

        self.grid_columnconfigure(1, weight=1)

        self.index_label = customtkinter.CTkLabel(
            self, text=str(profile.index), width=30, height=30,text_color="#ffffff",fg_color= "#34474F",corner_radius=10,
            font=customtkinter.CTkFont(weight="bold")
        )
        self.index_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="n")

        self.check_var = customtkinter.StringVar(value="on")
        self.checkbox = customtkinter.CTkCheckBox(
            self, text="", variable=self.check_var, onvalue="on", offvalue="off",
            command=self._on_select_callback, width=30
        )
        self.checkbox.grid(row=1, column=0, padx=5, pady=5, sticky="n")

        self.profile_font = customtkinter.CTkFont(weight="bold", slant="italic", underline=True, size=16)
        self.profile_label = customtkinter.CTkLabel(
            self, text=profile.full_name+" ", anchor="w", cursor="hand2",
            font=self.profile_font, text_color="#34474F"
        )
        self.profile_label.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="ew")
        self.profile_label.bind("<Button-1>", lambda e: self.on_label_click(self.profile))
        self.profile_label.bind("<Enter>", lambda e: self.profile_label.configure(text_color="yellow"))
        self.profile_label.bind("<Leave>", lambda e: self.profile_label.configure(text_color="#34474F"))

        self.points_frame = customtkinter.CTkFrame(self,corner_radius=20)
        self.points_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.available_points_label = customtkinter.CTkLabel(
            self.points_frame, text="", text_color="#95bdef", font=customtkinter.CTkFont(weight="bold")
        )
        self.available_points_label.pack(side="left",padx=10,pady=5)

        self.separator_label = customtkinter.CTkLabel(self.points_frame, text="" )
        self.separator_label.pack(side="left", padx=5)

        self.daily_progress_label = customtkinter.CTkLabel(self.points_frame, text="",text_color="#4ad342", font=customtkinter.CTkFont(weight="bold"))
        self.daily_progress_label.pack(side="left",padx=10,pady=5)

        initial_points_str = str(profile.available_points) if isinstance(profile.available_points, int) else "N/A"
        self.update_points_display({"available_points": initial_points_str})

    def _get_color_for_points(self, points: int) -> tuple | str:
        """Returns the appropriate (light_color, dark_color) tuple or string for the points."""
        for (lower, upper), color in POINTS_COLORS.items():
            if lower <= points < upper:
                return color
        return DEFAULT_COLORS

    def update_background_color(self):
        """Sets the frame background color based on the profile's current points."""
        new_color = self._get_color_for_points(self.profile.available_points)
        self.configure(fg_color=new_color)

    def _on_select_callback(self):
        is_selected = self.check_var.get() == "on"
        self.on_select(self.profile, is_selected)

    def set_checked(self, is_checked: bool):
        self.check_var.set("on" if is_checked else "off")

    def update_points_display(self, points_data: dict):
        available_str = points_data.get("available_points", "")
        daily = points_data.get("daily_progress", "")
        points_updated = False

        try:
            cleaned_available = available_str.replace(",", "")
            if cleaned_available.isdigit():
                 new_points = int(cleaned_available)
                 if self.profile.available_points != new_points:
                      self.profile.available_points = new_points
                      points_updated = True
                 self.available_points_label.configure(text=available_str)
            elif available_str in ["Fetching...", "Error", "N/A", ""]:
                 if self.profile.available_points != 0:
                     self.profile.available_points = 0
                     points_updated = True
                 self.available_points_label.configure(text=available_str)
            else: # Unexpected string
                 if self.profile.available_points != 0:
                      self.profile.available_points = 0
                      points_updated = True
                 self.available_points_label.configure(text="Error?")

        except (ValueError, AttributeError):
             if self.profile.available_points != 0:
                  self.profile.available_points = 0
                  points_updated = True
             self.available_points_label.configure(text="Error")

        if daily and ("Error" in daily or "N/A" in daily):
            self.daily_progress_label.configure(text=daily, text_color="orange")
        elif daily:
            self.daily_progress_label.configure(text=daily, text_color=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])
        else:
            self.daily_progress_label.configure(text="")

        current_available_text = self.available_points_label.cget("text")
        if current_available_text and daily and "Fetching" not in daily and "N/A" not in daily and "Error" not in daily and "Error" not in current_available_text:
            self.separator_label.configure(text="|")
        else:
            self.separator_label.configure(text="")

        if points_updated:
             self.update_background_color()