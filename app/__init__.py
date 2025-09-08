import logging
from flask import Flask
from .config import is_config_valid
from .services import configure_gemini

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    
    # Added for debugging startup
    print("🚀 Flask app creation started!")
    logging.info("🚀 Flask app creation started!")

    if not is_config_valid:
        logging.critical("CRITICAL: Application cannot start due to invalid configuration.")
        # In a real scenario, you might want to prevent the app from running.
        # For platforms like Railway, logging the error is often sufficient.
    
    if not configure_gemini():
        logging.critical("CRITICAL: Gemini API could not be configured.")

    # Import and register routes
    from . import routes
    app.register_blueprint(routes.bp)

    # Added for debugging startup
    print("✅ Flask app configured and ready to go!")
    logging.info("✅ Flask app configured and ready to go!")

    return app
