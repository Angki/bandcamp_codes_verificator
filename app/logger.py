"""
Logging utilities for Bandcamp Code Verificator.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

from app.config import Config


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if available
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class VerificatorLogger:
    """Logger for verification operations."""
    
    def __init__(self, name: str = "verificator", log_file: Optional[str] = None):
        """Initialize logger.
        
        Args:
            name: Logger name
            log_file: Path to log file (uses Config.LOG_FILE if not provided)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Avoid adding handlers multiple times
        if not self.logger.handlers:
            self._setup_handlers(log_file or Config.LOG_FILE)
    
    def _setup_handlers(self, log_file: str):
        """Set up file and console handlers."""
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        
        if Config.LOG_FORMAT == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s: %(message)s")
        )
        self.logger.addHandler(console_handler)
    
    def log_verification(
        self,
        code: str,
        status: int,
        success: bool,
        index: int,
        total: int,
        elapsed_ms: float,
        delay_sec: int,
        ip: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log a verification attempt.
        
        Args:
            code: The code being verified
            status: HTTP status code
            success: Whether verification was successful
            index: Code index in batch
            total: Total codes in batch
            elapsed_ms: Elapsed time in milliseconds
            delay_sec: Delay applied in seconds
            ip: Client IP address
            error: Error message if any
        """
        extra_data = {
            "event": "verify",
            "code": code,
            "status": status,
            "success": success,
            "index": index,
            "total": total,
            "elapsed_ms": elapsed_ms,
            "delay_sec": delay_sec,
        }
        
        if ip:
            extra_data["ip"] = ip
        
        if error:
            extra_data["error"] = error
        
        # Create a log record with extra data
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO if success else logging.WARNING,
            __file__,
            0,
            f"Code verification: {code[:20]}... - Status: {status}",
            (),
            None,
        )
        record.extra_data = extra_data
        self.logger.handle(record)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra={"extra_data": kwargs} if kwargs else {})
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra={"extra_data": kwargs} if kwargs else {})
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra={"extra_data": kwargs} if kwargs else {})
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra={"extra_data": kwargs} if kwargs else {})


# Global logger instance
logger = VerificatorLogger()
