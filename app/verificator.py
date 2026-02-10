"""
Core verification logic for Bandcamp Code Verificator.
"""

import time
import random
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self.min_delay = min_delay or Config.MIN_DELAY_SEC
        self.max_delay = max_delay or Config.MAX_DELAY_SEC
        
        # Initialize HTTP session
        self.http_session = self._create_session()
        
        logger.info("BandcampVerificator initialized")
    
    def _create_session(self) -> requests.Session:
        """Create and configure HTTP session with retry logic.
        
        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://bandcamp.com",
            "Referer": "https://bandcamp.com/yum",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": Config.USER_AGENT,
        })
        
        # Set cookies
        session.cookies.set("client_id", self.client_id, domain=".bandcamp.com")
        session.cookies.set("session", self.session, domain=".bandcamp.com")
        
        return session
    
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
        
        # Apply random delay (rate limiting)
        delay = random.randint(self.min_delay, self.max_delay)
        time.sleep(delay)
        
        # Prepare payload
        payload = {
            "is_corp": True,
            "band_id": None,
            "platform_closed": False,
            "hard_to_download": False,
            "fan_logged_in": True,
            "band_url": None,
            "was_logged_out": None,
            "is_https": True,
            "ref_url": None,
            "code": code.strip(),
            "crumb": self.crumb,
        }
        
        try:
            # Make API request
            response = self.http_session.post(
                Config.VERIFY_URL,
                json=payload,
                timeout=Config.TIMEOUT,
            )
            
            # Calculate elapsed time
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Parse response
            status_code = response.status_code
            
            try:
                body = response.json()
            except ValueError:
                body = response.text
            
            # Determine success
            ok = 200 <= status_code < 300
            
            # Log the verification
            logger.log_verification(
                code=code,
                status=status_code,
                success=ok,
                index=index,
                total=total,
                elapsed_ms=elapsed_ms,
                delay_sec=delay,
                error=None if ok else f"HTTP {status_code}",
            )
            
            return {
                "ok": ok,
                "status": status_code,
                "delay_sec": delay,
                "elapsed_ms": elapsed_ms,
                "body": body,
                "error": None if ok else f"HTTP {status_code}",
                "code": code,
                "success": ok,
            }
        
        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start_time) * 1000
            error = f"Request timeout after {Config.TIMEOUT}s"
            
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
        
        except requests.exceptions.RequestException as e:
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
