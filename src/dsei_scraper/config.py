"""
Configuration module for DSEI Company Scraper
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration handler for the DSEI scraper"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config file. If None, uses default config.
        """
        if config_path is None:
            # Get project root directory
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config" / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_default_config()
        except Exception:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "base_url": "https://www.dsei.co.uk",
            "list_url_template": "https://www.dsei.co.uk/visit/exhibiting-companies?&page={page}&searchgroup=65207D8C-exhibitors-list",
            "company_detail_url_template": "https://www.dsei.co.uk/exhibitors-list/{company_slug}?=&page={page}&searchgroup=libraryentry-exhibitors-list",
            "delays": {
                "between_companies": 0.2,
                "between_pages": 1
            },
            "timeouts": {
                "request_timeout": 30
            },
            "output": {
                "csv_filename": "dsei_companies.csv",
                "log_filename": "scraper.log"
            },
            "selectors": {
                "company_links": "a.js-librarylink-entry",
                "company_title": "h1.m-exhibitor-entry__item__header__title",
                "categories": "li.m-exhibitor-entry__item__header__categories__item",
                "description": "div.m-exhibitor-entry__item__body__description"
            },
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0"
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_base_url(self) -> str:
        """Get base URL"""
        return self.get('base_url')
    
    def get_list_url_template(self) -> str:
        """Get list URL template"""
        return self.get('list_url_template')
    
    def get_company_detail_url_template(self) -> str:
        """Get company detail URL template"""
        return self.get('company_detail_url_template')
    
    def get_delays(self) -> Dict[str, int]:
        """Get delay settings"""
        return self.get('delays', {})
    
    def get_timeouts(self) -> Dict[str, int]:
        """Get timeout settings"""
        return self.get('timeouts', {})
    
    def get_output_config(self) -> Dict[str, str]:
        """Get output configuration"""
        return self.get('output', {})
    
    def get_selectors(self) -> Dict[str, str]:
        """Get CSS selectors"""
        return self.get('selectors', {})
    
    def get_user_agent(self) -> str:
        """Get user agent string"""
        return self.get('user_agent')
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self._config.copy()
