# BingRewardSearch/edge_profile.py

class EdgeProfile:
    """
    A data class representing a single Microsoft Edge profile.
    """
    def __init__(self, index: int, name: str, email: str, cmd_arg: str, status: str = "active"):
        """
        Initializes an EdgeProfile object.

        Args:
            index (int): The serial number of the profile (1-based).
            name (str): The display name of the profile (e.g., "Personal 1").
            email (str): The email associated with the profile.
            cmd_arg (str): The command-line argument to launch this specific profile.
            status (str): The status of the profile ('active' or 'suspended').
        """
        self.index = index
        self.name = name
        self.email = email
        self.cmd_arg = cmd_arg
        self.status = status

    def __repr__(self) -> str:
        """
        Provides the "official" string representation of the object.
        """
        return f"EdgeProfile(index={self.index}, name='{self.name}', email='{self.email}', status='{self.status}')"

    @property
    def full_name(self) -> str:
        """
        Returns the combined name and email string for display purposes.
        """
        return f"{self.email} ({self.name})"

    def to_dict(self):
        """Converts the profile object to a dictionary for JSON serialization."""
        return {
            "cmd": self.cmd_arg,
            "status": self.status
        }

    def __eq__(self, other):
        """
        Defines equality based on the command-line argument, which is a unique identifier.
        """
        if not isinstance(other, EdgeProfile):
            return NotImplemented
        return self.cmd_arg == other.cmd_arg

    def __hash__(self):
        """
        Makes the object hashable based on the unique command-line argument.
        """
        return hash(self.cmd_arg)
