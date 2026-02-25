"""
Auto-extraction module for Bandcamp credentials.
Automatically extracts cookies from browser and crumb from Bandcamp.
"""

import os
import json
import re
from typing import Optional, Dict, Tuple
from pathlib import Path

try:
    import browser_cookie3
    BROWSER_COOKIE_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

from app.logger import logger


class CredentialExtractor:
    """Auto-extract Bandcamp credentials from browser and website."""
    
    BANDCAMP_DOMAIN = ".bandcamp.com"
    BANDCAMP_YUM_URL = "https://bandcamp.com/yum"
    
    def __init__(self):
        """Initialize credential extractor."""
        self.client_id: Optional[str] = None
        self.session: Optional[str] = None
        self.identity: Optional[str] = None
        self.crumb: Optional[str] = None
        user_data_dir = os.path.join(os.getcwd(), 'bandcamp_profile')
        logger.info(f"Launching Playwright to extract cookies. Profile: {user_data_dir}")
        
        from playwright.sync_api import sync_playwright
        
        try:
            with sync_playwright() as p:
                logger.info("Opening browser window... Please log in to Bandcamp if prompted.")
                
                # Launch persistent context with headless=False so user can log in
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,  # VERY IMPORTANT: Visible window so they can type credentials
                    viewport={'width': 1000, 'height': 800}
                )
                
                page = browser.new_page() if len(browser.pages) == 0 else browser.pages[0]
                
                try:
                    # Go to YUM page to check login status
                    page.goto(self.BANDCAMP_YUM_URL, wait_until="networkidle", timeout=30000)
                    
                    # Wait for identity cookie to appear (up to 60 seconds if they need to log in)
                    logger.info("Waiting up to 60 seconds for successful Bandcamp login...")
                    
                    import time
                    start_time = time.time()
                    logged_in = False
                    
                    while time.time() - start_time < 60:
                        cookies = browser.cookies()
                        cookie_dict = {c['name']: c['value'] for c in cookies if 'bandcamp.com' in c.get('domain', '')}
                        
                        if 'client_id' in cookie_dict and 'session' in cookie_dict and 'identity' in cookie_dict:
                            self.client_id = cookie_dict['client_id']
                            self.session = cookie_dict['session']
                            self.identity = cookie_dict['identity']
                            logged_in = True
                            
                            # Also grab HTML for crumb extraction later
                            self._cached_html = page.content()
                            break
                            
                        # Refresh page or just wait
                        time.sleep(2)
                        
                    if logged_in:
                        logger.info("✓ Successfully extracted authentication cookies via Playwright!")
                        return True
                    else:
                        logger.warning("Timeout: Could not detect Bandcamp login cookies after 60 seconds.")
                        return False
                        
                except Exception as inner_e:
                    logger.warning(f"Playwright navigation/wait failed: {inner_e}")
                    return False
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"Playwright launch failed. Error: {e}")
            return False
    
    def extract_crumb_from_page(self) -> bool:
        """Extract crumb from Bandcamp page.
        
        Returns:
            True if successful
        """
        if not SCRAPING_AVAILABLE:
            logger.warning("requests/beautifulsoup4 not installed")
            return False
        
        if not self.client_id or not self.session:
            logger.warning("Need cookies before extracting crumb")
            return False
        
        try:
            logger.info("Extracting crumb from Bandcamp page HTML...")
            
            # If we already have the HTML cached from extract_from_browser, use it
            if hasattr(self, '_cached_html') and self._cached_html:
                html_text = self._cached_html
            else:
                return False
            
            # Parse HTML
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Method 1: Look for data-crumb attribute
            crumb_elem = soup.find(attrs={'data-crumb': True})
            if crumb_elem:
                self.crumb = crumb_elem.get('data-crumb')
                logger.info("✓ Found crumb in data-crumb attribute")
                return True
            
            # Method 2: Look in <script> tags for crumb variable
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for: var crumb = "...";
                    match = re.search(r'["\']crumb["\']\s*:\s*["\']([^"\']+)["\']', script.string)
                    if match:
                        self.crumb = match.group(1)
                        logger.info("✓ Found crumb in script tag")
                        return True
                    
                    # Look for: crumb: "..."
                    match = re.search(r'crumb\s*:\s*["\']([^"\']+)["\']', script.string)
                    if match:
                        self.crumb = match.group(1)
                        logger.info("✓ Found crumb in script tag (alt format)")
                        return True
            
            # Method 3: Look in page source directly
            match = re.search(r'&quot;crumb&quot;:&quot;([^&]+)&quot;', html_text)
            if match:
                self.crumb = match.group(1)
                logger.info("✓ Found crumb in page source directly")
                return True
                
            # Method 4: Look in un-escaped page source
            match = re.search(r'["\']crumb["\']\s*:\s*["\']([^"\']+)["\']', html_text)
            if match:
                self.crumb = match.group(1)
                logger.info("✓ Found crumb in page source")
                return True
            
            logger.warning("Could not find crumb in page")
            return False
        
        except Exception as e:
            logger.error(f"Error extracting crumb: {e}")
            return False
    
    def auto_extract(self, browser_name: Optional[str] = None) -> Tuple[bool, Dict[str, str]]:
        """Automatically extract all credentials.
        
        Args:
            browser_name: Browser to use (None for auto-detect)
        
        Returns:
            Tuple of (success, credentials_dict)
        """
        logger.info("Starting auto-extraction of credentials...")
        
        # Step 1: Extract cookies from browser
        if not self.extract_from_browser(browser_name):
            return False, {}
        
        # Step 2: Extract crumb from page
        if not self.extract_crumb_from_page():
            logger.warning("Could not extract crumb, but cookies are available")
            # Return cookies even if crumb extraction failed
        
        credentials = {
            'client_id': self.client_id or '',
            'session': self.session or '',
            'crumb': self.crumb or '',
        }
        
        success = bool(self.client_id and self.session)
        
        if success:
            logger.info("✓ Auto-extraction completed successfully!")
            if self.crumb:
                logger.info("  - client_id: " + self.client_id[:20] + "...")
                logger.info("  - session: " + self.session[:20] + "...")
                logger.info("  - crumb: " + self.crumb[:20] + "...")
            else:
                logger.info("  - client_id: " + self.client_id[:20] + "...")
                logger.info("  - session: " + self.session[:20] + "...")
                logger.warning("  - crumb: (not found, may need manual input)")
        
        return success, credentials
    
    @classmethod
    def get_credentials(cls, browser_name: Optional[str] = None) -> Dict[str, str]:
        """Quick method to get credentials.
        
        Args:
            browser_name: Browser to use (None for auto-detect)
        
        Returns:
            Dictionary with credentials
        """
        extractor = cls()
        success, credentials = extractor.auto_extract(browser_name)
        return credentials if success else {}


def test_extraction():
    """Test credential extraction."""
    print("=" * 60)
    print("Testing Bandcamp Credential Auto-Extraction")
    print("=" * 60)
    
    extractor = CredentialExtractor()
    success, creds = extractor.auto_extract()
    
    if success:
        print("\n✓ SUCCESS!")
        print(f"  Client ID: {creds.get('client_id', '')[:30]}...")
        print(f"  Session:   {creds.get('session', '')[:30]}...")
        print(f"  Crumb:     {creds.get('crumb', '')[:50]}...")
    else:
        print("\n✗ FAILED")
        print("  Make sure you have:")
        print("  1. browser-cookie3 installed: pip install browser-cookie3")
        print("  2. Logged into Bandcamp in your browser")
        print("  3. Visited https://bandcamp.com/yum at least once")
    
    print("=" * 60)


if __name__ == "__main__":
    test_extraction()
