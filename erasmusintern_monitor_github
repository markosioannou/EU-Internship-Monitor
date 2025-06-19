#!/usr/bin/env python3
"""
ErasmusIntern Traineeship Monitor - GitHub Actions Version
Monitors the ErasmusIntern.org website for new traineeship postings and sends Telegram alerts.

This version:
- Reads Telegram credentials from environment variables
- Runs once and exits (no continuous loop)
- Commits CSV updates back to the repository
- Stores data separately from EurOdyssey monitor
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import logging
import os
from datetime import datetime
import hashlib
from typing import List, Dict, Set
import re
import sys

# Configuration
TRAINEESHIP_URL = "https://erasmusintern.org/traineeships"

# Get Telegram config from environment variables
TELEGRAM_CONFIG = {
    'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.environ.get('TELEGRAM_CHAT_ID', '')
}

# File to store traineeships data
DATA_FILE = 'erasmusintern_traineeships.csv'

# Request headers to appear more human-like
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Setup logging for GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ErasmusInternMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def get_page_content(self, url: str) -> str:
        """Fetch page content with error handling."""
        try:
            # Add delay to be respectful to the server
            time.sleep(2)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching page: {e}")
            return None
    
    def extract_date_from_text(self, text: str, patterns: List[str]) -> str:
        """Extract date from text using multiple possible patterns."""
        if not text:
            return ''
            
        # Common date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',      # DD/MM/YYYY or D/M/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',      # DD-MM-YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',      # YYYY-MM-DD
            r'\d{1,2}\.\d{1,2}\.\d{4}',    # DD.MM.YYYY
            r'[A-Za-z]+ \d{1,2}, \d{4}',   # Month DD, YYYY
            r'\d{1,2} [A-Za-z]+ \d{4}',    # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ''
    
    def parse_traineeships(self, html_content: str) -> List[Dict]:
        """Parse traineeship listings from HTML content."""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        traineeships = []
        
        # Debug: Print page title to verify we got the right page
        title = soup.find('title')
        logger.info(f"Parsing ErasmusIntern page: {title.get_text(strip=True) if title else 'Unknown'}")
        
        # Try multiple possible selectors for traineeship listings
        traineeship_containers = self.find_traineeship_containers(soup)
        
        if not traineeship_containers:
            logger.warning("Could not find traineeship containers - page structure may have changed")
            return []
        
        logger.info(f"Found {len(traineeship_containers)} potential traineeship containers")
        
        for i, container in enumerate(traineeship_containers):
            try:
                traineeship = self.parse_single_traineeship(container, i)
                if traineeship:
                    traineeships.append(traineeship)
                    logger.debug(f"Added traineeship: {traineeship['title']} in {traineeship['location']}")
                
            except Exception as e:
                logger.warning(f"Error parsing traineeship container {i}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(traineeships)} traineeships from ErasmusIntern")
        return traineeships
    
    def find_traineeship_containers(self, soup):
        """Find traineeship containers using multiple selector strategies."""
        # Strategy 1: Look for common traineeship/job listing selectors
        selectors = [
            '.traineeship-item', '.job-item', '.internship-item',
            '.listing-item', '.opportunity-item', '.vacancy-item',
            '[class*="traineeship"]', '[class*="internship"]', '[class*="job"]',
            '.card', '.post', '.entry', '.item',
            'article', '.result', '.listing'
        ]
        
        for selector in selectors:
            containers = soup.select(selector)
            if containers and len(containers) > 1:  # Need multiple items
                logger.info(f"Found containers using selector: {selector}")
                return containers
        
        # Strategy 2: Look for repeated structure patterns
        # Find divs that appear multiple times with similar structure
        all_divs = soup.find_all('div')
        class_counts = {}
        
        for div in all_divs:
            classes = div.get('class', [])
            if classes:
                class_key = ' '.join(sorted(classes))
                class_counts[class_key] = class_counts.get(class_key, 0) + 1
        
        # Find classes that appear multiple times (likely listings)
        for class_name, count in class_counts.items():
            if count >= 3:  # At least 3 similar items
                containers = soup.find_all('div', class_=class_name.split())
                if self.validate_containers(containers):
                    logger.info(f"Found containers using repeated pattern: .{class_name} ({count} items)")
                    return containers
        
        # Strategy 3: Fallback - look for any structure with links
        containers = soup.find_all(['div', 'article', 'li'], href=True)
        if not containers:
            containers = soup.find_all(['div', 'article', 'li'])
            containers = [c for c in containers if c.find('a', href=True)]
        
        if containers:
            logger.info(f"Using fallback strategy, found {len(containers)} containers")
            return containers[:20]  # Limit to first 20 to avoid noise
        
        return []
    
    def validate_containers(self, containers):
        """Validate that containers look like traineeship listings."""
        if len(containers) < 2:
            return False
        
        # Check if containers have typical job listing elements
        has_links = sum(1 for c in containers[:5] if c.find('a', href=True)) >= 2
        has_text = sum(1 for c in containers[:5] if len(c.get_text(strip=True)) > 20) >= 2
        
        return has_links and has_text
    
    def parse_single_traineeship(self, container, index: int) -> Dict:
        """Parse a single traineeship container."""
        # Generate unique ID
        container_text = container.get_text(strip=True)
        traineeship_id = hashlib.md5(f"{container_text[:100]}{index}".encode()).hexdigest()[:12]
        
        # Extract title
        title = self.extract_title(container)
        
        # Extract company/organization
        company = self.extract_company(container)
        
        # Extract location
        location = self.extract_location(container)
        
        # Extract dates
        deadline = self.extract_deadline(container)
        start_date = self.extract_start_date(container)
        duration = self.extract_duration(container)
        
        # Extract description snippet
        description = self.extract_description(container)
        
        # Extract link
        link = self.extract_link(container)
        
        # Validate that we have minimum required data
        if not title or len(title.strip()) < 3:
            return None
        
        traineeship = {
            'id': traineeship_id,
            'title': title,
            'company': company,
            'location': location,
            'deadline': deadline,
            'start_date': start_date,
            'duration': duration,
            'description': description[:200] if description else '',  # Limit description length
            'link': link,
            'date_identified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return traineeship
    
    def extract_title(self, container):
        """Extract traineeship title."""
        # Try multiple selectors for title
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5',
            '.title', '.job-title', '.traineeship-title', '.position-title',
            '[class*="title"]', '[class*="heading"]',
            'a[href*="/traineeship"]', 'a[href*="/internship"]', 'a[href*="/job"]'
        ]
        
        for selector in title_selectors:
            element = container.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        
        # Fallback: first link text or strong text
        link = container.find('a', href=True)
        if link:
            title = link.get_text(strip=True)
            if title and len(title) > 3:
                return title
        
        strong = container.find(['strong', 'b'])
        if strong:
            title = strong.get_text(strip=True)
            if title and len(title) > 3:
                return title
        
        return f"Traineeship Opportunity #{container.get('id', 'unknown')}"
    
    def extract_company(self, container):
        """Extract company/organization name."""
        company_selectors = [
            '.company', '.organization', '.employer',
            '[class*="company"]', '[class*="org"]', '[class*="employer"]'
        ]
        
        for selector in company_selectors:
            element = container.select_one(selector)
            if element:
                company = element.get_text(strip=True)
                if company:
                    return company
        
        # Look for common company indicators in text
        text = container.get_text()
        company_patterns = [
            r'Company:\s*([^\n]+)',
            r'Organization:\s*([^\n]+)',
            r'Employer:\s*([^\n]+)',
            r'at\s+([A-Z][^\n,]+(?:Ltd|Inc|Corp|GmbH|B\.V\.|S\.A\.))',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return 'Unknown Organization'
    
    def extract_location(self, container):
        """Extract location information."""
        location_selectors = [
            '.location', '.city', '.country', '.place',
            '[class*="location"]', '[class*="city"]', '[class*="country"]'
        ]
        
        for selector in location_selectors:
            element = container.select_one(selector)
            if element:
                location = element.get_text(strip=True)
                if location:
                    return location
        
        # Look for location patterns in text
        text = container.get_text()
        location_patterns = [
            r'Location:\s*([^\n]+)',
            r'City:\s*([^\n]+)',
            r'Country:\s*([^\n]+)',
            r'in\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return 'Unknown Location'
    
    def extract_deadline(self, container):
        """Extract application deadline."""
        text = container.get_text()
        deadline_patterns = [
            r'Deadline:\s*([^\n]+)',
            r'Apply by:\s*([^\n]+)',
            r'Application deadline:\s*([^\n]+)',
            r'Due:\s*([^\n]+)',
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self.extract_date_from_text(match.group(1), [])
        
        return ''
    
    def extract_start_date(self, container):
        """Extract start date."""
        text = container.get_text()
        start_patterns = [
            r'Start date:\s*([^\n]+)',
            r'Starting:\s*([^\n]+)',
            r'Begins:\s*([^\n]+)',
            r'From:\s*([^\n]+)',
        ]
        
        for pattern in start_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self.extract_date_from_text(match.group(1), [])
        
        return ''
    
    def extract_duration(self, container):
        """Extract duration information."""
        text = container.get_text()
        duration_patterns = [
            r'Duration:\s*([^\n]+)',
            r'Length:\s*([^\n]+)',
            r'Period:\s*([^\n]+)',
            r'(\d+)\s*months?',
            r'(\d+)\s*weeks?',
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip() if 'Duration:' in pattern else match.group(0)
        
        return ''
    
    def extract_description(self, container):
        """Extract description snippet."""
        # Remove title and other structured elements to get description
        container_copy = container.__copy__()
        
        # Remove common non-description elements
        for tag in container_copy.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            tag.decompose()
        
        text = container_copy.get_text(strip=True)
        
        # Take first reasonable chunk of text
        sentences = text.split('.')
        description = ''
        
        for sentence in sentences:
            if len(sentence.strip()) > 20:  # Substantial sentence
                description = sentence.strip()
                break
        
        return description
    
    def extract_link(self, container):
        """Extract link to full traineeship details."""
        # Look for links within the container
        link_element = container.find('a', href=True)
        
        if link_element:
            href = link_element['href']
            
            # Make absolute URL
            if href.startswith('/'):
                return f"https://erasmusintern.org{href}"
            elif href.startswith('http'):
                return href
            else:
                return f"https://erasmusintern.org/{href}"
        
        return ''
    
    def load_previous_data(self) -> List[Dict]:
        """Load previously stored traineeship data from CSV."""
        if not os.path.exists(DATA_FILE):
            logger.info("No previous ErasmusIntern data file found - this is the first run")
            return []
        
        try:
            traineeships = []
            with open(DATA_FILE, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    traineeships.append(row)
            
            logger.info(f"Loaded {len(traineeships)} previous ErasmusIntern traineeships from CSV")
            return traineeships
            
        except Exception as e:
            logger.error(f"Error loading previous ErasmusIntern data from CSV: {e}")
            return []
    
    def save_current_data(self, traineeships: List[Dict]):
        """Save current traineeship data to CSV."""
        if not traineeships:
            logger.warning("No ErasmusIntern traineeships to save")
            return
            
        try:
            # Define CSV headers
            fieldnames = [
                'id', 'title', 'company', 'location', 'deadline', 'start_date',
                'duration', 'description', 'link', 'date_identified'
            ]
            
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists(DATA_FILE)
            
            with open(DATA_FILE, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                    logger.info("Created new ErasmusIntern CSV file with headers")
                
                # Write new traineeships
                for traineeship in traineeships:
                    writer.writerow(traineeship)
                
            logger.info(f"Saved {len(traineeships)} ErasmusIntern traineeships to CSV")
            
        except Exception as e:
            logger.error(f"Error saving ErasmusIntern data to CSV: {e}")
    
    def get_existing_ids(self) -> Set[str]:
        """Get set of existing traineeship IDs from CSV."""
        existing_ids = set()
        previous_data = self.load_previous_data()
        
        for traineeship in previous_data:
            if 'id' in traineeship:
                existing_ids.add(traineeship['id'])
        
        logger.info(f"Found {len(existing_ids)} existing ErasmusIntern traineeship IDs")
        return existing_ids
    
    def find_new_traineeships(self, current_traineeships: List[Dict]) -> List[Dict]:
        """Find traineeships that are not already in the CSV file."""
        existing_ids = self.get_existing_ids()
        new_traineeships = []
        
        for traineeship in current_traineeships:
            if traineeship['id'] not in existing_ids:
                new_traineeships.append(traineeship)
        
        logger.info(f"Found {len(new_traineeships)} new ErasmusIntern traineeships out of {len(current_traineeships)} total")
        return new_traineeships
    
    def send_telegram_alert(self, new_traineeships: List[Dict]):
        """Send Telegram alert with new traineeships."""
        if not new_traineeships:
            logger.info("No new ErasmusIntern traineeships to send")
            return
            
        try:
            # Create message text
            message = f"🇪🇺 *{len(new_traineeships)} New ErasmusIntern Traineeship(s) Found!*\n\n"
            message += f"Found on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for i, traineeship in enumerate(new_traineeships, 1):
                # Clean up text to avoid issues
                title = str(traineeship.get('title', 'No title')).strip()
                company = str(traineeship.get('company', 'Unknown company')).strip()
                location = str(traineeship.get('location', 'Unknown location')).strip()
                deadline = str(traineeship.get('deadline', '')).strip()
                start_date = str(traineeship.get('start_date', '')).strip()
                duration = str(traineeship.get('duration', '')).strip()
                link = str(traineeship.get('link', '')).strip()
                
                message += f"*{i}. {title}*\n"
                message += f"🏢 Company: {company}\n"
                message += f"📍 Location: {location}\n"
                
                if start_date:
                    message += f"📅 Start: {start_date}\n"
                if duration:
                    message += f"⏱️ Duration: {duration}\n"
                if deadline:
                    message += f"⏰ Deadline: {deadline}\n"
                
                if link and link.startswith('http'):
                    message += f"🔗 [View Details]({link})\n"
                message += "\n"
            
            message += f"[View All ErasmusIntern Traineeships]({TRAINEESHIP_URL})\n"
            message += "_Source: ErasmusIntern.org - Auto-generated alert_"
            
            # Send via Telegram Bot API
            telegram_url = f"https://api.telegram.org/bot{TELEGRAM_CONFIG['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': str(TELEGRAM_CONFIG['chat_id']),
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(telegram_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"ErasmusIntern Telegram alert sent for {len(new_traineeships)} new traineeships")
            else:
                logger.error(f"Telegram API returned error: {result}")
            
        except Exception as e:
            logger.error(f"Error sending ErasmusIntern Telegram message: {e}")
            # If message is too long, try sending a shorter version
            if "message is too long" in str(e).lower():
                try:
                    short_message = f"🇪🇺 *{len(new_traineeships)} New ErasmusIntern Traineeships Found!*\n\n"
                    for traineeship in new_traineeships[:3]:
                        title = str(traineeship.get('title', 'No title')).strip()
                        company = str(traineeship.get('company', 'Unknown')).strip()
                        short_message += f"• {title} at {company}\n"
                    if len(new_traineeships) > 3:
                        short_message += f"• ... and {len(new_traineeships) - 3} more\n"
                    short_message += f"\n[View All]({TRAINEESHIP_URL})"
                    
                    payload['text'] = short_message
                    response = requests.post(telegram_url, json=payload, timeout=30)
                    response.raise_for_status()
                    logger.info("Sent shortened ErasmusIntern Telegram alert")
                except Exception as e2:
                    logger.error(f"Error sending shortened ErasmusIntern Telegram message: {e2}")
    
    def check_for_new_traineeships(self):
        """Main function to check for new traineeships."""
        logger.info("Checking for new ErasmusIntern traineeships...")
        
        # Get current page content
        html_content = self.get_page_content(TRAINEESHIP_URL)
        if not html_content:
            logger.error("Failed to fetch ErasmusIntern page content")
            return False
        
        # Parse current traineeships
        current_traineeships = self.parse_traineeships(html_content)
        if not current_traineeships:
            logger.warning("No ErasmusIntern traineeships found - check if page structure has changed")
            return False
        
        # Find new traineeships (those not in CSV)
        new_traineeships = self.find_new_traineeships(current_traineeships)
        
        if new_traineeships:
            logger.info(f"Found {len(new_traineeships)} new ErasmusIntern traineeships!")
            # Send notification
            self.send_telegram_alert(new_traineeships)
            # Save only new traineeships to CSV
            self.save_current_data(new_traineeships)
        else:
            logger.info("No new ErasmusIntern traineeships found")
        
        logger.info(f"Total ErasmusIntern traineeships on page: {len(current_traineeships)}")
        logger.info(f"New ErasmusIntern traineeships added: {len(new_traineeships)}")
        
        return True

def main():
    """Main function for GitHub Actions."""
    logger.info("Starting ErasmusIntern traineeship monitor...")
    
    # Validate Telegram configuration
    required_config = ['bot_token', 'chat_id']
    if any(not TELEGRAM_CONFIG.get(key) for key in required_config):
        logger.error("Missing Telegram configuration in environment variables")
        logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets in GitHub")
        sys.exit(1)
    
    logger.info(f"Monitoring ErasmusIntern URL: {TRAINEESHIP_URL}")
    
    # Create monitor and run check
    monitor = ErasmusInternMonitor()
    success = monitor.check_for_new_traineeships()
    
    if success:
        logger.info("ErasmusIntern monitor completed successfully")
        sys.exit(0)
    else:
        logger.error("ErasmusIntern monitor encountered errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
