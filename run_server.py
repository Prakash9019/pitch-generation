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


# import os
# import google.generativeai as genai
# from dotenv import load_dotenv

# # --- Step 1: Load Environment Variables ---
# print("Attempting to load .env file...")
# if load_dotenv():
#     print("✅ .env file loaded successfully.")
# else:
#     print("⚠️  Could not find or load .env file. Please ensure it exists in the same directory.")
#     exit()

# api_key = os.environ.get("GOOGLE_API_KEY")

# if not api_key:
#     print("❌ ERROR: GOOGLE_API_KEY not found in the .env file.")
#     exit()

# print(f"🔑 API Key found, starting with: {api_key[:4]}...{api_key[-4:]}")


# # --- Step 2: Configure the API ---
# try:
#     genai.configure(api_key=api_key)
#     print("✅ google.generativeai configured successfully.")
# except Exception as e:
#     print(f"❌ ERROR: Failed to configure the google.generativeai library.")
#     print(f"   Details: {e}")
#     exit()


# # --- Step 3: List Available Models ---
# print("\n--- Testing Model Listing ---")
# try:
#     print("Fetching list of available models...")
#     model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
#     # *** THIS LINE IS NOW CORRECTED ***
#     if model_list:
#         print("✅ Successfully fetched models that support 'generateContent':")
#         for model_name in model_list:
#             print(f"   - {model_name}")
#     else:
#         print("⚠️  Successfully connected, but no models supporting 'generateContent' were found for your API key.")

#     # Specifically check for gemini-pro
#     if 'models/gemini-pro' in model_list:
#         print("\n✅ 'models/gemini-pro' is available.")
#     else:
#         print("\n❌ 'models/gemini-pro' is NOT in the list of available models for your API key.")

# except Exception as e:
#     print(f"❌ ERROR: Failed to list models. This is a strong indicator of an API key or project issue.")
#     print(f"   Details: {e}")
#     print("   Please check the troubleshooting steps for your Google Cloud project.")
#     exit()


# # --- Step 4: Test Content Generation ---
# print("\n--- Testing Content Generation with 'gemini-pro' ---")
# try:
#     print("Instantiating 'gemini-pro' model...")
#     model = genai.GenerativeModel('gemini-pro')
#     prompt = "What is the speed of light?"
#     print(f"Sending prompt: '{prompt}'")
#     response = model.generate_content(prompt)

#     if response.text:
#         print("✅ Content generation successful!")
#         print(f"   Model Response: {response.text.strip()}")
#     else:
#         print("⚠️  Content generation completed but returned an empty response.")
#         print(f"   Full Response Details: {response}")

# except Exception as e:
#     print(f"❌ ERROR: Content generation failed.")
#     print(f"   This confirms a problem with your API key, project permissions, or billing.")
#     print(f"   Details: {e}")
#     exit()

# print("\n--- Verification Complete ---")
# print("If all steps above were successful, your API key is working correctly.")
# print("If any step failed, please review the error and follow the Google Cloud troubleshooting steps.")