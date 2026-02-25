"""
Core verification logic for Bandcamp Code Verificator.
"""

import time
import random
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin

import requests
import json
from urllib.parse import urljoin

from app.config import Config
from app.logger import logger
from app.utils import sanitize_cookie_value, validate_input


class BandcampVerificator:
    """Main verificator class for Bandcamp code verification."""
    
    def __init__(
        self,
        crumb: str,
        client_id: str,
        session: str,
        identity: Optional[str] = None,
        min_delay: Optional[int] = None,
        max_delay: Optional[int] = None,
    ):
        """Initialize verificator.
        
        Args:
            crumb: API crumb for authentication
            client_id: Client ID cookie value
            session: Session cookie value
            min_delay: Minimum delay between requests (default: from Config)
            max_delay: Maximum delay between requests (default: from Config)
        
        Raises:
            ValueError: If validation fails
        """
        # Auto-extract crumb if not provided
        if not crumb:
            from app.auto_extract import CredentialExtractor
            logger.info("Crumb not provided. Attempting to auto-extract from http://bandcamp.com/yum...")
            extractor = CredentialExtractor()
            extractor.client_id = client_id
            extractor.session = session
            extractor.identity = identity
            if extractor.extract_crumb_from_page():
                crumb = extractor.crumb
                logger.info("Successfully extracted crumb.")
            else:
                logger.warning("Failed to automatically extract crumb.")

        # Validate inputs
        errors = validate_input(
            crumb=crumb,
            client_id=client_id,
            session=session,
            max_crumb_len=Config.MAX_CRUMB_LENGTH,
            max_client_id_len=Config.MAX_CLIENT_ID_LENGTH,
            max_session_len=Config.MAX_SESSION_LENGTH,
        )
        
        if errors:
            raise ValueError(f"Validation errors: {errors}")
        
        self.crumb = crumb
        self.client_id = sanitize_cookie_value(client_id, Config.MAX_CLIENT_ID_LENGTH)
        self.session = sanitize_cookie_value(session, Config.MAX_SESSION_LENGTH)
        self.identity = identity or getattr(Config, "BANDCAMP_IDENTITY", "")
        self.min_delay = min_delay or Config.MIN_DELAY_SEC
        self.max_delay = max_delay or Config.MAX_DELAY_SEC
        
        # Initialize Playwright Browser session
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self._init_browser()
        
        logger.info("BandcampVerificator initialized with Playwright")
    
    def _init_browser(self):
        """Initialize Playwright and navigate to Bandcamp."""
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        
        self.browser = self.pw.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent=Config.USER_AGENT
        )
        
        # Inject required cookies
        cookies = [
            {"name": "client_id", "value": self.client_id, "domain": ".bandcamp.com", "path": "/"},
            {"name": "session", "value": self.session, "domain": ".bandcamp.com", "path": "/"},
            {"name": "js_logged_in", "value": "1", "domain": ".bandcamp.com", "path": "/"}
        ]
        if self.identity:
            cookies.append({"name": "identity", "value": self.identity, "domain": ".bandcamp.com", "path": "/"})
            
        self.context.add_cookies(cookies)
        self.page = self.context.new_page()
        
        # Preload the YUM page to be ready for verifications
        self.page.goto("https://bandcamp.com/yum", wait_until="networkidle")
        
    def close(self):
        """Clean up the browser instance."""
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    
    
    def verify_code(
        self,
        code: str,
        index: int = 0,
        total: int = 1,
    ) -> Dict[str, Any]:
        """Verify a single Bandcamp code.
        
        Args:
            code: The download code to verify
            index: Index of this code in batch (for logging)
            total: Total codes in batch (for logging)
        
        Returns:
            Dictionary with verification results:
            {
                "ok": bool,
                "status": int,
                "delay_sec": int,
                "elapsed_ms": float,
                "body": dict or str,
                "error": str or None,
                "code": str,
                "success": bool,
            }
        """
        start_time = time.time()
        
        # Validate code
        errors = validate_input(code=code)
        if errors:
            return {
                "ok": False,
                "status": 0,
                "delay_sec": 0,
                "elapsed_ms": 0,
                "body": None,
                "error": f"Invalid code: {errors.get('code')}",
                "code": code,
                "success": False,
            }
        
        # Apply random delay (rate limiting) BEFORE action
        delay = random.randint(self.min_delay, self.max_delay)
        time.sleep(delay)
        
        try:
            # Ensure we are on the page
            if "bandcamp.com/yum" not in self.page.url:
                self.page.goto("https://bandcamp.com/yum", wait_until="networkidle")
                
            input_locator = self.page.locator('input[name="code"]').first
            input_locator.wait_for(state="visible", timeout=10000)
            
            input_locator.focus()
            
            api_status = 0
            api_body = {}
            is_valid_dom = False
            
            with self.page.expect_response(lambda r: "api/codes/1/verify" in r.url, timeout=15000) as response_info:
                input_locator.fill(code)
                self.page.keyboard.press("Tab")
                
            response = response_info.value
            api_status = response.status
            try:
                api_body = response.json()
            except:
                api_body = response.text()
                
            # Wait for visual checkmark just in case
            try:
                self.page.wait_for_selector(".bc-ui.form-icon.check:visible", timeout=1500)
                is_valid_dom = True
            except:
                is_valid_dom = False
                
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Determine success (API gives 200 regardless of already_redeemed, so check JSON for errors if 200)
            ok = (200 <= api_status < 300)
            success_payload = ok
            if isinstance(api_body, dict) and api_body.get('errors'):
                success_payload = False

            # Log the verification
            logger.log_verification(
                code=code,
                status=api_status,
                success=success_payload,
                index=index,
                total=total,
                elapsed_ms=elapsed_ms,
                delay_sec=delay,
                error=api_body.get('errors', [{}])[0].get('reason') if isinstance(api_body, dict) and api_body.get('errors') else None,
            )
            
            return {
                "ok": ok,
                "status": api_status,
                "delay_sec": delay,
                "elapsed_ms": elapsed_ms,
                "body": api_body,
                "error": None if success_payload else (api_body.get('errors', [{}])[0].get('reason') if isinstance(api_body, dict) and api_body.get('errors') else f"HTTP {api_status}"),
                "code": code,
                "success": success_payload,
            }
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error = f"Browser automation error: {str(e)}"
            
            logger.log_verification(
                code=code,
                status=0,
                success=False,
                index=index,
                total=total,
                elapsed_ms=elapsed_ms,
                delay_sec=delay,
                error=error,
            )
            
            return {
                "ok": False,
                "status": 0,
                "delay_sec": delay,
                "elapsed_ms": elapsed_ms,
                "body": None,
                "error": error,
                "code": code,
                "success": False,
            }
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error = f"Request error: {str(e)}"
            
            logger.log_verification(
                code=code,
                status=0,
                success=False,
                index=index,
                total=total,
                elapsed_ms=elapsed_ms,
                delay_sec=delay,
                error=error,
            )
            
            return {
                "ok": False,
                "status": 0,
                "delay_sec": delay,
                "elapsed_ms": elapsed_ms,
                "body": None,
                "error": error,
                "code": code,
                "success": False,
            }
    
    def verify_batch(
        self,
        codes: List[str],
        progress_callback: Optional[callable] = None,
        stop_flag: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """Verify a batch of codes.
        
        Args:
            codes: List of codes to verify
            progress_callback: Optional callback(current, total, result) for progress
            stop_flag: Optional callback() that returns True to stop processing
        
        Returns:
            List of verification results
        """
        results = []
        total = len(codes)
        
        logger.info(f"Starting batch verification of {total} codes")
        
        for idx, code in enumerate(codes):
            # Check stop flag
            if stop_flag and stop_flag():
                logger.info(f"Batch verification stopped by user at {idx}/{total}")
                break
            
            # Verify code
            result = self.verify_code(code, index=idx, total=total)
            results.append(result)
            
            # Call progress callback
            if progress_callback:
                progress_callback(idx + 1, total, result)
        
        logger.info(f"Batch verification completed: {len(results)}/{total} codes processed")
        
        return results
    
    def close(self):
        """Close HTTP session."""
        if self.http_session:
            self.http_session.close()
            logger.info("HTTP session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
