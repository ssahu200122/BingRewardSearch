# BingRewardSearch/ui_components.py

import customtkinter
from typing import Callable
from edge_profile import EdgeProfile

class LabeledSlider(customtkinter.CTkFrame):
    """
    A custom widget combining a CTkLabel and a CTkSlider.
    """
    def __init__(self, master, text, from_, to, step, initial_value, command=None):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.label = customtkinter.CTkLabel(self, text=f"{text} {initial_value}", anchor="w")
        self.label.grid(row=0, column=0, sticky="ew", padx=5)
        self.slider = customtkinter.CTkSlider(self, from_=from_, to=to, number_of_steps=(to - from_) // step, command=self._update_label)
        self.slider.set(initial_value)
        self.slider.grid(row=1, column=0, sticky="ew", padx=5)
        self.text = text
        self.command = command

    def _update_label(self, value):
        self.label.configure(text=f"{self.text} {int(value)}")
        if self.command:
            self.command(value)

    def get(self):
        return int(self.slider.get())

class ProfileRow(customtkinter.CTkFrame):
    """
    A custom widget representing a single profile in the list with a two-row design.
    """
    def __init__(self, master, profile: EdgeProfile, on_select_callback: Callable, on_label_click_callback: Callable, on_status_toggle_callback: Callable):
        # Made the background color slightly darker for dark mode
        super().__init__(master, fg_color=("gray90", "gray25"), corner_radius=8)
        self.profile = profile
        self.on_select_callback = on_select_callback
        self.on_label_click_callback = on_label_click_callback
        self.on_status_toggle_callback = on_status_toggle_callback

        # --- Grid Layout Configuration ---
        self.grid_columnconfigure(1, weight=1) # Make the label column expandable

        # --- Row 1 Widgets: Status Button and Profile Label ---
        self.status_button = customtkinter.CTkButton(
            self,
            text=str(profile.index), # Display index number
            width=40,
            corner_radius=8, # Rounded corners for a square-like shape
            command=self._toggle_status
        )
        self.status_button.grid(row=0, column=0, padx=(5, 10), pady=(5, 2))
        self._update_status_button_color()

        self.profile_font = customtkinter.CTkFont(size=14, weight="bold", slant="italic", underline=True)
        self.label_color_active = "#3b82f6" # Light blue for active profiles
        self.label_color_suspended = "gray60" # Gray for suspended profiles
        self.label_hover_color = "#FFD700" # Yellow/Gold color for hover

        self.label = customtkinter.CTkLabel(
            self,
            # --- MODIFICATION START ---
            # Add a non-breaking space to prevent the last character from being cut off
            text=profile.full_name + "\u00A0", 
            # --- MODIFICATION END ---
            font=self.profile_font,
            anchor="w"
        )
        # Removed the incorrect padding fix from the previous version
        self.label.grid(row=0, column=1, pady=(5, 2), sticky="ew")
        
        # Bind events for hover effect and clicking
        self.label.bind("<Button-1>", self._on_label_click)
        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        
        # --- Row 2 Widgets: Points Label and Checkbox ---
        self.points_label = customtkinter.CTkLabel(
            self,
            text="",
            anchor="w",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            text_color=("gray98", "#A7D3A4") # Light green text color
        )
        self.points_label.grid(row=1, column=1, padx=0, pady=(0, 5), sticky="w")

        self.check_var = customtkinter.StringVar(value="on")
        self.checkbox = customtkinter.CTkCheckBox(
            self,
            text="",
            variable=self.check_var,
            onvalue="on",
            offvalue="off",
            command=self._on_select,
            width=25
        )
        self.checkbox.grid(row=1, column=0, padx=(5, 10), pady=(0, 5))
        
        # Set initial label color based on status
        self._update_label_color()

    def _on_enter(self, event):
        """Handler for mouse entering the label area."""
        self.label.configure(text_color=self.label_hover_color, cursor="hand2")

    def _on_leave(self, event):
        """Handler for mouse leaving the label area."""
        # Restore the correct color based on status, not a fixed color
        self._update_label_color()
        self.label.configure(cursor="")

    def _toggle_status(self):
        """Toggles the profile status between 'active' and 'suspended'."""
        self.profile.status = "suspended" if self.profile.status == "active" else "active"
        self._update_status_button_color()
        # Update the label color when status changes
        self._update_label_color()
        if self.on_status_toggle_callback:
            self.on_status_toggle_callback(self.profile)

    def _update_label_color(self):
        """Sets the profile label color based on its current status."""
        if self.profile.status == "active":
            self.label.configure(text_color=self.label_color_active)
        else:
            self.label.configure(text_color=self.label_color_suspended)

    def _update_status_button_color(self):
        """Changes the button color based on the profile's status."""
        if self.profile.status == "active":
            self.status_button.configure(fg_color="green", hover_color="#006400")
        else:
            self.status_button.configure(fg_color="#E53935", hover_color="#C62828") # Light red and darker red

    def update_points(self, points_text: str):
        """Updates the text of the points label."""
        self.points_label.configure(text=points_text)

    def _on_select(self):
        """Callback for when the checkbox is clicked."""
        is_selected = self.check_var.get() == "on"
        if self.on_select_callback:
            self.on_select_callback(self.profile, is_selected)

    def set_checked(self, is_checked: bool):
        """Programmatically sets the checkbox state."""
        self.check_var.set("on" if is_checked else "off")

    def _on_label_click(self, event):
        """Callback for when the main profile label is clicked."""
        if self.on_label_click_callback:
            self.on_label_click_callback(self.profile)
