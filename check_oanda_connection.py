import os
import requests
import logging
from dotenv import load_dotenv

# Define the path to the config file and load it
OANDA_CONFIG_PATH = "/Users/mac/quant_system_clean/google-cloud-trading-system/oanda_config.env"
load_dotenv(dotenv_path=OANDA_CONFIG_PATH)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_oanda_connection():
    """
    Checks for OANDA credentials and attempts a simple API call to verify them.
    """
    OANDA_API_KEY = os.getenv("OANDA_API_KEY")
    # Use PRIMARY_ACCOUNT from the .env file as the account ID for this test
    OANDA_ACCOUNT_ID = os.getenv("PRIMARY_ACCOUNT")
    OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

    print("-" * 80)
    logger.info("Starting OANDA Connection Verification...")
    print("-" * 80)

    # 1. Check if the environment variables are set
    logger.info("Step 1: Checking for environment variables...")
    if not OANDA_API_KEY:
        logger.error("❌ FAILED: OANDA_API_KEY environment variable is NOT set.")
        return False
    else:
        logger.info("✅ SUCCESS: OANDA_API_KEY is set.")

    if not OANDA_ACCOUNT_ID:
        logger.error("❌ FAILED: OANDA_ACCOUNT_ID environment variable is NOT set.")
        return False
    else:
        logger.info("✅ SUCCESS: OANDA_ACCOUNT_ID is set.")

    # 2. Attempt to connect to the OANDA API
    logger.info("\nStep 2: Attempting to connect to OANDA API and fetch account details...")
    headers = {
        'Authorization': f'Bearer {OANDA_API_KEY}',
        'Content-Type': 'application/json'
    }
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/summary"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ SUCCESS: Successfully connected to OANDA and fetched account summary.")
            account_summary = response.json().get('account', {})
            currency = account_summary.get('currency', 'N/A')
            balance = account_summary.get('balance', 'N/A')
            logger.info(f"   - Account Currency: {currency}")
            logger.info(f"   - Account Balance: {balance}")
            return True
        else:
            logger.error(f"❌ FAILED: Could not connect to OANDA. The API returned status code: {response.status_code}")
            logger.error(f"   - Response: {response.text}")
            logger.error("   - Please verify that your OANDA_API_KEY and OANDA_ACCOUNT_ID are correct.")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ FAILED: A network error occurred while trying to connect to OANDA.")
        logger.error(f"   - Error: {e}")
        return False

if __name__ == "__main__":
    is_successful = verify_oanda_connection()
    print("-" * 80)
    if is_successful:
        print("✅ Verification Passed. The system has the necessary credentials to fetch live data.")
    else:
        print("❌ Verification Failed. The system is missing the required OANDA credentials. Please set the environment variables.")
    print("-" * 80)
