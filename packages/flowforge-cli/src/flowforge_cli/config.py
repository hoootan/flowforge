"""Configuration file support for FlowForge CLI.

Loads configuration from:
1. .flowforge.yml or .flowforge.yaml in current directory
2. .flowforge.yml or .flowforge.yaml in parent directories (up to home)
3. ~/.flowforge.yml or ~/.flowforge.yaml in home directory

Environment variables override file configuration.
Command-line arguments override everything.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Check if pyyaml is available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


CONFIG_FILENAMES = [".flowforge.yml", ".flowforge.yaml", "flowforge.yml", "flowforge.yaml"]


@dataclass
class DevConfig:
    """Development server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    app_id: str = "dev-app"
    watch: bool = False
    directory: str = "."


@dataclass
class ServerConfig:
    """Server connection configuration."""

    url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: int = 30


@dataclass
class CLIConfig:
    """Complete CLI configuration."""

    # Server connection
    server: ServerConfig = field(default_factory=ServerConfig)
    # Development server
    dev: DevConfig = field(default_factory=DevConfig)
    # Default output format
    output_format: str = "table"  # table, json, yaml
    # Enable colors
    color: bool = True
    # Verbose output
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CLIConfig":
        """Create config from dictionary."""
        config = cls()

        # Server config
        if "server" in data:
            server_data = data["server"]
            config.server = ServerConfig(
                url=server_data.get("url", config.server.url),
                api_key=server_data.get("api_key", config.server.api_key),
                timeout=server_data.get("timeout", config.server.timeout),
            )

        # Dev config
        if "dev" in data:
            dev_data = data["dev"]
            config.dev = DevConfig(
                host=dev_data.get("host", config.dev.host),
                port=dev_data.get("port", config.dev.port),
                app_id=dev_data.get("app_id", config.dev.app_id),
                watch=dev_data.get("watch", config.dev.watch),
                directory=dev_data.get("directory", config.dev.directory),
            )

        # Top-level options
        config.output_format = data.get("output_format", config.output_format)
        config.color = data.get("color", config.color)
        config.verbose = data.get("verbose", config.verbose)

        return config

    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Server
        if url := os.environ.get("FLOWFORGE_SERVER_URL"):
            self.server.url = url
        if api_key := os.environ.get("FLOWFORGE_API_KEY"):
            self.server.api_key = api_key
        if timeout := os.environ.get("FLOWFORGE_TIMEOUT"):
            self.server.timeout = int(timeout)

        # Dev
        if host := os.environ.get("FLOWFORGE_DEV_HOST"):
            self.dev.host = host
        if port := os.environ.get("FLOWFORGE_DEV_PORT"):
            self.dev.port = int(port)
        if app_id := os.environ.get("FLOWFORGE_APP_ID"):
            self.dev.app_id = app_id

        # Options
        if output_format := os.environ.get("FLOWFORGE_OUTPUT_FORMAT"):
            self.output_format = output_format
        if no_color := os.environ.get("NO_COLOR"):
            self.color = False


def find_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find configuration file by walking up directory tree.

    Args:
        start_dir: Directory to start search from (default: current directory)

    Returns:
        Path to config file if found, None otherwise
    """
    current = start_dir or Path.cwd()
    home = Path.home()

    # Walk up from current directory
    while current != current.parent:
        for filename in CONFIG_FILENAMES:
            config_path = current / filename
            if config_path.is_file():
                return config_path

        # Stop at home directory
        if current == home:
            break

        current = current.parent

    # Check home directory explicitly
    for filename in CONFIG_FILENAMES:
        config_path = home / filename
        if config_path.is_file():
            return config_path

    return None


def load_config_file(path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        path: Path to the configuration file

    Returns:
        Parsed configuration dictionary
    """
    if not YAML_AVAILABLE:
        raise ImportError(
            "pyyaml is required to load configuration files. "
            "Install with: pip install pyyaml"
        )

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return data or {}


def load_config(start_dir: Optional[Path] = None) -> CLIConfig:
    """Load configuration from file and environment.

    Configuration is loaded in order of precedence (lowest to highest):
    1. Default values
    2. Config file (if found)
    3. Environment variables

    Args:
        start_dir: Directory to start config file search from

    Returns:
        Loaded configuration
    """
    config = CLIConfig()

    # Try to load config file
    config_path = find_config_file(start_dir)
    if config_path and YAML_AVAILABLE:
        try:
            data = load_config_file(config_path)
            config = CLIConfig.from_dict(data)
        except Exception:
            # Silently ignore config file errors for now
            pass

    # Apply environment variable overrides
    config.apply_env_overrides()

    return config


# Global config cache
_config: Optional[CLIConfig] = None


def get_config() -> CLIConfig:
    """Get the global CLI configuration (cached)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset the cached configuration."""
    global _config
    _config = None
