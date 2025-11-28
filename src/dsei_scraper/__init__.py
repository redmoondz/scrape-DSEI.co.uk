# DSEI Company Scraper Package
__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main classes after ensuring modules exist
try:
    from .scraper import DSEICompanyScraper
    from .async_scraper import AsyncDSEICompanyScraper, run_async_scraper
    from .config import Config
    __all__ = ['DSEICompanyScraper', 'AsyncDSEICompanyScraper', 'run_async_scraper', 'Config']
except ImportError:
    # Fallback for development
    __all__ = []
