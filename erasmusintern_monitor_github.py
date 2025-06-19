#!/usr/bin/env python3
"""
Improved ErasmusIntern Traineeship Parser - GitHub Actions Version
More focused parsing methods for capturing specific fields from ErasmusIntern.org
Designed to run as a GitHub Action on a schedule.

This version:
- Reads Telegram credentials from environment variables
- Runs once and exits (no continuous loop)
- Commits CSV updates back to the repository
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
    
    def parse_traineeships(self, html_content: str) -> List[Dict]:
        """Parse traineeship listings from HTML content with focused selectors."""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        traineeships = []
        
        # Debug: Print page title to verify we got the right page
        title = soup.find('title')
        logger.info(f"Parsing ErasmusIntern page: {title.get_text(strip=True) if title else 'Unknown'}")
        
        # Try multiple strategies to find traineeship containers
        traineeship_containers = self.find_traineeship_containers_robust(soup)
        
        if not traineeship_containers:
            logger.warning("Could not find traineeship containers - page structure may have changed")
            # Basic structure info for debugging
            view_content = soup.find('div', class_='view-content')
            if view_content:
                logger.info("Found view-content div")
                divs_in_content = view_content.find_all('div', recursive=False)
                logger.info(f"Found {len(divs_in_content)} direct child divs in view-content")
            else:
                logger.warning("Could not find view-content div")
            return []
        
        logger.info(f"Found {len(traineeship_containers)} traineeship containers")
        
        for i, container in enumerate(traineeship_containers):
            try:
                traineeship = self.parse_single_traineeship(container, i)
                if traineeship:
                    traineeships.append(traineeship)
                    logger.debug(f"Parsed: {traineeship['title']} at {traineeship['company']}")
                
            except Exception as e:
                logger.warning(f"Error parsing traineeship {i}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(traineeships)} ErasmusIntern traineeships")
        return traineeships
    
    def find_traineeship_containers_robust(self, soup):
        """Find traineeship containers using multiple strategies."""
        # Strategy 1: Exact class match (handle extra spaces)
        containers = soup.find_all('div', class_=lambda x: x and 'node' in x and 'node-traineeship' in x and 'view-mode-media_list' in x)
        if containers:
            logger.info(f"Found containers using exact class match: {len(containers)}")
            return containers
        
        # Strategy 2: Look for divs with 'about' attribute containing 'traineeship'
        containers = soup.find_all('div', attrs={'about': lambda x: x and 'traineeship' in x})
        if containers:
            logger.info(f"Found containers using 'about' attribute: {len(containers)}")
            return containers
        
        # Strategy 3: Look within view-content for nested structures
        view_content = soup.find('div', class_='view-content')
        if view_content:
            # Look for divs that contain traineeship links
            potential_containers = []
            for div in view_content.find_all('div', recursive=True):
                # Check if this div contains a link to a traineeship
                traineeship_link = div.find('a', href=lambda x: x and 'traineeship' in x)
                if traineeship_link and 'node' in str(div.get('class', [])):
                    potential_containers.append(div)
            
            if potential_containers:
                logger.info(f"Found containers using traineeship links: {len(potential_containers)}")
                return potential_containers
        
        # Strategy 4: Look for any div with a title that links to a traineeship
        containers = []
        for h3 in soup.find_all('h3'):
            link = h3.find('a', href=lambda x: x and 'traineeship' in x)
            if link:
                # Find the parent container
                parent = h3.find_parent('div', class_=lambda x: x and 'node' in x)
                if parent and parent not in containers:
                    containers.append(parent)
        
        if containers:
            logger.info(f"Found containers using h3 title links: {len(containers)}")
            return containers
        
        logger.error("All container detection strategies failed")
        return []
    
    def parse_single_traineeship(self, container, index: int) -> Dict:
        """Parse a single traineeship with focused field extraction."""
        
        # Extract title
        title = self.extract_title(container)
        if not title or len(title.strip()) < 3:
            return None
        
        # Generate unique ID based on title and content
        container_text = container.get_text(strip=True)
        traineeship_id = hashlib.md5(f"{title}{container_text[:100]}".encode()).hexdigest()[:12]
        
        # Extract other fields
        field = self.extract_field(container)
        company = self.extract_company(container)
        location = self.extract_location(container)
        duration = self.extract_duration(container)
        post_date = self.extract_post_date(container)
        deadline = self.extract_deadline(container)
        link = self.extract_link(container)
        description = self.extract_description(container)
        
        traineeship = {
            'id': traineeship_id,
            'title': title,
            'field': field,
            'company': company,
            'location': location,
            'duration': duration,
            'post_date': post_date,
            'deadline': deadline,
            'description': description[:200] if description else '',
            'link': link,
            'date_identified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return traineeship
    
    def extract_title(self, container) -> str:
        """Extract traineeship title from the specific structure."""
        try:
            # Look for the title in the h3 with class "dot-title"
            title_element = container.select_one('h3.dot-title a')
            if title_element:
                return title_element.get_text(strip=True)
            
            # Fallback: look for any h3 with a link
            h3_link = container.select_one('h3 a')
            if h3_link:
                return h3_link.get_text(strip=True)
                
            # Final fallback: first link that looks like a title
            first_link = container.find('a', href=True)
            if first_link and len(first_link.get_text(strip=True)) > 10:
                return first_link.get_text(strip=True)
                
        except Exception as e:
            logger.debug(f"Error extracting title: {e}")
            
        return "Unknown Title"
    
    def extract_field(self, container) -> str:
        """Extract field of study from ds-top-content h5."""
        try:
            # Look for field in the ds-top-content section
            field_element = container.select_one('.ds-top-content h5')
            if field_element:
                return field_element.get_text(strip=True)
        except Exception as e:
            logger.debug(f"Error extracting field: {e}")
            
        return "Unknown Field"
    
    def extract_company(self, container) -> str:
        """Extract company/recruiter name."""
        try:
            # Look for recruiter name in the specific field
            company_element = container.select_one('.field-name-recruiter-name a')
            if company_element:
                return company_element.get_text(strip=True)
                
            # Fallback: look for any element with recruiter in class name
            recruiter_div = container.find('div', class_=lambda x: x and 'recruiter' in x.lower())
            if recruiter_div:
                link = recruiter_div.find('a')
                if link:
                    return link.get_text(strip=True)
                    
        except Exception as e:
            logger.debug(f"Error extracting company: {e}")
            
        return "Unknown Company"
    
    def extract_location(self, container) -> str:
        """Extract location information (country and city)."""
        try:
            locations = []
            
            # Look for location information in the specific field structure
            location_containers = container.select('.field-name-field-traineeship-full-location .field-item')
            
            for loc_container in location_containers:
                country_elem = loc_container.select_one('.country')
                city_elem = loc_container.select_one('.field-name-field-traineeship-location-city')
                
                country = country_elem.get_text(strip=True) if country_elem else ""
                city = city_elem.get_text(strip=True) if city_elem else ""
                
                if country and city:
                    locations.append(f"{city}, {country}")
                elif country:
                    locations.append(country)
                elif city:
                    locations.append(city)
            
            if locations:
                return "; ".join(locations[:3])  # Limit to 3 locations
                
        except Exception as e:
            logger.debug(f"Error extracting location: {e}")
            
        return "Unknown Location"
    
    def extract_duration(self, container) -> str:
        """Extract duration from the specific field."""
        try:
            # Look for duration in the labeled field
            duration_element = container.select_one('.field-name-field-traineeship-duration .field-item')
            if duration_element:
                return duration_element.get_text(strip=True)
                
        except Exception as e:
            logger.debug(f"Error extracting duration: {e}")
            
        return ""
    
    def extract_post_date(self, container) -> str:
        """Extract post date from the specific field."""
        try:
            # Look for post date in the labeled field
            post_date_element = container.select_one('.field-name-post-date .field-item')
            if post_date_element:
                return post_date_element.get_text(strip=True)
                
        except Exception as e:
            logger.debug(f"Error extracting post date: {e}")
            
        return ""
    
    def extract_deadline(self, container) -> str:
        """Extract deadline from the specific field."""
        try:
            # Look for deadline in the labeled field
            deadline_element = container.select_one('.field-name-field-traineeship-apply-deadline .field-item')
            if deadline_element:
                return deadline_element.get_text(strip=True)
                
        except Exception as e:
            logger.debug(f"Error extracting deadline: {e}")
            
        return ""
    
    def extract_link(self, container) -> str:
        """Extract link to the full traineeship details."""
        try:
            # Look for the main title link
            link_element = container.select_one('h3.dot-title a')
            if link_element and link_element.get('href'):
                href = link_element['href']
                if href.startswith('/'):
                    return f"https://erasmusintern.org{href}"
                elif href.startswith('http'):
                    return href
                else:
                    return f"https://erasmusintern.org/{href}"
                    
        except Exception as e:
            logger.debug(f"Error extracting link: {e}")
            
        return ""
    
    def extract_description(self, container) -> str:
        """Extract description snippet."""
        try:
            # Look for description in the body field
            desc_element = container.select_one('.field-name-body .field-item')
            if desc_element:
                # Get text and clean it up
                desc_text = desc_element.get_text(strip=True)
                # Remove any HTML tags that might have been missed
                desc_text = re.sub(r'<[^>]+>', '', desc_text)
                return desc_text
                
        except Exception as e:
            logger.debug(f"Error extracting description: {e}")
            
        return ""
    
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
            # Define CSV headers with the focused fields
            fieldnames = [
                'id', 'title', 'field', 'company', 'location', 'duration',
                'post_date', 'deadline', 'description', 'link', 'date_identified'
            ]
            
            file_exists = os.path.exists(DATA_FILE)
            
            with open(DATA_FILE, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                    logger.info("Created new ErasmusIntern CSV file with headers")
                
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
            # Create message text with focused fields
            message = f"🇪🇺 *{len(new_traineeships)} New ErasmusIntern Traineeship(s) Found!*\n\n"
            message += f"Found on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for i, traineeship in enumerate(new_traineeships, 1):
                title = str(traineeship.get('title', 'No title')).strip()
                field = str(traineeship.get('field', 'Unknown field')).strip()
                company = str(traineeship.get('company', 'Unknown company')).strip()
                location = str(traineeship.get('location', 'Unknown location')).strip()
                duration = str(traineeship.get('duration', '')).strip()
                deadline = str(traineeship.get('deadline', '')).strip()
                link = str(traineeship.get('link', '')).strip()
                
                message += f"*{i}. {title}*\n"
                message += f"📚 Field: {field}\n"
                message += f"🏢 Company: {company}\n"
                message += f"📍 Location: {location}\n"
                
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
            # Try sending a shorter version if message is too long
            if "message is too long" in str(e).lower():
                try:
                    short_message = f"🇪🇺 *{len(new_traineeships)} New ErasmusIntern Traineeships!*\n\n"
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
        
        # Find new traineeships
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
    logger.info("Starting ErasmusIntern traineeship monitor (GitHub Actions version)...")
    
    # Validate Telegram configuration
    required_config = ['bot_token', 'chat_id']
    if any(not TELEGRAM_CONFIG.get(key) for key in required_config):
        logger.error("Missing Telegram configuration in environment variables")
        logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets in GitHub")
        sys.exit(1)
    
    logger.info(f"Monitoring ErasmusIntern URL: {TRAINEESHIP_URL}")
    logger.info(f"Telegram alerts will be sent to chat ID: {TELEGRAM_CONFIG['chat_id']}")
    
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
