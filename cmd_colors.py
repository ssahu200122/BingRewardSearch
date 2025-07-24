# BingRewardSearch/cmd_colors.py

class Colors:
    """A utility class for adding ANSI color codes to console output."""
    # Reset all attributes
    RESET = "\033[0m"

    # Text Styles
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    WHITE = "\033[37m"

    # Bright Foreground Colors
    BRIGHT_YELLOW = "\033[93m"

    # Background Colors
    BG_BLUE = "\033[44m"
    BG_BRIGHT_YELLOW = "\033[103m"

    # 256-Color Support
    @staticmethod
    def color_256_fg(code):
        return f"\033[38;5;{code}m"

    @staticmethod
    def color_256_bg(code):
        return f"\033[48;5;{code}m"

# Instantiate for easy import
colors = Colors()
