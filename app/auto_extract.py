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
    
    def extract_from_browser(self, browser_name: Optional[str] = None) -> bool:
        """Extract cookies from browser.
        
        Args:
            browser_name: Browser to use ('chrome', 'firefox', 'edge', or None for auto-detect)
        
        Returns:
            True if successful
        """
        if not BROWSER_COOKIE_AVAILABLE:
            logger.warning("browser_cookie3 not installed. Run: pip install browser-cookie3")
            return False
        
        browsers = {
            'chrome': browser_cookie3.chrome,
            'firefox': browser_cookie3.firefox,
            'edge': browser_cookie3.edge,
            'chromium': browser_cookie3.chromium,
        }
        
        # Try specified browser or all browsers
        to_try = [browser_name] if browser_name and browser_name in browsers else browsers.keys()
        
        for browser in to_try:
            try:
                logger.info(f"Trying to extract cookies from {browser}...")
                
                # Get cookies
                jar = browsers[browser](domain_name=self.BANDCAMP_DOMAIN)
                
                # Extract client_id, session, and identity
                for cookie in jar:
                    if cookie.name == 'client_id':
                        self.client_id = cookie.value
                    elif cookie.name == 'session':
                        self.session = cookie.value
                    elif cookie.name == 'identity':
                        self.identity = cookie.value
                
                if self.client_id and self.session and self.identity:
                    logger.info(f"✓ Successfully extracted cookies from {browser}")
                    return True
            
            except Exception as e:
                logger.debug(f"Failed to extract from {browser}: {e}")
                continue
        
        logger.warning("Could not extract cookies from any browser")
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
            logger.info("Extracting crumb from Bandcamp page using Playwright...")
            from playwright.sync_api import sync_playwright
            
            html_text = ""
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
                )
                
                cookies = [
                    {"name": "client_id", "value": self.client_id, "domain": ".bandcamp.com", "path": "/"},
                    {"name": "session", "value": self.session, "domain": ".bandcamp.com", "path": "/"},
                    {"name": "js_logged_in", "value": "1", "domain": ".bandcamp.com", "path": "/"}
                ]
                if hasattr(self, 'identity') and self.identity:
                    cookies.append({"name": "identity", "value": self.identity, "domain": ".bandcamp.com", "path": "/"})
                    
                context.add_cookies(cookies)
                page = context.new_page()
                
                try:
                    page.goto(self.BANDCAMP_YUM_URL, wait_until="networkidle", timeout=15000)
                    html_text = page.content()
                except Exception as e:
                    logger.warning(f"Playwright navigation failed: {e}")
                    return False
                finally:
                    browser.close()
            
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
