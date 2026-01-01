import os
import yaml
from google.cloud import firestore
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Source of truth on the VM's local disk
ACCOUNTS_YAML_PATH = "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"

# Firestore Configuration
PROJECT_ID = "ai-quant-trading"
FIRESTORE_DB = "ai-trading-config"
COLLECTION_NAME = "strategies"

def load_local_yaml(path):
    """Loads the accounts.yaml file from the VM."""
    logging.info(f"Attempting to read local configuration from {path}...")
    try:
        with open(path, 'r') as file:
            data = yaml.safe_load(file)
            logging.info("✅ Successfully loaded accounts.yaml.")
            return data.get('accounts', {})
    except FileNotFoundError:
        logging.error(f"❌ CRITICAL: The file {path} was not found.")
        return None
    except Exception as e:
        logging.error(f"❌ CRITICAL: Failed to parse {path}. Error: {e}")
        return None

def transform_and_upload(accounts_data, db):
    """Transforms the accounts data and uploads each strategy to Firestore."""
    if not accounts_data:
        logging.warning("No account data to process.")
        return

    logging.info(f"Found {len(accounts_data)} account configurations to process.")
    
    for account_key, account_details in accounts_data.items():
        strategy_id = account_details.get('strategy')
        if not strategy_id or strategy_id == 'placeholder':
            logging.warning(f"Skipping account '{account_key}' with placeholder or missing strategy ID.")
            continue

        # The document ID in Firestore will be the strategy name
        doc_ref = db.collection(COLLECTION_NAME).document(strategy_id)
        
        # We will create a structured document for each strategy
        # This is a simplified transformation; a real dashboard might need more detail
        strategy_payload = {
            "strategy_id": strategy_id,
            "account_id": account_details.get("account_id"),
            "account_name": account_details.get("name"),
            "active": account_details.get("active", False),
            "trading_pairs": account_details.get("trading_pairs", []),
            "risk_settings": account_details.get("risk_settings", {})
            # We can add more parameters from the strategy's own config file later if needed
        }

        logging.info(f"Uploading configuration for strategy '{strategy_id}'...")
        doc_ref.set(strategy_payload, merge=True) # Use merge=True to not overwrite other fields if doc exists
        logging.info(f"  -> Successfully uploaded '{strategy_id}' to Firestore.")

def main():
    """Main execution function."""
    accounts_data = load_local_yaml(ACCOUNTS_YAML_PATH)
    if accounts_data is None:
        return

    try:
        logging.info(f"Connecting to Firestore (Project: {PROJECT_ID}, DB: {FIRESTORE_DB})...")
        db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DB)
        transform_and_upload(accounts_data, db)
        logging.info("✅ Universal migration complete. All strategies are now in the Cloud Truth.")
    except Exception as e:
        logging.error(f"❌ An error occurred during Firestore operations: {e}")

if __name__ == "__main__":
    main()





















