#!/usr/bin/env python3
"""
Command Line Interface for DSEI Company Scraper
"""

import sys
import argparse
from pathlib import Path

from .scraper import DSEICompanyScraper
from .config import Config


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='DSEI Company Scraper - Collect company data from DSEI.co.uk',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Scrape all pages
  %(prog)s --max-pages 5            # Scrape first 5 pages only
  %(prog)s --start-page 3           # Start from page 3
  %(prog)s --output companies.csv   # Custom output file
  %(prog)s --config custom.json     # Use custom config
        """
    )
    
    parser.add_argument('--start-page', type=int, default=1, 
                       help='Starting page number (default: 1)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to scrape (default: all)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to configuration file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output CSV file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    scraper = None  # Initialize to avoid unbound variable issues
    
    try:
        # Initialize configuration
        if args.config:
            config = Config(args.config)
        else:
            config = Config()
        
        # Initialize scraper
        scraper = DSEICompanyScraper(config)
        
        print("🚀 Starting DSEI Company Scraper...")
        print(f"📄 Config: {config.config_path}")
        print(f"📊 Pages: {args.start_page} to {'all' if args.max_pages is None else args.start_page + args.max_pages - 1}")
        
        # Run scraper
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
        
        # Save partial results if any
        if scraper and scraper.companies_data:
            print(f"💾 Saving {len(scraper.companies_data)} companies collected so far...")
            if args.output:
                scraper.save_to_csv(args.output)
            else:
                scraper.save_to_csv()
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
