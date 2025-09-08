#!/usr/bin/env python3
"""
Main entry point for DSEI Company Scraper
"""

import sys
import argparse
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dsei_scraper import DSEICompanyScraper, Config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DSEI Company Scraper')
    parser.add_argument('--start-page', type=int, default=1, 
                       help='Starting page number (default: 1)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to scrape (default: all)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to configuration file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output CSV file path')
    
    args = parser.parse_args()
    
    # Initialize configuration
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Initialize scraper
    scraper = DSEICompanyScraper(config)
    
    # Run scraper
    try:
        scraper.scrape_all_companies(
            start_page=args.start_page,
            max_pages=args.max_pages
        )
        
        # Save with custom output file if specified
        if args.output:
            scraper.save_to_csv(args.output)
        
        print(f"\n✅ Scraping completed successfully!")
        print(f"📊 Total companies collected: {len(scraper.companies_data)}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
        
        # Save partial results
        if scraper.companies_data:
            print(f"💾 Saving {len(scraper.companies_data)} companies collected so far...")
            if args.output:
                scraper.save_to_csv(args.output)
            else:
                scraper.save_to_csv()
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
