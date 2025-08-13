import os, requests
from dotenv import load_dotenv

load_dotenv()
HOST = os.getenv("RAPIDAPI_HOST", "flightera-flight-data.p.rapidapi.com")
KEY  = os.getenv("RAPIDAPI_KEY")

class LiveAPIError(Exception): pass

def _headers():
    if not KEY:
        raise LiveAPIError("Missing RAPIDAPI_KEY")
    return {"x-rapidapi-host": HOST, "x-rapidapi-key": KEY}

def _get(path: str, params: dict):
    url = f"https://{HOST}/{path.lstrip('/')}"
    r = requests.get(url, headers=_headers(), params=params, timeout=20)
    if r.status_code != 200:
        raise LiveAPIError(f"{r.status_code}: {r.text[:400]}")
    return r.json()

def flight_status_by_number(flight: str):
    # Adjust endpoint/param names if your Flightera plan uses different ones
    return _get("flights/status", {"flight": flight})

def airport_departures(iata: str, hours: int = 6):
    # Adjust endpoint/param names if your plan uses different ones
    return _get("airports/departures", {"iata": iata, "hours": hours, "limit": 50})
