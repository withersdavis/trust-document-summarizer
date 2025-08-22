import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')
print(f"API Key found: {bool(api_key)}")
print(f"API Key starts with: {api_key[:20] if api_key else 'None'}")

try:
    # Try without any parameters first
    client = anthropic.Anthropic()
    print("Success: Created client without parameters")
except Exception as e:
    print(f"Error without parameters: {e}")
    
try:
    # Try with api_key explicitly
    client = anthropic.Anthropic(api_key=api_key)
    print("Success: Created client with api_key")
except Exception as e:
    print(f"Error with api_key: {e}")