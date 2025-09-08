# DSEI Company Scraper

A professional web scraper for collecting company data from DSEI.co.uk (Defence and Security Equipment International) website.

## 🏗️ Project Structure

```
dsei-company-scraper/
├── src/
│   └── dsei_scraper/           # Main package
│       ├── __init__.py         # Package initialization
│       ├── scraper.py          # Core scraper logic
│       ├── config.py           # Configuration management
│       └── cli.py              # Command line interface
├── tests/                      # Test files
│   ├── __init__.py
│   ├── test_scraper.py         # Scraper tests
│   └── verify_scraper.py       # Connection verification
├── scripts/                    # Utility scripts
│   ├── setup_and_run.py        # Interactive setup
│   └── project_info.py         # Project information
├── docs/                       # Documentation
│   └── README.md               # This file
├── config/                     # Configuration files
│   └── config.json             # Main configuration
├── requirements/               # Dependencies
│   ├── base.txt                # Base requirements
│   ├── dev.txt                 # Development requirements
│   └── prod.txt                # Production requirements
├── data/                       # Data directories
│   ├── raw/                    # Raw scraped data
│   └── processed/              # Processed data
├── logs/                       # Log files
├── main.py                     # Main entry point
├── setup.py                    # Package setup
├── Makefile                    # Common tasks
├── requirements.txt            # Main requirements
└── .gitignore                  # Git ignore rules
```

## Usage

### Basic Usage
```bash
python dsei_scraper.py
```

### For Testing (Limited Pages)
Edit the `main()` function in `dsei_scraper.py` and uncomment the line:
```python
scraper.scrape_all_companies(start_page=1, max_pages=2)  # For testing
```

## Output

The scraper generates:
- `dsei_companies.csv` - Main output file with company data
- `scraper.log` - Detailed logging information

### CSV Format
```
company_name,tags,overview,website
"Wind River","Digital Twins; Mission Computing; Software","Wind River is a global leader...","https://windriver.com"
```

## URL Structure

### List URL Template:
```
https://www.dsei.co.uk/visit/exhibiting-companies?&page={page}&searchgroup=65207D8C-exhibitors-list
```

### Company Detail URL Template:
```
https://www.dsei.co.uk/exhibitors-list/{company_slug}?=&page={page}&searchgroup=libraryentry-exhibitors-list
```

## How It Works

1. **Page Iteration**: Starts from page 1 and iterates through all available pages
2. **Company Discovery**: Finds all `<a>` tags with class `js-librarylink-entry`
3. **Slug Extraction**: Extracts company slugs from JavaScript URLs using regex
4. **Detail Fetching**: Makes XHR requests to get detailed company information
5. **Data Extraction**: Parses HTML to extract:
   - Company name from `<h1>` tag
   - Tags from category list items
   - Overview from description div
   - Website URL from external links
6. **CSV Export**: Saves all collected data to CSV file

## Rate Limiting

The scraper includes respectful delays:
- 1 second between company detail requests
- 2 seconds between page requests

## Logging

Detailed logging is available in:
- Console output (INFO level)
- `scraper.log` file (DEBUG level)

## Error Handling

- Network timeouts (30 seconds)
- HTTP error responses
- Missing HTML elements
- Malformed data

## Customization

You can modify the scraper by:
- Changing the delay timings in `scrape_all_companies()`
- Adjusting the CSS selectors for different HTML structures
- Adding more data fields to extract
- Modifying the output format

## Technical Details

### Headers Used
The scraper mimics a Firefox browser with these headers:
- User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0)
- X-Requested-With: XMLHttpRequest
- Proper Accept and encoding headers

### Session Management
Uses `requests.Session()` for:
- Cookie persistence
- Connection pooling
- Header management
