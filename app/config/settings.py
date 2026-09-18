"""
Configuration settings for the investigation system.
"""
import os
from typing import Optional


class Settings:
    """Application settings."""
    
    # Maximum number of investigation iterations
    MAX_ITERATIONS: int = 5
    
    # Minimum evidence items required for sufficiency
    MIN_EVIDENCE_ITEMS: int = 2
    
    # Logging level
    LOG_LEVEL: str = "INFO"
    
    # Mock data settings
    USE_MOCK_DATA: bool = True
    
    # Search settings
    MAX_SEARCH_RESULTS: int = 10
    SEARCH_TIMEOUT: int = 30


settings = Settings()