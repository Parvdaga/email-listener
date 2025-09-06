import os
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    """
    Loads and validates application configuration from environment variables.
    """
    GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GCP_SA_CREDS_JSON = os.environ.get("GCP_SA_CREDS_JSON")
    GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
    
    IMAP_SERVER = "imap.gmail.com"
    SUBJECT_FILTER = "God bless you"
    CREDENTIALS_FILE = "credentials.json"

    @staticmethod
    def validate():
        """Checks if all required environment variables are set."""
        required_vars = [
            'GMAIL_ADDRESS', 'GMAIL_APP_PASSWORD', 'GEMINI_API_KEY',
            'GCP_SA_CREDS_JSON', 'GOOGLE_SHEET_ID'
        ]
        missing_vars = [var for var in required_vars if not getattr(Config, var)]
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False

        # Validate and write the credentials file
        try:
            creds_json = json.loads(Config.GCP_SA_CREDS_JSON)
            with open(Config.CREDENTIALS_FILE, "w") as f:
                json.dump(creds_json, f)
            logger.info("✅ Credentials file created successfully.")
        except (json.JSONDecodeError, TypeError):
            logger.error("❌ Invalid JSON in GCP_SA_CREDS_JSON.")
            return False
            
        logger.info("✅ All required environment variables are set and valid.")
        return True

# Load and validate the configuration on startup
config = Config()
is_config_valid = config.validate()