"""
Base class for all agents in the SimEcon simulation.

Provides common functionality like logging that can be shared across different agent types.
"""

from logging_config import get_logger
from dataclasses import asdict

logger = get_logger(__name__)


class BaseAgent:
    """Base class for all simulation agents with common logging functionality."""

    def __init__(self, name_prefix: str = "Agent"):
        self.tick: int = 0
        self.name = f"{name_prefix}-{id(self)}"

    def set_tick(self, tick: int):
        """Set the current tick value from the simulation."""
        self.tick = tick

    def _log(self, message: str, *args, level: str = "debug") -> None:
        """Helper method to log with agent name, tick, and method name."""
        import inspect

        method_name = inspect.stack()[1].function
        full_message = f"Tick:{self.tick} - {self.name} - {method_name} - {message}"
        getattr(logger, level)(full_message, *args)


class BaseStats:
    def __init__(self):
        self.tick: int = 0

    def set_tick(self, tick: int):
        self.tick = tick

    def record(self, tick: int, **kwargs):
        for key, val in kwargs.items():
            getattr(self, key)[tick] = val

    def get_latest(self):
        latest_stats = {}
        for stat_name, stat_dict in asdict(self).items():
            if not stat_dict:
                latest_stats[stat_name] = None
                continue
            max_tick = max(stat_dict.keys())
            latest_stats[stat_name] = stat_dict[max_tick]
        return latest_stats

    def generate_chart(self, columns: list[str], filename: str):
        pass
