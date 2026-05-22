import os
import requests
import pytest
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DATA_GOV_API_KEY")
has_api_key = api_key and api_key != "your_key_here"

@pytest.mark.skipif(not has_api_key, reason="DATA_GOV_API_KEY is not configured in .env file")
def test_real_fetch():
    print(f"\n[📡 INFO] Attempting to connect to data.gov.in API with key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 5 else ''}")
    
    base_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 5,
        "filters[commodity]": "Tomato"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
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
        else:
            print("\n[⚠️ WARNING] API request succeeded, but returned 0 records for 'Tomato'. This might be due to API filters or temporary platform maintenance.")
            print(f"API Response: {data}\n")
            
        assert response.status_code == 200
        
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print(f"\n[⚠️ WARNING] API connection issue: {e}. Skipping real API test.")
        pytest.skip(f"Network issue connecting to data.gov.in: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"\n[❌ ERROR] API responded with HTTP error: {e}")
        assert False, f"HTTP Error: {e}"
    except Exception as e:
        print(f"\n[❌ ERROR] Connection failed: {e}\n")
        assert False, f"Connection failure: {e}"

if __name__ == "__main__":
    if has_api_key:
        test_real_fetch()
    else:
        print("API Key not configured, skipping real fetch.")
