import urllib.parse
import requests
import re

client_id = '2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772'
session_raw = '1%09r%3A%5B%22nilZ0c0x1772042139%22%2C%22374859956a1577887883c0x1772041658%22%2C%22324224306a3163526261a1577887883x1772041641%22%5D%09t%3A1772041244%09bp%3A1'

def test(sess):
    s = requests.Session()
    s.cookies.set('client_id', client_id, domain='.bandcamp.com')
    s.cookies.set('session', sess, domain='.bandcamp.com')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }
    r = s.get('https://bandcamp.com/yum', headers=headers, timeout=10)
    print('status:', r.status_code)
    
    crumb_elem = re.search(r'data-crumb=["\']([^"\']+)["\']', r.text)
    if crumb_elem:
        print('crumb:', crumb_elem.group(1))
    else:
        print('crumb not found in HTML data-crumb attr')
        
    scripts = r.text
    match1 = re.search(r'["\']crumb["\']\s*:\s*["\']([^"\']+)["\']', scripts)
    match2 = re.search(r'crumb\s*:\s*["\']([^"\']+)["\']', scripts)
    if match1:
        print('crumb_match1:', match1.group(1))
    elif match2:
        print('crumb_match2:', match2.group(1))
    
    print('login status text snippet:', r.text[:200].replace('\n', ' '))
    if "Log in" in r.text:
        print('Warning: page says Log in')

print('testing unquote:')
test(urllib.parse.unquote(session_raw))
print('\n=================\n')
print('testing raw:')
test(session_raw)
