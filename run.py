#!/usr/bin/env python
"""
CollegeMate - AI College Clerk Assistant
Run script to start the application
"""

import os
import sys
import webbrowser
from app import app, init_db, initialize_time_slots

def main():
    """Main function to run the CollegeMate application"""
    print("=" * 60)
    print("CollegeMate - AI College Clerk Assistant")
    print("=" * 60)
    
    # Initialize database and time slots
    print("Initializing database...")
    init_db()
    
    print("Initializing time slots...")
    initialize_time_slots()
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable is not set.")
        print("Using default API key from .env file.")
    
    # Start the application
    print("Starting CollegeMate application...")
    print("Open your browser at http://localhost:5000")
    
    # Open browser automatically
    webbrowser.open('http://localhost:5000')
    
    # Run the Flask application
    app.run(debug=True)

if __name__ == "__main__":
    main() 