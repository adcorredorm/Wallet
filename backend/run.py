"""
Application entry point.

This script starts the Flask development server.
"""

import os
from dotenv import load_dotenv

from app import create_app

# Load environment variables
load_dotenv()

# Create Flask application
config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    # Run development server
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
