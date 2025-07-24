# BingRewardSearch/edge_profile.py

class EdgeProfile:
    """
    A data class representing a single Microsoft Edge profile.

    This class holds all the necessary information for one user profile,
    making the data easier to manage than using raw dictionaries.
    """

    def __init__(self, name: str, email: str, cmd_arg: str):
        """
        Initializes an EdgeProfile object.

        Args:
            name (str): The display name of the profile (e.g., "Personal 1").
            email (str): The email associated with the profile.
            cmd_arg (str): The command-line argument to launch this specific profile
                         (e.g., "--profile-directory=Default").
        """
        self.name = name
        self.email = email
        self.cmd_arg = cmd_arg

    def __repr__(self) -> str:
        """
        Provides the "official" string representation of the object.
        """
        return f"EdgeProfile(name='{self.name}', email='{self.email}')"

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
            # Add other fields here if you want to save them in the future
            # "PcPoints": 0,
            # "MobilePoints": 0
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
