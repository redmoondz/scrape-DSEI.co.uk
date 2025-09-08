#!/usr/bin/env python3
"""
DSEI Company Scraper - Project Summary and Usage Guide

This project implements a web scraper for collecting company data from DSEI.co.uk
following the exact flowchart logic provided by the user.
"""

def print_project_summary():
    """Print a summary of the project"""
    
    summary = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         DSEI COMPANY SCRAPER                                ║
║                    Web Scraper for DSEI.co.uk Companies                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 PROJECT OVERVIEW:
   This scraper collects company information from DSEI (Defence and Security 
   Equipment International) website, following the exact flowchart logic:
   
   1. Get first page of resource
   2. Check for company blocks (li tags with specific class)
   3. Extract company slugs from each block
   4. Make HTTP requests to API for additional company info
   5. Save data and move to next page
   6. Repeat until no more pages

📁 PROJECT FILES:
   ├── dsei_scraper.py      - Main scraper implementation
   ├── verify_scraper.py    - Connection and functionality verification
   ├── test_scraper.py      - Quick test with limited pages
   ├── setup_and_run.py     - Interactive setup and run script
   ├── requirements.txt     - Python dependencies
   ├── config.json          - Configuration settings
   ├── README.md            - Detailed documentation
   └── scraper.log          - Logging output (created when run)

📊 OUTPUT FORMAT:
   CSV file with columns: company_name, tags, overview, website
   
   Example:
   "Wind River","Digital Twins; Software","Global leader in...","https://windriver.com"

🔧 TECHNICAL FEATURES:
   ✅ Follows exact flowchart logic
   ✅ Respectful rate limiting (1-2 second delays)
   ✅ Retry logic with exponential backoff
   ✅ Comprehensive error handling
   ✅ Detailed logging
   ✅ Session management with proper headers
   ✅ BeautifulSoup HTML parsing
   ✅ CSV output formatting

🌐 URL PATTERNS:
   List Page: https://www.dsei.co.uk/visit/exhibiting-companies?&page={page}&searchgroup=65207D8C-exhibitors-list
   Detail:    https://www.dsei.co.uk/exhibitors-list/{slug}?=&page={page}&searchgroup=libraryentry-exhibitors-list

🚀 QUICK START:
   1. Run: python3 setup_and_run.py
   2. Choose option 4 for full setup + scraping
   3. Wait for completion
   4. Check dsei_companies.csv for results

⚙️  MANUAL USAGE:
   # Install dependencies
   pip install -r requirements.txt
   
   # Verify functionality
   python3 verify_scraper.py
   
   # Quick test (1 page)
   python3 test_scraper.py
   
   # Full scraper
   python3 dsei_scraper.py

📈 PERFORMANCE:
   - Processes ~20-50 companies per page
   - Includes respectful delays between requests
   - Full scrape may take 30-60 minutes depending on data size
   - Creates detailed logs for monitoring progress

🛡️  ERROR HANDLING:
   - Network timeouts and retries
   - HTTP error responses
   - Missing HTML elements
   - Malformed data gracefully handled
   - Comprehensive logging for debugging

💡 CUSTOMIZATION:
   - Modify delays in scraper configuration
   - Adjust CSS selectors for different HTML structures
   - Add additional data fields to extract
   - Change output format (JSON, XML, etc.)

📝 LOGS:
   Check scraper.log for detailed execution information including:
   - Pages processed
   - Companies found
   - Errors encountered
   - Performance metrics

🎯 COMPLIANCE:
   - Respectful scraping with delays
   - Proper User-Agent headers
   - Error handling to avoid overwhelming server
   - Following robots.txt principles
   
═══════════════════════════════════════════════════════════════════════════════
For detailed documentation, see README.md
For issues or questions, check the log files
═══════════════════════════════════════════════════════════════════════════════
"""
    
    print(summary)

def show_quick_commands():
    """Show quick command reference"""
    
    commands = """
🔧 QUICK COMMAND REFERENCE:

# Full interactive setup and run
python3 setup_and_run.py

# Manual step-by-step
pip3 install -r requirements.txt    # Install dependencies
python3 verify_scraper.py           # Test connection
python3 test_scraper.py             # Quick test
python3 dsei_scraper.py             # Full scraper

# Check results
cat dsei_companies.csv | head -5    # View first 5 companies
wc -l dsei_companies.csv            # Count total companies
tail -f scraper.log                 # Monitor progress

# Customize scraping
# Edit dsei_scraper.py line 305 to limit pages:
# scraper.scrape_all_companies(start_page=1, max_pages=5)
"""
    
    print(commands)

if __name__ == "__main__":
    print_project_summary()
    
    choice = input("Show quick commands? (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        show_quick_commands()
