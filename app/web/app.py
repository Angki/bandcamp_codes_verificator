"""
Flask web application for Bandcamp Code Verificator.
"""

import os
import secrets
from flask import Flask, render_template, request, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config
from app.verificator import BandcampVerificator
from app.logger import logger
from app.utils import sanitize_codes, validate_input, generate_csrf_token
from app.auto_extract import CredentialExtractor


def create_app():
    """Create and configure Flask application.
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Configuration
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    
    # Session configuration
    app.config["SESSION_COOKIE_SECURE"] = Config.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = Config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = Config.SESSION_COOKIE_SAMESITE
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )
    
    # Store verificators (keyed by session ID)
    verificators = {}
    
    @app.route("/")
    def index():
        """Render main page."""
        # Generate CSRF token
        if "csrf_token" not in session:
            session["csrf_token"] = generate_csrf_token()
        
        return render_template(
            "index.html",
            csrf_token=session["csrf_token"],
            max_codes=Config.MAX_CODES,
            min_delay=Config.MIN_DELAY_SEC,
            max_delay=Config.MAX_DELAY_SEC,
            has_credentials=Config.has_credentials(),
        )
    
    @app.route("/api/verify", methods=["POST"])
    @limiter.limit("10 per minute")
    def verify_code():
        """API endpoint to verify a single code."""
        # Check CSRF
        if Config.CSRF_ENABLED:
            csrf_token = request.json.get("csrf_token")
            if not csrf_token or csrf_token != session.get("csrf_token"):
                return jsonify({"ok": False, "error": "Invalid CSRF token"}), 419
        
        # Get request data
        code = request.json.get("code", "")
        
        # Use credentials from config if available, otherwise from request
        crumb = request.json.get("crumb", "") or Config.BANDCAMP_CRUMB
        client_id = request.json.get("client_id", "") or Config.BANDCAMP_CLIENT_ID
        session_val = request.json.get("session", "") or Config.BANDCAMP_SESSION
        
        index = request.json.get("index", 0)
        total = request.json.get("total", 1)
        
        # Validate inputs
        errors = validate_input(
            code=code,
            client_id=client_id,
            session=session_val,
        )
        
        if errors:
            return jsonify({"ok": False, "error": f"Validation failed: {errors}"}), 400
        
        try:
            # Create or reuse verificator
            session_id = session.get("session_id")
            if not session_id:
                session_id = secrets.token_hex(16)
                session["session_id"] = session_id
            
            # Check if we need to create a new verificator
            verificator_key = f"{session_id}_{crumb}_{client_id}"
            identity = getattr(Config, "BANDCAMP_IDENTITY", "")
            
            if verificator_key not in verificators:
                verificators[verificator_key] = BandcampVerificator(
                    crumb=crumb,
                    client_id=client_id,
                    session=session_val,
                    identity=identity,
                )
            
            verificator = verificators[verificator_key]
            verificator.last_used = time.time() # Update last used timestamp
            
            # Verify the code
            result = verificator.verify_code(code, index=index, total=total)
            
            # Return result
            return jsonify({
                "ok": result["ok"],
                "status": result["status"],
                "delay_sec": result["delay_sec"],
                "elapsed_ms": result["elapsed_ms"],
                "body": result["body"],
                "error": result.get("error"),
            })
        
        except ValueError as e:
            logger.error(f"Verification error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 400
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({"ok": False, "error": "Internal server error"}), 500
    
    @app.route("/api/auto-extract", methods=["POST"])
    @limiter.limit("5 per minute")
    def auto_extract_credentials():
        """API endpoint to auto-extract credentials from browser."""
        # Check CSRF
        if Config.CSRF_ENABLED:
            csrf_token = request.json.get("csrf_token") if request.json else None
            if not csrf_token or csrf_token != session.get("csrf_token"):
                return jsonify({"ok": False, "error": "Invalid CSRF token"}), 419
        
        try:
            browser = request.json.get("browser") if request.json else None
            
            logger.info("Auto-extracting credentials from browser...")
            extractor = CredentialExtractor()
            success, credentials = extractor.auto_extract(browser)
            
            if success:
                return jsonify({
                    "ok": True,
                    "credentials": credentials,
                    "message": "Credentials extracted successfully!"
                })
            else:
                return jsonify({
                    "ok": False,
                    "error": "Could not extract credentials. Make sure you're logged into Bandcamp in your browser."
                }), 400
        
        except Exception as e:
            logger.error(f"Auto-extraction error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    @app.route("/api/health")
    def health():
        """Health check endpoint."""
        return jsonify({"status": "ok", "version": "1.0.0"})
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 errors."""
        logger.error(f"Internal error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit errors."""
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    return app


def run_server():
    """Run the Flask development server."""
    app = create_app()
    
    logger.info(f"Starting Flask server on {Config.HOST}:{Config.PORT}")
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
    )


if __name__ == "__main__":
    run_server()
