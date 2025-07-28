#!/usr/bin/env python3
"""
Simple script to run the AI Pitchdeck Generator server with frontend
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🚀 Starting AI Pitchdeck Generator Server...")
    print("📁 Frontend will be available at: http://localhost:8000")
    print("📊 API documentation at: http://localhost:8000/docs")
    print("🔧 API endpoints at: http://localhost:8000/api")
    print("🐛 Debug static files at: http://localhost:8000/debug/static")
    print("\n" + "="*50)
    
    # Check static files
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    print(f"📂 Static directory: {static_dir}")
    print(f"📂 Static directory exists: {os.path.exists(static_dir)}")
    if os.path.exists(static_dir):
        files = os.listdir(static_dir)
        print(f"📂 Static files: {', '.join(files)}")
    print("="*50 + "\n")
    
    # Check if required environment variables are set
    required_vars = ["GOOGLE_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  WARNING: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file for full functionality.")
        print("="*50 + "\n")
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()