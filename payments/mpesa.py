"""
M-Pesa Daraja API STK Push Service
"""
import os
import base64
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth


class MpesaService:
    def __init__(self):
        self.environment = os.getenv("MPESA_ENVIRONMENT", "sandbox")
        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.shortcode = os.getenv("MPESA_SHORTCODE", "174379")
        self.passkey = os.getenv("MPESA_PASSKEY")
        self.callback_url = os.getenv("MPESA_CALLBACK_URL")

        if self.environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"

    def get_access_token(self):
        """Get OAuth access token from Safaricom"""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
                timeout=30
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            print(f"[MPESA] Token acquired: {token[:20]}...")
            return token
        except Exception as e:
            print(f"[MPESA] Error getting token: {e}")
            return None

    def format_phone(self, phone):
        """Convert phone to 254XXXXXXXXX format"""
        phone = str(phone).strip().replace("+", "").replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif phone.startswith("7") or phone.startswith("1"):
            phone = "254" + phone
        elif not phone.startswith("254"):
            phone = "254" + phone
        return phone

    def stk_push(self, phone, amount, account_reference, description="Deposit"):
        """Initiate STK Push to customer phone"""
        access_token = self.get_access_token()
        if not access_token:
            return {"success": False, "error": "Failed to authenticate with Safaricom"}

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        formatted_phone = self.format_phone(phone)

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": self.shortcode,
            "PhoneNumber": formatted_phone,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": description[:13]
        }

        print(f"[MPESA STK] Sending to {formatted_phone}, Amount: {amount}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            print(f"[MPESA STK] Response: {data}")

            if data.get("ResponseCode") == "0":
                return {
                    "success": True,
                    "checkout_request_id": data.get("CheckoutRequestID"),
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "message": data.get("CustomerMessage"),
                    "response_code": data.get("ResponseCode")
                }
            else:
                return {
                    "success": False,
                    "error": data.get("errorMessage") or data.get("ResponseDescription") or "Unknown error",
                    "response_code": data.get("ResponseCode"),
                    "raw": data
                }
        except Exception as e:
            print(f"[MPESA STK] Error: {e}")
            return {"success": False, "error": str(e)}

    def query_transaction(self, checkout_request_id):
        """Check status of an STK push transaction"""
        access_token = self.get_access_token()
        if not access_token:
            return {"success": False, "error": "Failed to get access token"}

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
mpesa = MpesaService()
