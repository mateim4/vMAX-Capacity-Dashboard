"""
Configuration management for VMAX/PowerMax Capacity Dashboard.

This module handles loading and validating connection parameters
for the Unisphere for PowerMax REST API.
"""

import json
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class UnisphereConfig:
    """Configuration for Unisphere connection."""
    
    host: str
    port: int
    username: str
    password: str
    array_id: str
    verify_ssl: bool = False
    
    def validate(self) -> None:
        """Validate required configuration parameters."""
        if not self.host:
            raise ValueError("Unisphere host is required")
        if not self.username:
            raise ValueError("Username is required")
        if not self.password:
            raise ValueError("Password is required")
        if not self.array_id:
            raise ValueError("Array ID is required")
        if not isinstance(self.port, int) or self.port <= 0:
            raise ValueError("Port must be a positive integer")


def load_config(config_path: str = "config.json") -> UnisphereConfig:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        UnisphereConfig object with validated parameters
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create {config_path} based on config.example.json"
        )
    
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    config = UnisphereConfig(
        host=config_data.get('unisphere_host', ''),
        port=config_data.get('unisphere_port', 8443),
        username=config_data.get('username', ''),
        password=config_data.get('password', ''),
        array_id=config_data.get('array_id', ''),
        verify_ssl=config_data.get('verify_ssl', False)
    )
    
    config.validate()
    return config


def load_config_from_env() -> UnisphereConfig:
    """
    Load configuration from environment variables.
    
    Expected environment variables:
    - UNISPHERE_HOST
    - UNISPHERE_PORT (default: 8443)
    - UNISPHERE_USER
    - UNISPHERE_PASSWORD
    - VMAX_ARRAY_ID
    - UNISPHERE_VERIFY_SSL (default: false)
    
    Returns:
        UnisphereConfig object with validated parameters
        
    Raises:
        ValueError: If required environment variables are missing
    """
    config = UnisphereConfig(
        host=os.environ.get('UNISPHERE_HOST', ''),
        port=int(os.environ.get('UNISPHERE_PORT', '8443')),
        username=os.environ.get('UNISPHERE_USER', ''),
        password=os.environ.get('UNISPHERE_PASSWORD', ''),
        array_id=os.environ.get('VMAX_ARRAY_ID', ''),
        verify_ssl=os.environ.get('UNISPHERE_VERIFY_SSL', 'false').lower() == 'true'
    )
    
    config.validate()
    return config
