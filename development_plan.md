# Bandcamp Code Verificator - Development Plan

This document outlines the roadmap and future ideas for extending the Bandcamp Code Verificator system. The core architecture has recently transitioned from standard HTTP requests to full Headless Browser Automation (Playwright) to guarantee continuous circumvention of advanced WAFs like Fastly.

## 1. Short-Term Enhancements

### Pluggable Browser Automation
- **Multi-Browser Support**: Expand Playwright support beyond Chromium (Firefox, WebKit) to rotate fingerprints.
- **Proxy Rotation**: Build a robust proxy rotation feature inside the Playwright context to distribute verification loads.
- **Headless Toggle**: Add a configuration option to toggle Headless mode in `app/config.py` for easier user debugging.
- **Concurrent Processing**: The current Playwright integration is synchronous (blocks until the browser finishes). Migrate the queue logic to `asyncio` (`playwright.async_api`) to permit highly rapid, parallel verifications across multiple isolated tabs/contexts.

## 2. Mid-Term Architectural Upgrades

### Database Storage
- **SQLAlchemy / SQLite**: Replace the CSV log output with a formal SQL database. Keep track of verified codes with more metadata (date uploaded, album name if available, user session used).
- **Web UI History**: Provide a "History" tab in the Flask UI to review previous batch scans without checking manual CSV logs.

### Verification Metadata Enrichment
- **Album / Artist Polling**: When a code returns an HTTP 200 `verified` success message, the application could transition the Chromium tab to the download page and scrape the Artist Name, Album Name, and Album Art to enrich the verification output with actual music metadata.

## 3. Long-Term / Enterprise Ideas

### Multi-User / SaaS Capability
- **User Accounts**: Wrap the Flask frontend with standard user authentication.
- **Session Isolation**: Store browser cookies (`client_id`, `session`, `identity`) inside the Database, encrypted per-user. This ensures every user gets their own Playwright browser context.

### Fully Automated Auto-Extraction
- Automatically extract cookies natively via Playwright extensions or a customized Chrome Extension, bypassing the need for `browser-cookie3` which is often unreliable because of SQLite locks on Windows.

### API Orchestration
- Create a set of structured REST endpoints (`FastAPI` or Flask) to allow external applications to ping the Verificator system programmatically, queue a code, and receive a webhook callback when the Headless browser finishes rendering the checkmark.
