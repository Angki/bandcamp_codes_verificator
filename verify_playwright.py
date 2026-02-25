import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BANDCAMP_CLIENT_ID = os.environ.get("BANDCAMP_CLIENT_ID", "")
BANDCAMP_SESSION = os.environ.get("BANDCAMP_SESSION", "")
BANDCAMP_IDENTITY = os.environ.get("BANDCAMP_IDENTITY", "")

def verify_codes(codes_file: str, output_csv: str = "playwright_results.csv"):
    if not Path(codes_file).exists():
        print(f"Error: {codes_file} not found.")
        return

    with open(codes_file, 'r', encoding='utf-8') as f:
        codes = [line.strip() for line in f if line.strip()]

    if not codes:
        print("No codes found to verify.")
        return

    print(f"Loaded {len(codes)} codes. Launching browser...")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
        )

        cookies = [
            {"name": "client_id", "value": BANDCAMP_CLIENT_ID, "domain": ".bandcamp.com", "path": "/"},
            {"name": "session", "value": BANDCAMP_SESSION, "domain": ".bandcamp.com", "path": "/"},
            {"name": "identity", "value": BANDCAMP_IDENTITY, "domain": ".bandcamp.com", "path": "/"},
            {"name": "js_logged_in", "value": "1", "domain": ".bandcamp.com", "path": "/"}
        ]
        context.add_cookies(cookies)

        page = context.new_page()
        
        for idx, code in enumerate(codes, 1):
            print(f"[{idx}/{len(codes)}] Verifying {code}...")
            
            # Skenario 1: Load halaman yum dari awal untuk setiap kode 
            # untuk memastikan state selalu bersih
            page.goto("https://bandcamp.com/yum", wait_until="networkidle")
            
            api_status = 0
            api_body = {}
            is_valid_dom = False
            error_text = ""

            try:
                # Cari input element, pakai name="code" lebih aman dari ID
                input_locator = page.locator('input[name="code"]').first
                input_locator.wait_for(state="visible", timeout=10000)
                
                # Set active / focus ke textbox
                input_locator.focus()
                
                # Setup interceptor REST API verify post
                with page.expect_response(lambda r: "api/codes/1/verify" in r.url, timeout=10000) as response_info:
                    
                    # Masukkan kode
                    input_locator.fill(code)
                    
                    # Simulasikan tekan tombol tab agar keluar dari active textbox (memicu event validation JS)
                    page.keyboard.press("Tab")
                    
                # Baca response dari background API Bandcamp
                response = response_info.value
                api_status = response.status
                try:
                    api_body = response.json()
                except:
                    api_body = response.text()
                    
            except Exception as e:
                print(f"  -> Error / Timeout API Request: {e}")
            
            # Tunggu dan baca DOM sesuai permintaan User
            try:
                # Periksa apakah muncul check (berhasil) atau pesan error
                # div id="code-icon" class="bc-ui form-icon check"
                page.wait_for_selector(".bc-ui.form-icon.check:visible, .form-field-error:visible", timeout=3000)
                
                success_icon = page.locator(".bc-ui.form-icon.check").first
                error_el = page.locator(".form-field-error").first
                
                if success_icon.is_visible():
                    is_valid_dom = True
                elif error_el.is_visible():
                    is_valid_dom = False
                    error_text = error_el.inner_text().strip()
            except:
                pass
            
            print(f"  -> HTTP: {api_status} | DOM Ceklist: {is_valid_dom} | Error: {error_text}")
            
            results.append({
                "no": idx,
                "code": code,
                "http_status": api_status,
                "api_response": api_body,
                "dom_valid": is_valid_dom,
                "error_ui": error_text
            })
            
            time.sleep(1) # jeda kecil

        browser.close()

    # Save to CSV
    import csv
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["No", "Code", "HTTP Status", "DOM Valid", "UI Error", "API Response"])
        for r in results:
            writer.writerow([
                r["no"], r["code"], r["http_status"], 
                "Yes" if r["dom_valid"] else "No",
                r["error_ui"],
                json.dumps(r["api_response"])
            ])
            
    print(f"\nCompleted! Results saved to {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify Bandcamp codes via Playwright")
    parser.add_argument("codes_file", help="Path to text file containing codes")
    parser.add_argument("--output", "-o", default="playwright_results.csv", help="Output CSV file")
    args = parser.parse_args()
    
    verify_codes(args.codes_file, args.output)
