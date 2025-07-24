# BingRewardSearch/logger.py
import datetime
import re
import config

class Logger:
    """A simple logger class to write timestamped messages to a file."""

    def __init__(self, log_file=config.LOG_FILE_PATH):
        self.log_file = log_file
        # Regex to find and remove ANSI escape sequences (color codes)
        self.ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._write_log_header()

    def _write_log_header(self):
        """Writes a header to the log file each time the application starts."""
        header = f"\n--- Log Session Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(header)
        except Exception as e:
            print(f"CRITICAL: Could not write to log file '{self.log_file}'. Error: {e}")

    def log(self, message: str, level: str = "INFO"):
        """
        Writes a formatted message to the log file, stripping any color codes.
        
        Args:
            message (str): The message to log.
            level (str): The log level (e.g., INFO, WARN, ERROR).
        """
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        
        sanitized_message = self.ansi_escape_pattern.sub('', message).strip()
        if not sanitized_message:
            return

        log_entry = f"[{timestamp}] [{level.upper()}] {sanitized_message}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"CRITICAL: Could not write to log file. Error: {e}")

    def clear_log(self):
        """Clears the log file by truncating it and writing a new header."""
        try:
            # Open in write mode to clear the file
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate()
            self._write_log_header()
            self.log("Log file cleared by user.", level="SYSTEM")
        except Exception as e:
            print(f"CRITICAL: Could not clear log file '{self.log_file}'. Error: {e}")


# Singleton instance for easy importing and use across the application
logger = Logger()
