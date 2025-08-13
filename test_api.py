import os
import requests
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get API details from .env
api_key = os.getenv("RAPIDAPI_KEY")
api_host = os.getenv("RAPIDAPI_HOST")

# Test endpoint
url = f"https://{api_host}/aircraft/info"

# Example parameters (replace with a real aircraft reg if you have one)
querystring = {"reg": "C-FIVQ"}  # Air Canada Boeing 777 as an example

headers = {
    "x-rapidapi-key": api_key,
    "x-rapidapi-host": api_host
}

print("Sending request...")
response = requests.get(url, headers=headers, params=querystring)

# Show status and data
print("Status Code:", response.status_code)
print("Response:", response.text)
