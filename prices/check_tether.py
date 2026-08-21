import urllib.request
import json
import re

url = 'https://api.tgju.org/v1/widget/live-data?lang=fa'
try:
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print(data.keys())
except Exception as e:
    print(f"Error 1: {e}")

url = 'https://www.tgju.org/profile/crypto-tether'
try:
    req = urllib.request.Request(url, headers={'Accept': 'text/html', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        
        matches = re.findall(r'data-price="([^"]+)"', html)
        for m in matches[:10]:
            if len(m) > 4:
                print('Price found in profile:', m)
except Exception as e:
    print(f"Error 2: {e}")
