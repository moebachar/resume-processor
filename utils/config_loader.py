"""
Configuration Loader

This module provides utilities to load and access the centralized config.json file.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """Singleton class to load and cache the project configuration."""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the config loader."""
        if self._config is None:
            try:
                self._load_config()
            except FileNotFoundError:
                # In microservice mode, config is passed via API, not from file
                self._config = {}

    def _load_config(self):
        """Load the config.json file from the project root."""
        # Find project root (where config.json is located)
        current_dir = Path(__file__).parent.parent
        config_path = current_dir / "config.json"

        if not config_path.exists():
            # Don't raise error - allow microservice to work without file
            self._config = {}
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config.json: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading config.json: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            path: Dot-separated path to the config value (e.g., "extraction.html.output_format")
            default: Default value to return if path is not found

        Returns:
            The configuration value or default if not found

        Examples:
            >>> config = ConfigLoader()
            >>> config.get("extraction.html.output_format")
            'txt'
            >>> config.get("extraction.html.trafilatura.include_tables")
            True
        """
        if self._config is None:
            self._load_config()

        keys = path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.

        Args:
            section: Section name (e.g., "extraction", "openai")

        Returns:
            Dictionary containing the section configuration

        Examples:
            >>> config = ConfigLoader()
            >>> config.get_section("extraction")
            {'html': {...}, 'yaml': {...}}
        """
        return self.get(section, {})

    def reload(self):
        """Reload the configuration from disk."""
        self._config = None
        self._load_config()


# Singleton instance (lazy initialization)
_config_loader = None


def _get_loader():
    """Get or create the singleton config loader."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_config(path: str, default: Any = None) -> Any:
    """
    Convenience function to get a configuration value.

    Args:
        path: Dot-separated path to the config value
        default: Default value to return if path is not found

    Returns:
        The configuration value or default if not found
    """
    return _get_loader().get(path, default)


def get_config_section(section: str) -> Dict[str, Any]:
    """
    Convenience function to get a configuration section.

    Args:
        section: Section name

    Returns:
        Dictionary containing the section configuration
    """
    return _get_loader().get_section(section)


def reload_config():
    """Reload the configuration from disk."""
    _get_loader().reload()
