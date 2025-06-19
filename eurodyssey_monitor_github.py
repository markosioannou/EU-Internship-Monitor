#!/usr/bin/env python3
"""
EurOdyssey Traineeship Monitor - GitHub Actions Version
Monitors the EurOdyssey website for new traineeship postings and sends Telegram alerts.
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

# Configuration - reads from environment variables
TRAINEESHIP_URL = "https://eurodyssey.aer.eu/traineeships/?traineeship-country=&sector=&traineeship-start-date=19%2F06%2F2025&region=&traineeship-title-or-ref=&traineeship-start-date-before=&sortfield=&sortorder=desc"

# Get Telegram config from environment variables
TELEGRAM_CONFIG = {
    'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.environ.get('TELEGRAM_CHAT_ID', '')
}

# File to store traineeships data
DATA_FILE = 'eurodyssey_traineeships.csv'

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

class TraineeshipMonitor:
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
    
    def extract_date_from_text(self, element, prefix: str) -> str:
        """Extract date from text with given prefix (e.g., 'From:', 'Until:')."""
        try:
            text = element.get_text()
            # Look for pattern like "From: 01/08/2025" or "Until: 31/12/2025"
            pattern = rf"{re.escape(prefix)}\s*(\d{{2}}/\d{{2}}/\d{{4}})"
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        except Exception as e:
            logger.debug(f"Error extracting date with prefix '{prefix}': {e}")
        return ''
    
    def extract_deadline_date(self, element) -> str:
        """Extract deadline date from the element."""
        try:
            # Look for deadline value in the second ed-table-data section
            deadline_sections = element.find_all('div', class_='ed-table-data ed-table-data--second')
            for section in deadline_sections:
                deadline_label = section.find('p', class_='ed-table-data__label')
                if deadline_label and 'deadline' in deadline_label.get_text().lower():
                    deadline_value = section.find('p', class_='ed-table-data__value')
                    if deadline_value:
                        deadline_text = deadline_value.get_text(strip=True)
                        # Extract date pattern
                        date_pattern = r'\d{2}/\d{2}/\d{4}'
                        match = re.search(date_pattern, deadline_text)
                        if match:
                            return match.group(0)
        except Exception as e:
            logger.debug(f"Error extracting deadline date: {e}")
        return ''
    
    def parse_traineeships(self, html_content: str) -> List[Dict]:
        """Parse traineeship listings from HTML content."""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        traineeships = []
        
        # Debug: Print page title to verify we got the right page
        title = soup.find('title')
        logger.info(f"Parsing page: {title.get_text(strip=True) if title else 'Unknown'}")
        
        # Find the traineeship table
        table = soup.find('table', id='traineeship-table')
        if not table:
            logger.warning("Could not find traineeship table")
            return []
        
        # Find all traineeship rows
        traineeship_rows = table.find_all('tr', class_='ed-table-row')
        logger.info(f"Found {len(traineeship_rows)} traineeship rows")
        
        for i, row in enumerate(traineeship_rows):
            try:
                # Extract data-id attribute
                traineeship_id = row.get('data-id', f'unknown_{i}')
                
                # Get all table cells
                cells = row.find_all('td')
                if len(cells) < 5:
                    logger.warning(f"Row {i} has insufficient cells: {len(cells)}")
                    continue
                
                # Extract dates from first cell
                date_cell = cells[0]
                from_date = self.extract_date_from_text(date_cell, "From:")
                until_date = self.extract_date_from_text(date_cell, "Until:")
                deadline_date = self.extract_deadline_date(date_cell)
                
                # Extract position title from second cell
                title_cell = cells[1]
                title_value = title_cell.find('p', class_='ed-table-data__value')
                title = title_value.get_text(strip=True) if title_value else f'Position {i+1}'
                
                # Extract area from second cell (second ed-table-data)
                area_data = title_cell.find_all('div', class_='ed-table-data')
                area = 'Unknown Area'
                if len(area_data) >= 2:
                    area_value = area_data[1].find('p', class_='ed-table-data__value')
                    if area_value:
                        area = area_value.get_text(strip=True)
                
                # Extract region and country from third cell
                location_cell = cells[2]
                location_data = location_cell.find_all('div', class_='ed-table-data')
                
                region = 'Unknown Region'
                country = 'Unknown Country'
                if len(location_data) >= 1:
                    region_value = location_data[0].find('p', class_='ed-table-data__value')
                    if region_value:
                        region = region_value.get_text(strip=True)
                
                if len(location_data) >= 2:
                    country_value = location_data[1].find('p', class_='ed-table-data__value')
                    if country_value:
                        country = country_value.get_text(strip=True)
                
                # Extract reference from fourth cell
                ref_cell = cells[3]
                ref_value = ref_cell.find('p', class_='ed-table-data__value')
                reference = ref_value.get_text(strip=True) if ref_value else f'REF_{traineeship_id}'
                
                # Extract link from fifth cell
                link_cell = cells[4]
                link_elem = link_cell.find('a', class_='traineeship-listing__traineeship-link')
                link = link_elem['href'] if link_elem and link_elem.get('href') else ''
                
                # Ensure full URL
                if link and link.startswith('/'):
                    link = 'https://eurodyssey.aer.eu' + link
                elif link and not link.startswith('http'):
                    link = 'https://eurodyssey.aer.eu/' + link
                
                # Create traineeship object
                traineeship = {
                    'id': traineeship_id,
                    'from_date': from_date,
                    'until_date': until_date,
                    'deadline': deadline_date,
                    'title': title,
                    'area': area,
                    'region': region,
                    'country': country,
                    'reference': reference,
                    'link': link,
                    'date_identified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                traineeships.append(traineeship)
                logger.debug(f"Added traineeship: {title} in {region}, {country} (From: {from_date}, Until: {until_date})")
                
            except Exception as e:
                logger.warning(f"Error parsing traineeship row {i}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(traineeships)} traineeships")
        return traineeships
    
    def load_previous_data(self) -> List[Dict]:
        """Load previously stored traineeship data from CSV."""
        if not os.path.exists(DATA_FILE):
            logger.info("No previous data file found - this is the first run")
            return []
        
        try:
            traineeships = []
            with open(DATA_FILE, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    traineeships.append(row)
            
            logger.info(f"Loaded {len(traineeships)} previous traineeships from CSV")
            return traineeships
            
        except Exception as e:
            logger.error(f"Error loading previous data from CSV: {e}")
            return []
    
    def save_current_data(self, traineeships: List[Dict]):
        """Save current traineeship data to CSV."""
        if not traineeships:
            logger.warning("No traineeships to save")
            return
            
        try:
            # Define CSV headers
            fieldnames = [
                'id', 'from_date', 'until_date', 'deadline', 'title', 
                'area', 'region', 'country', 'reference', 'link', 'date_identified'
            ]
            
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists(DATA_FILE)
            
            with open(DATA_FILE, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                    logger.info("Created new CSV file with headers")
                
                # Write new traineeships
                for traineeship in traineeships:
                    writer.writerow(traineeship)
                
            logger.info(f"Saved {len(traineeships)} traineeships to CSV")
            
        except Exception as e:
            logger.error(f"Error saving data to CSV: {e}")
    
    def get_existing_ids(self) -> Set[str]:
        """Get set of existing traineeship IDs from CSV."""
        existing_ids = set()
        previous_data = self.load_previous_data()
        
        for traineeship in previous_data:
            if 'id' in traineeship:
                existing_ids.add(traineeship['id'])
        
        logger.info(f"Found {len(existing_ids)} existing traineeship IDs")
        return existing_ids
    
    def find_new_traineeships(self, current_traineeships: List[Dict]) -> List[Dict]:
        """Find traineeships that are not already in the CSV file."""
        existing_ids = self.get_existing_ids()
        new_traineeships = []
        
        for traineeship in current_traineeships:
            if traineeship['id'] not in existing_ids:
                new_traineeships.append(traineeship)
        
        logger.info(f"Found {len(new_traineeships)} new traineeships out of {len(current_traineeships)} total")
        return new_traineeships
    
    def send_telegram_alert(self, new_traineeships: List[Dict]):
        """Send Telegram alert with new traineeships."""
        if not new_traineeships:
            logger.info("No new traineeships to send")
            return
            
        try:
            # Create message text
            message = f"🚨 *{len(new_traineeships)} New EurOdyssey Traineeship(s) Found!*\n\n"
            message += f"Found on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for i, traineeship in enumerate(new_traineeships, 1):
                # Clean up text to avoid issues
                title = str(traineeship.get('title', 'No title')).strip()
                area = str(traineeship.get('area', 'Unknown area')).strip()
                region = str(traineeship.get('region', 'Unknown region')).strip()
                country = str(traineeship.get('country', 'Unknown country')).strip()
                reference = str(traineeship.get('reference', '')).strip()
                link = str(traineeship.get('link', '')).strip()
                from_date = str(traineeship.get('from_date', '')).strip()
                until_date = str(traineeship.get('until_date', '')).strip()
                deadline = str(traineeship.get('deadline', '')).strip()
                
                message += f"*{i}. {title}*\n"
                message += f"📋 Area: {area}\n"
                message += f"📍 Region: {region}, {country}\n"
                
                # Add date information if available
                if from_date and until_date:
                    message += f"📅 Period: {from_date} - {until_date}\n"
                elif from_date:
                    message += f"📅 From: {from_date}\n"
                
                if deadline:
                    message += f"⏰ Deadline: {deadline}\n"
                
                if reference:
                    message += f"🔢 Reference: {reference}\n"
                if link and link.startswith('http'):
                    message += f"🔗 [View Details]({link})\n"
                message += "\n"
            
            message += f"[View All Traineeships]({TRAINEESHIP_URL})\n"
            message += "_This alert was generated automatically by your EurOdyssey monitor._"
            
            # Debug: Print message length and preview
            logger.info(f"Message length: {len(message)} characters")
            logger.info(f"Message preview: {message[:200]}...")
            
            # Ensure message is not empty
            if not message.strip():
                logger.error("Message is empty after construction!")
                return
            
            # Send via Telegram Bot API
            telegram_url = f"https://api.telegram.org/bot{TELEGRAM_CONFIG['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': str(TELEGRAM_CONFIG['chat_id']),  # Ensure string
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            logger.info(f"Sending to chat_id: {payload['chat_id']}")
            
            response = requests.post(telegram_url, json=payload, timeout=30)
            
            # Debug response
            logger.info(f"Telegram API response: {response.status_code}")
            logger.info(f"Response text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"Telegram alert sent for {len(new_traineeships)} new traineeships")
            else:
                logger.error(f"Telegram API returned error: {result}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            # If message is too long, try sending a shorter version
            if "message is too long" in str(e).lower():
                try:
                    short_message = f"🚨 *{len(new_traineeships)} New EurOdyssey Traineeships Found!*\n\n"
                    for traineeship in new_traineeships[:3]:  # Only show first 3
                        title = str(traineeship.get('title', 'No title')).strip()
                        region = str(traineeship.get('region', 'Unknown')).strip()
                        deadline = str(traineeship.get('deadline', '')).strip()
                        short_message += f"• {title} in {region}"
                        if deadline:
                            short_message += f" (Deadline: {deadline})"
                        short_message += "\n"
                    if len(new_traineeships) > 3:
                        short_message += f"• ... and {len(new_traineeships) - 3} more\n"
                    short_message += f"\n[View All]({TRAINEESHIP_URL})"
                    
                    payload['text'] = short_message
                    response = requests.post(telegram_url, json=payload, timeout=30)
                    response.raise_for_status()
                    logger.info("Sent shortened Telegram alert")
                except Exception as e2:
                    logger.error(f"Error sending shortened Telegram message: {e2}")
    
    def check_for_new_traineeships(self):
        """Main function to check for new traineeships."""
        logger.info("Checking for new traineeships...")
        
        # Get current page content
        html_content = self.get_page_content(TRAINEESHIP_URL)
        if not html_content:
            logger.error("Failed to fetch page content")
            return False
        
        # Parse current traineeships
        current_traineeships = self.parse_traineeships(html_content)
        if not current_traineeships:
            logger.warning("No traineeships found - check if page structure has changed")
            return False
        
        # Find new traineeships (those not in CSV)
        new_traineeships = self.find_new_traineeships(current_traineeships)
        
        if new_traineeships:
            logger.info(f"Found {len(new_traineeships)} new traineeships!")
            # Send notification
            self.send_telegram_alert(new_traineeships)
            # Save only new traineeships to CSV
            self.save_current_data(new_traineeships)
        else:
            logger.info("No new traineeships found")
        
        logger.info(f"Total traineeships on page: {len(current_traineeships)}")
        logger.info(f"New traineeships added: {len(new_traineeships)}")
        
        return True

def main():
    """Main function for GitHub Actions."""
    logger.info("Starting EurOdyssey traineeship monitor (GitHub Actions version)...")
    
    # Validate Telegram configuration
    required_config = ['bot_token', 'chat_id']
    if any(not TELEGRAM_CONFIG.get(key) for key in required_config):
        logger.error("Missing Telegram configuration in environment variables")
        logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets in GitHub")
        sys.exit(1)
    
    logger.info(f"Monitoring URL: {TRAINEESHIP_URL}")
    logger.info(f"Telegram alerts will be sent to chat ID: {TELEGRAM_CONFIG['chat_id']}")
    
    # Create monitor and run check
    monitor = TraineeshipMonitor()
    success = monitor.check_for_new_traineeships()
    
    if success:
        logger.info("Monitor completed successfully")
        sys.exit(0)
    else:
        logger.error("Monitor encountered errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
