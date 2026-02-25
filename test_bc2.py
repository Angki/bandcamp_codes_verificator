import subprocess
import re
import json
import html

cmd = [
    'curl.exe', '-s',
    '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    '-b', 'client_id=2F468B341CC6977036E49EBB0B6BB3A621721E8E7ED18615503DB5745B1D7772; session=1%09r%3A%5B%22nilZ0c0x1772042139%22%2C%22374859956a1577887883c0x1772041658%22%2C%22324224306a3163526261a1577887883x1772041641%22%5D%09t%3A1772041244%09bp%3A1',
    'https://bandcamp.com'
]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
html_text = res.stdout

m_blob = re.search(r'data-blob=(["\'])(.*?)\1', html_text)
if m_blob:
    try:
        data = json.loads(html.unescape(m_blob.group(2)))
        print('crumb from data-blob:', data.get('identities', {}).get('crumb'))
    except Exception as e:
        print('data-blob error:', e)

m_crumb = re.search(r'&quot;crumb&quot;:&quot;([^&]+)&quot;', html_text)
if m_crumb:
    print('crumb regex:', m_crumb.group(1))
    
m_identities = re.search(r'&quot;identities&quot;:\{&quot;crumb&quot;:&quot;([^&]+)&quot;', html_text)
if m_identities:
    print('identities regex:', m_identities.group(1))

m_script = re.search(r'["\']crumb["\']\s*:\s*["\']([^"\']+)["\']', html_text)
if m_script:
    print('script regex:', m_script.group(1))
