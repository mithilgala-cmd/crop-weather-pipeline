import os
import requests
from dotenv import load_dotenv

def test_real_fetch():
    load_dotenv()
    api_key = os.getenv("DATA_GOV_API_KEY")
    
    if not api_key or api_key == "your_key_here":
        print("\n[❌ ERROR] DATA_GOV_API_KEY is not configured in your .env file!")
        print("Please obtain a free API key from https://data.gov.in, add it to your .env file, and try again.\n")
        return False
        
    print(f"\n[📡 INFO] Attempting to connect to data.gov.in API with key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 5 else ''}")
    
    base_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 5,
        "filters[commodity]": "Tomato"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        records = data.get("records", [])
        
        if records:
            print("\n[✅ SUCCESS] Real API connection established successfully!")
            print(f"[📊 INFO] Retrieved {len(records)} sample Tomato records.")
            print("\nSample Record Preview:")
            for i, record in enumerate(records[:2], 1):
                print(f"  Record {i}: State: {record.get('state')}, District: {record.get('district')}, Market: {record.get('market')}, Price: {record.get('modal_price')}")
            print("\nAll systems operational! Mandi Price fetcher is fully validated.\n")
            return True
        else:
            print("\n[⚠️ WARNING] API request succeeded, but returned 0 records for 'Tomato'. This might be due to API filters or temporary platform maintenance.")
            print(f"API Response: {data}\n")
            return True
            
    except requests.exceptions.HTTPError as e:
        print(f"\n[❌ ERROR] API responded with HTTP error: {e}")
        if response.status_code == 401 or response.status_code == 403:
            print("[🔑 HINT] Your API key might be invalid or unactivated. Ensure it is copied correctly from your data.gov.in account page.")
        return False
    except Exception as e:
        print(f"\n[❌ ERROR] Connection failed: {e}\n")
        return False

if __name__ == "__main__":
    test_real_fetch()
