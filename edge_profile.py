# BingRewardSearch/edge_profile.py

from dataclasses import dataclass, field

@dataclass(unsafe_hash=True) # Keep unsafe_hash=True
class EdgeProfile:
    """Holds information about a single Edge profile."""
    index: int
    name: str
    email: str
    cmd_arg: str
    # status: str = "active" # <-- REMOVED

    # --- NEW: Field to store points numerically ---
    available_points: int = 0 # Default to 0

    @property
    def full_name(self) -> str:
        return f"{self.email} ({self.name})"

    def to_dict(self) -> dict:
        """Converts the profile data to a dictionary for saving."""
        return {
            "cmd": self.cmd_arg,
            # "status": self.status, # <-- REMOVED
            "available_points": self.available_points # <-- ADDED
            # We'll keep saving points here for persistence
        }