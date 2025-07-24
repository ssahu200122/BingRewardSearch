# BingRewardSearch/ui_components.py

import customtkinter

class ProfileRow(customtkinter.CTkFrame):
    """
    A custom widget representing a single profile row in the UI.
    """
    def __init__(self, master, profile, checkbox_callback, label_click_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.checkbox_callback = checkbox_callback
        self.label_click_callback = label_click_callback

        self.check_var = customtkinter.StringVar(value="on")
        self.checkbox = customtkinter.CTkCheckBox(
            self,
            text="",
            command=self._on_checkbox_toggle,
            variable=self.check_var,
            onvalue="on",
            offvalue="off",
            width=10
        )
        self.checkbox.grid(row=0, column=0, padx=(5, 10), pady=5)

        self.label = customtkinter.CTkLabel(
            self,
            text=self.profile.full_name,
            font=customtkinter.CTkFont(size=14, underline=True),
            text_color="cyan",
            anchor="w",
            cursor="hand2"
        )
        self.label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.columnconfigure(1, weight=1)

        # Bind events for hover and click
        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        self.label.bind("<Button-1>", self._on_click)

    def _on_enter(self, event):
        self.label.configure(text_color="yellow")

    def _on_leave(self, event):
        self.label.configure(text_color="cyan")

    def _on_click(self, event):
        self.label_click_callback(self.profile)

    def _on_checkbox_toggle(self):
        is_selected = self.check_var.get() == "on"
        self.checkbox_callback(self.profile, is_selected)

    def set_checked(self, is_checked: bool):
        if is_checked:
            self.check_var.set("on")
        else:
            self.check_var.set("off")


class LabeledSlider(customtkinter.CTkFrame):
    """
    A custom widget combining a label, a slider, and a value display.
    """
    def __init__(self, master, text: str, from_: int, to: int, step: int, initial_value: int, command=None):
        super().__init__(master)
        self.command = command
        self.variable = customtkinter.IntVar(value=initial_value)

        self.label = customtkinter.CTkLabel(self, text=text, font=("Cascadia Code", 15))
        self.label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.slider = customtkinter.CTkSlider(
            self,
            from_=from_,
            to=to,
            variable=self.variable,
            command=self._slider_event,
            number_of_steps=(to - from_) // step if step != 0 else to - from_
        )
        self.slider.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.value_label = customtkinter.CTkLabel(self, text=str(initial_value), font=("Cascadia Code", 15), width=30)
        self.value_label.grid(row=1, column=1, sticky="w", padx=(5, 10), pady=(0, 10))

        self.columnconfigure(0, weight=1)

    def _slider_event(self, value):
        self.value_label.configure(text=str(int(value)))
        if self.command:
            self.command(int(value))

    def get(self) -> int:
        return self.variable.get()
