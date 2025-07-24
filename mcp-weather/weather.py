from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
AVIATION_WEATHER_API = "https://aviationweather.gov/api/data"
GEOCODING_API = "https://nominatim.openstreetmap.org"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

async def make_aviation_request(url: str) -> str | None:
    """Make a request to the Aviation Weather API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

async def make_geocoding_request(url: str) -> dict[str, Any] | None:
    """Make a request to the geocoding API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
        Event: {props.get('event', 'Unknown')}
        Area: {props.get('areaDesc', 'Unknown')}
        Severity: {props.get('severity', 'Unknown')}
        Description: {props.get('description', 'No description available')}
        Instructions: {props.get('instruction', 'No specific instructions provided')}
        """

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
            {period['name']}:
            Temperature: {period['temperature']}°{period['temperatureUnit']}
            Wind: {period['windSpeed']} {period['windDirection']}
            Forecast: {period['detailedForecast']}
            """
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def geocode_location(location: str) -> str:
    """Convert a location name into latitude and longitude coordinates.

    Args:
        location: Location name (e.g. "New York, NY", "London, UK", "Tokyo, Japan")
    """
    if not location or not location.strip():
        return "Please provide a valid location name."
    
    # URL encode the location and make the request
    import urllib.parse
    encoded_location = urllib.parse.quote(location.strip())
    url = f"{GEOCODING_API}/search?q={encoded_location}&format=json&limit=1"
    
    data = await make_geocoding_request(url)
    
    if not data or len(data) == 0:
        return f"Unable to find coordinates for '{location}'. Please try a more specific location name."
    
    result = data[0]
    latitude = float(result["lat"])
    longitude = float(result["lon"])
    display_name = result.get("display_name", location)
    
    return f"""Location: {display_name}
Latitude: {latitude}
Longitude: {longitude}
Coordinates: {latitude}, {longitude}"""

@mcp.tool()
async def get_aviation_weather(icao_code: str) -> str:
    """Get METAR and TAF aviation weather data for an airport by ICAO code.

    Args:
        icao_code: 4-letter ICAO airport code (e.g. KORD, EGLL, KJFK)
    """
    # Validate ICAO code format
    icao_code = icao_code.upper().strip()
    if len(icao_code) != 4 or not icao_code.isalpha():
        return "Invalid ICAO code. Please provide a 4-letter airport code (e.g., KORD, EGLL, KJFK)."
    
    result_parts = []
    
    # Get METAR data
    metar_url = f"{AVIATION_WEATHER_API}/metar?ids={icao_code}&format=raw"
    metar_data = await make_aviation_request(metar_url)
    
    if metar_data and metar_data.strip():
        result_parts.append(f"METAR for {icao_code}:")
        result_parts.append(metar_data.strip())
    else:
        result_parts.append(f"METAR for {icao_code}: No current METAR data available")
    
    # Get TAF data
    taf_url = f"{AVIATION_WEATHER_API}/taf?ids={icao_code}&format=raw"
    taf_data = await make_aviation_request(taf_url)
    
    if taf_data and taf_data.strip():
        result_parts.append(f"\nTAF for {icao_code}:")
        result_parts.append(taf_data.strip())
    else:
        result_parts.append(f"\nTAF for {icao_code}: No current TAF data available")
    
    if not metar_data and not taf_data:
        return f"Unable to fetch aviation weather data for {icao_code}. Please check the ICAO code and try again."
    
    return "\n".join(result_parts)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
