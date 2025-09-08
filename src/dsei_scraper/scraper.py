#!/usr/bin/env python3
"""
DSEI.co.uk Company Data Scraper

This scraper follows the flowchart logic:
1. Gets the first page of the resource
2. Collects all company blocks (li tags with specific class)
3. Extracts company slugs from each block
4. Makes HTTP requests to the API for additional company info
5. Saves the data and moves to the next page

Output CSV format: company_name, tags, overview, website
"""

import requests
import csv
import re
import time
import logging
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, quote
from typing import List, Dict, Optional
import json
from pathlib import Path

from .config import Config


class DSEICompanyScraper:
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the DSEI Company Scraper
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or Config()
        
        # URLs from config
        self.base_url = self.config.get_base_url()
        self.list_url_template = self.config.get_list_url_template()
        self.company_detail_url_template = self.config.get_company_detail_url_template()
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.get_user_agent(),
            'Accept': '*/*',
            'Accept-Language': 'ru,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'X-Requested-With': 'XMLHttpRequest',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': self.base_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-GPC': '1',
            'Priority': 'u=0'
        })
        
        # Get project root for paths
        self.project_root = Path(__file__).parent.parent.parent
        
        # Set up logging
        self._setup_logging()
        
        # Data storage
        self.companies_data = []
        
        # Settings from config
        self.delays = self.config.get_delays()
        self.timeouts = self.config.get_timeouts()
        self.selectors = self.config.get_selectors()
        self.max_retries = 3
    
    def _setup_logging(self):
        """Set up logging configuration"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / self.config.get_output_config().get('log_filename', 'scraper.log')
        
        # Clear existing handlers to avoid duplication
        logging.getLogger().handlers.clear()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def make_request_with_retry(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic
        
        Args:
            url: URL to request
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed for {url}")
        
        return None
    
    def get_company_slugs_from_page(self, page_number: int) -> List[str]:
        """
        STEP 1: Get all company slugs from a listing page
        
        Args:
            page_number: The page number to scrape
            
        Returns:
            List of company slugs found on the page
        """
        url = self.list_url_template.format(page=page_number)
        self.logger.info(f"Fetching page {page_number}: {url}")
        
        try:
            response = self.make_request_with_retry(url, timeout=self.timeouts.get('request_timeout', 30))
            if not response:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all company blocks using selector from config
            company_slugs = []
            company_links = soup.find_all('a', class_='js-librarylink-entry')
            
            for link in company_links:
                if isinstance(link, Tag):
                    href = link.get('href', '') or ''
                    # Extract slug from href like "javascript:openRemoteModal('exhibitors-list/wind-river','ajax'..."
                    if isinstance(href, str):
                        match = re.search(r"'exhibitors-list/([^']+)'", href)
                        if match:
                            slug = match.group(1)
                            company_slugs.append(slug)
                            self.logger.debug(f"Found company slug: {slug}")
            
            self.logger.info(f"Found {len(company_slugs)} companies on page {page_number}")
            return company_slugs
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching page {page_number}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error processing page {page_number}: {e}")
            return []
    
    def get_company_details(self, company_slug: str, page_number: int) -> Optional[Dict[str, str]]:
        """
        STEP 2: Get detailed company information using the company slug
        
        Args:
            company_slug: The company's URL slug
            page_number: Current page number for the API call
            
        Returns:
            Dictionary with company details or None if failed
        """
        url = self.company_detail_url_template.format(
            company_slug=quote(company_slug), 
            page=page_number
        )
        
        self.logger.debug(f"Fetching company details: {url}")
        
        try:
            response = self.make_request_with_retry(url, timeout=self.timeouts.get('request_timeout', 30))
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract company name using selector from config
            company_name = ""
            title_selector = self.selectors.get('company_title', 'h1.m-exhibitor-entry__item__header__title')
            title_element = soup.select_one(title_selector)
            if title_element:
                company_name = title_element.get_text(strip=True)
            
            # Extract tags/categories using selector from config
            tags = []
            category_selector = self.selectors.get('categories', 'li.m-exhibitor-entry__item__header__categories__item')
            category_elements = soup.select(category_selector)
            for cat_elem in category_elements:
                tag = cat_elem.get_text(strip=True)
                if tag:
                    tags.append(tag)
            
            # Extract overview/description using selector from config
            overview = ""
            desc_selector = self.selectors.get('description', 'div.m-exhibitor-entry__item__body__description')
            description_element = soup.select_one(desc_selector)
            if description_element:
                overview = description_element.get_text(strip=True)
            
            # Extract website URL
            website = ""
            website_elements = soup.find_all('a', href=True)
            for link in website_elements:
                if isinstance(link, Tag):
                    href = link.get('href', '') or ''
                    # Look for external URLs (not internal site links)
                    if isinstance(href, str) and href.startswith('http') and 'dsei.co.uk' not in href:
                        website = href
                        break
            
            company_data = {
                'company_name': company_name,
                'tags': '; '.join(tags),  # Join tags with semicolon
                'overview': overview.replace('\n', ' ').replace('\r', ' '),  # Clean line breaks
                'website': website
            }
            
            self.logger.debug(f"Extracted data for {company_name}")
            return company_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching details for {company_slug}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error processing {company_slug}: {e}")
            return None
    
    def has_next_page(self, page_number: int) -> bool:
        """
        Check if there are more pages to process
        
        Args:
            page_number: Current page number
            
        Returns:
            True if there are more pages, False otherwise
        """
        url = self.list_url_template.format(page=page_number + 1)
        
        try:
            response = self.make_request_with_retry(url, timeout=self.timeouts.get('request_timeout', 30))
            if not response:
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if there are any company links on the next page
            company_links = soup.find_all('a', class_='js-librarylink-entry')
            
            return len(company_links) > 0
            
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False
    
    def save_to_csv(self, filename: Optional[str] = None):
        """
        Save collected data to CSV file
        
        Args:
            filename: Output CSV filename. If None, uses config default.
        """
        if not self.companies_data:
            self.logger.warning("No data to save")
            return
        
        if filename is None:
            # Save to data/processed directory
            data_dir = self.project_root / "data" / "processed"
            data_dir.mkdir(parents=True, exist_ok=True)
            file_path = data_dir / self.config.get_output_config().get('csv_filename', 'dsei_companies.csv')
        else:
            file_path = Path(filename)
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['company_name', 'tags', 'overview', 'website']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for company in self.companies_data:
                    writer.writerow(company)
            
            self.logger.info(f"Saved {len(self.companies_data)} companies to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {e}")
    
    def scrape_all_companies(self, start_page: int = 1, max_pages: Optional[int] = None):
        """
        Main scraping method that follows the flowchart logic
        
        Args:
            start_page: Page number to start from
            max_pages: Maximum number of pages to scrape (None for all)
        """
        self.logger.info("Starting DSEI company scraper")
        
        current_page = start_page
        pages_scraped = 0
        
        while True:
            # Check max pages limit
            if max_pages and pages_scraped >= max_pages:
                self.logger.info(f"Reached maximum pages limit: {max_pages}")
                break
            
            # STEP 1: Get company slugs from current page
            company_slugs = self.get_company_slugs_from_page(current_page)
            
            # Check if page has companies (flowchart decision point)
            if not company_slugs:
                self.logger.info(f"No companies found on page {current_page}. Parsing completed.")
                break
            
            # STEP 2: Process each company
            for slug in company_slugs:
                # Add delay to be respectful to the server
                time.sleep(self.delays.get('between_companies', 1))
                
                company_details = self.get_company_details(slug, current_page)
                if company_details:
                    self.companies_data.append(company_details)
                    self.logger.info(f"Processed: {company_details['company_name']}")
                else:
                    self.logger.warning(f"Failed to get details for slug: {slug}")
            
            # Check if there's a next page (flowchart decision point)
            if not self.has_next_page(current_page):
                self.logger.info("No more pages found. Parsing completed.")
                break
            
            # Move to next page
            current_page += 1
            pages_scraped += 1
            
            # Add delay between pages
            time.sleep(self.delays.get('between_pages', 2))
        
        # Final report
        self.logger.info(f"Scraping completed. Total companies collected: {len(self.companies_data)}")
        self.logger.info(f"Pages processed: {pages_scraped + 1}")
        
        # Save data to CSV
        self.save_to_csv()
