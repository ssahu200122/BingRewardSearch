# BingRewardSearch/ui_components.py

import customtkinter
from edge_profile import EdgeProfile

class ProfileRow(customtkinter.CTkFrame):
    """
    A custom widget representing a single profile row in the UI.
    Includes a status button, checkbox, a label for the profile name, and a points display.
    """
    def __init__(self, master, profile: EdgeProfile, on_select_callback, on_label_click_callback, on_status_toggle_callback):
        super().__init__(master, fg_color="transparent")
        self.profile = profile
        self.on_select_callback = on_select_callback
        self.on_label_click_callback = on_label_click_callback
        self.on_status_toggle_callback = on_status_toggle_callback

        self.grid_columnconfigure(2, weight=1)

        # --- Status Toggle Button ---
        self.status_button = customtkinter.CTkButton(
            self,
            text="●",
            width=28,
            command=self._toggle_status
        )
        self.status_button.grid(row=0, column=0, padx=(0, 5))

        self.check_var = customtkinter.StringVar(value="on")
        self.checkbox = customtkinter.CTkCheckBox(self, text="", variable=self.check_var, onvalue="on", offvalue="off", command=self._on_check, width=20)
        self.checkbox.grid(row=0, column=1, padx=5)

        # --- Define Fonts and Colors for styling ---
        self.label_font = customtkinter.CTkFont(weight="bold", slant="italic", underline=True, size=14)
        self.points_font = customtkinter.CTkFont(weight="bold", size=14)
        
        self.default_color = "#3498db"  # A distinct blue color
        self.hover_color = "#f1c40f"   # A bright yellow for hover
        self.suspended_color = "gray60"

        self.label = customtkinter.CTkLabel(self, text=profile.full_name, anchor="w", cursor="hand2", font=self.label_font, text_color=self.default_color)
        self.label.grid(row=0, column=2, sticky="ew", padx=5)
        
        self.points_label = customtkinter.CTkLabel(self, text="0/0 pts", anchor="e", width=80, font=self.points_font)
        self.points_label.grid(row=0, column=3, sticky="e", padx=5)

        # Bind events for hover effect and click
        self.label.bind("<Button-1>", lambda e: self.on_label_click_callback(self.profile))
        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        
        self.update_status_visual()

    def _on_enter(self, event):
        """Changes the label color on mouse hover."""
        self.label.configure(text_color=self.hover_color)

    def _on_leave(self, event):
        """Resets the label color based on the profile's status."""
        if self.profile.status == 'active':
            self.label.configure(text_color=self.default_color)
        else:
            self.label.configure(text_color=self.suspended_color)

    def _on_check(self):
        is_selected = self.check_var.get() == "on"
        self.on_select_callback(self.profile, is_selected)

    def set_checked(self, is_checked: bool):
        self.check_var.set("on" if is_checked else "off")

    def update_points(self, points_text: str):
        self.points_label.configure(text=points_text)

    def _toggle_status(self):
        """Toggles the profile's status between 'active' and 'suspended'."""
        self.profile.status = "suspended" if self.profile.status == "active" else "active"
        self.update_status_visual()
        if self.on_status_toggle_callback:
            self.on_status_toggle_callback(self.profile)

    def update_status_visual(self):
        """Updates the entire row's visual appearance based on the profile's status."""
        if self.profile.status == "active":
            self.status_button.configure(fg_color="#2ECC71", text_color="white") # Green
            self.label.configure(text_color=self.default_color, font=self.label_font)
            self.points_label.configure(text_color=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])
            self.checkbox.configure(state="normal")
        else:
            self.status_button.configure(fg_color="#95a5a6", text_color="black") # Gray
            self.label.configure(text_color=self.suspended_color, font=customtkinter.CTkFont(slant="roman", underline=False)) # Revert font style
            self.points_label.configure(text_color=self.suspended_color)
            self.checkbox.configure(state="disabled")

class LabeledSlider(customtkinter.CTkFrame):
    """A custom widget combining a label and a slider."""
    def __init__(self, master, text: str, from_: int, to: int, step: int, initial_value: int, command=None):
        super().__init__(master)
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.label = customtkinter.CTkLabel(self, text=f"{text} {initial_value}")
        self.label.grid(row=0, column=0, sticky="w", padx=5)

        self.slider = customtkinter.CTkSlider(self, from_=from_, to=to, number_of_steps=(to - from_) // step, command=self._slider_event_wrapper)
        self.slider.set(initial_value)
        self.slider.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)
        
        self.text = text
        self.command = command

    def _slider_event_wrapper(self, value):
        int_value = int(value)
        self.label.configure(text=f"{self.text} {int_value}")
        if self.command:
            self.command(int_value)
            
    def get(self) -> int:
        return int(self.slider.get())
