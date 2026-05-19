import os
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()
ck = os.getenv("MPESA_CONSUMER_KEY")
cs = os.getenv("MPESA_CONSUMER_SECRET")

url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

try:
    r = requests.get(url, auth=HTTPBasicAuth(ck, cs), timeout=30)
    if r.status_code == 200:
        token = r.json().get("access_token")
        print(f"  [OK] M-Pesa credentials valid")
        print(f"  [OK] Token: {token[:25]}...")
    else:
        print(f"  [FAIL] Status: {r.status_code}")
        print(f"  [FAIL] Response: {r.json()}")
except Exception as e:
    print(f"  [ERROR] {e}")
