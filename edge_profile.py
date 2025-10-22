# BingRewardSearch/edge_profile.py

from dataclasses import dataclass, field

@dataclass(unsafe_hash=True)  # <-- THIS FIX IS NEEDED
class EdgeProfile:
    """Holds information about a single Edge profile."""
    index: int
    name: str
    email: str
    cmd_arg: str
    status: str = "active"
    
    # Use a property to get the full display name
    @property
    def full_name(self) -> str:
        return f"{self.email} ({self.name})"

    def to_dict(self) -> dict:
        """Converts the profile data to a dictionary for saving."""
        return {
            "cmd": self.cmd_arg,
            "status": self.status
        }