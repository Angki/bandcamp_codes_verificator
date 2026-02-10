# Bandcamp Code Verificator 🎵

A professional Python system for verifying Bandcamp download codes with both CLI and web interfaces.

## ✨ Features

- **🖥️ CLI Interface** - Command-line tool with rich progress bars and colored output
- **🌐 Web Interface** - Modern Flask-based web UI with real-time AJAX updates
- **📊 Batch Processing** - Verify multiple codes from text files
- **⏱️ Rate Limiting** - Configurable delays (1-5 seconds) to respect API limits
- **🔐 Security** - CSRF protection, session management, input sanitization
- **📝 Logging** - Comprehensive JSON-formatted logs with rotation
- **📥 Export** - Save results in CSV or JSON format
- **🎨 Modern UI** - Beautiful gradient design with responsive layout
- **🔄 Progress Tracking** - Real-time progress bars and status updates
- **🛡️ Error Handling** - Robust retry logic and error recovery

## 📋 Requirements

- Python 3.8 or higher
- Internet connection
- Valid Bandcamp session cookies

## 🚀 Installation

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🎯 Usage

### Web Interface

1. **Start the web server**
   ```bash
   python -m app.web.app
   ```

2. **Open browser**
   Navigate to `http://127.0.0.1:5000`

3. **Enter credentials**
   - Paste your download codes (one per line)
   - Add your `crumb`, `client_id`, and `session` values from browser cookies
   - Click "Start Verification"

4. **Export results**
   Click "Export CSV" when verification is complete

### CLI Interface

**Basic usage**
```bash
python cli.py verify --input codes.txt --output results.csv
```

**With credentials provided**
```bash
python cli.py verify \
  --input codes.txt \
  --crumb "|api/codes/1/verify|1759468523|HTNmuiFhDBD3w..." \
  --client-id "2F468B341CC6977..." \
  --session "1%09r%3A%5B%22...%22%5D..." \
  --output results.csv
```

**JSON output**
```bash
python cli.py verify --input codes.txt --output results.json --format json
```

**Verbose mode**
```bash
python cli.py verify --input codes.txt --output results.csv --verbose
```

**Dry run (test without verifying)**
```bash
python cli.py verify --input codes.txt --output results.csv --dry-run
```

## 🔑 Getting Credentials

To use this tool, you need to extract the following values from your browser while logged into Bandcamp:

1. **Open Bandcamp** in your browser and log in
2. **Go to** `https://bandcamp.com/yum` (download codes page)
3. **Open Developer Tools** (F12)
4. **Go to Network tab**
5. **Try verifying a code** manually
6. **Find the `/verify` request** in the Network tab
7. **Extract:**
   - **crumb**: From request payload
   - **client_id**: From cookies
   - **session**: From cookies

## 📁 Project Structure

```
bandcamp_codes_verificator/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration settings
│   ├── verificator.py        # Core verification logic
│   ├── logger.py             # Logging utilities
│   ├── utils.py              # Helper functions
│   └── web/
│       ├── __init__.py
│       ├── app.py            # Flask application
│       └── templates/
│           └── index.html    # Web UI
├── cli.py                    # CLI entry point
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── .gitignore               # Git ignore rules
└── tests/
    └── sample_codes.txt      # Sample test file
```

## ⚙️ Configuration

Edit `app/config.py` to customize:

- **Rate limiting**: `MIN_DELAY_SEC`, `MAX_DELAY_SEC`
- **API settings**: `VERIFY_URL`, `TIMEOUT`
- **Limits**: `MAX_CODES`, `MAX_CODE_LENGTH`
- **Logging**: `LOG_FILE`, `LOG_FORMAT`, `LOG_LEVEL`

Or use environment variables:
```bash
export MIN_DELAY_SEC=2
export MAX_DELAY_SEC=10
```

## 📊 Output Formats

### CSV Format
```csv
no,code,http_status,delay_sec,elapsed_ms,response,success
1,XXXX-YYYY-ZZZZ,200,3,2450,"{""ok"":true,...}",True
```

### JSON Format
```json
{
  "total": 10,
  "results": [
    {
      "code": "XXXX-YYYY-ZZZZ",
      "status": 200,
      "delay_sec": 3,
      "elapsed_ms": 2450,
      "body": {...},
      "success": true
    }
  ]
}
```

## 🔒 Security Notes

- **Never share** your `session` or `client_id` cookies
- **Don't commit** configuration files with real credentials
- **Use HTTPS** when deploying the web interface
- **Keep logs private** - they may contain sensitive data

## 🐛 Troubleshooting

**"Invalid CSRF token" error**
- Clear browser cookies and restart the web server

**"Request timeout" errors**
- Increase `TIMEOUT` in `config.py`
- Check your internet connection

**"Rate limit exceeded"**
- The tool already implements delays, but you may need to increase them
- Wait a few minutes before retrying

**Codes show as invalid**
- Verify your credentials are correct and from an active session
- Check that cookies haven't expired

## 📝 Logging

Logs are saved to `verificator.log` in JSON format:

```json
{
  "timestamp": "2024-02-11T03:15:00Z",
  "level": "INFO",
  "event": "verify",
  "code": "XXXX-YYYY-ZZZZ",
  "status": 200,
  "success": true,
  "elapsed_ms": 2450,
  "delay_sec": 3
}
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ⚠️ Disclaimer

This tool is for personal use only. Please respect Bandcamp's Terms of Service and don't abuse their API. Use reasonable rate limits and delays.

## 📄 License

MIT License - feel free to use and modify as needed.

## 🙏 Acknowledgments

Based on original PHP implementation. Converted to Python for better portability and extensibility.

---

**Made with ❤️ for Bandcamp users**
