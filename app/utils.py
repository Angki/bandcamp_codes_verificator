"""
Utility functions for Bandcamp Code Verificator.
"""

import re
import csv
import json
import secrets
from pathlib import Path
from typing import List, Dict, Any, Optional


def sanitize_codes(raw_text: str, max_length: int = 256) -> List[str]:
    """Sanitize and parse codes from raw text input.
    
    Args:
        raw_text: Raw text containing codes (one per line)
        max_length: Maximum allowed length for each code
    
    Returns:
        List of sanitized codes
    """
    # Normalize line endings
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split by lines and filter
    lines = raw_text.split("\n")
    codes = []
    
    for line in lines:
        code = line.strip()
        if not code:  # Skip empty lines
            continue
        
        # Truncate if too long
        if len(code) > max_length:
            code = code[:max_length]
        
        codes.append(code)
    
    return codes


def sanitize_cookie_value(value: str, max_length: int) -> str:
    """Sanitize cookie value to prevent header injection.
    
    Args:
        value: Cookie value to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized cookie value
    """
    # Remove CR/LF and semicolons
    value = value.strip()
    value = value.replace("\r", "").replace("\n", "")
    value = value.replace(";", "")
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def read_codes_from_file(file_path: str) -> List[str]:
    """Read codes from a text file.
    
    Args:
        file_path: Path to the text file
    
    Returns:
        List of codes
    
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return sanitize_codes(content)


def write_results_to_csv(results: List[Dict[str, Any]], output_path: str):
    """Write verification results to CSV file.
    
    Args:
        results: List of result dictionaries
        output_path: Path to output CSV file
    """
    if not results:
        return
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Define CSV columns
    fieldnames = ["no", "code", "http_status", "delay_sec", "elapsed_ms", "response", "success"]
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for idx, result in enumerate(results, 1):
            # Format response body
            body = result.get("body", "")
            if isinstance(body, dict):
                body = json.dumps(body)
            
            writer.writerow({
                "no": idx,
                "code": result.get("code", ""),
                "http_status": result.get("status", 0),
                "delay_sec": result.get("delay_sec", 0),
                "elapsed_ms": result.get("elapsed_ms", 0),
                "response": str(body),
                "success": result.get("success", False),
            })


def write_results_to_json(results: List[Dict[str, Any]], output_path: str):
    """Write verification results to JSON file.
    
    Args:
        results: List of result dictionaries
        output_path: Path to output JSON file
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": len(results),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def generate_csrf_token() -> str:
    """Generate a secure CSRF token.
    
    Returns:
        Random hex token
    """
    return secrets.token_hex(32)


def validate_input(
    code: Optional[str] = None,
    crumb: Optional[str] = None,
    client_id: Optional[str] = None,
    session: Optional[str] = None,
    max_crumb_len: int = 512,
    max_client_id_len: int = 128,
    max_session_len: int = 4096,
) -> Dict[str, str]:
    """Validate input parameters.
    
    Args:
        code: Download code
        crumb: API crumb
        client_id: Client ID cookie
        session: Session cookie
        max_crumb_len: Maximum crumb length
        max_client_id_len: Maximum client_id length
        max_session_len: Maximum session length
    
    Returns:
        Dictionary with validation errors (empty if valid)
    """
    errors = {}
    
    if code is not None and not code.strip():
        errors["code"] = "Code cannot be empty"
    
    if crumb is not None:
        if not crumb.strip():
            errors["crumb"] = "Crumb cannot be empty"
        elif len(crumb) > max_crumb_len:
            errors["crumb"] = f"Crumb too long (max {max_crumb_len})"
    
    if client_id is not None:
        if not client_id.strip():
            errors["client_id"] = "Client ID cannot be empty"
        elif len(client_id) > max_client_id_len:
            errors["client_id"] = f"Client ID too long (max {max_client_id_len})"
    
    if session is not None:
        if not session.strip():
            errors["session"] = "Session cannot be empty"
        elif len(session) > max_session_len:
            errors["session"] = f"Session too long (max {max_session_len})"
    
    return errors


def format_elapsed_time(ms: float) -> str:
    """Format elapsed time for display.
    
    Args:
        ms: Time in milliseconds
    
    Returns:
        Formatted string (e.g., "1.23s" or "523ms")
    """
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{int(ms)}ms"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string for display.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated string with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
