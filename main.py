import os
import requests
import xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Weather API Service", version="1.0.0")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "weatherapi-com.p.rapidapi.com"

if not RAPIDAPI_KEY:
    raise RuntimeError("Missing RAPIDAPI_KEY in environment variables.")

class WeatherRequest(BaseModel):
    city: str = Field(..., description="City name for weather lookup")
    output_format: str = Field(
        "json",
        description="Response format: 'json' or 'xml'",
        pattern="^(json|xml)$",  # ✅ replaced regex with pattern
    )

def get_weather_data(city: str):
    """
    Fetch weather data from RapidAPI's WeatherAPI endpoint.
    """
    url = f"https://{RAPIDAPI_HOST}/current.json"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    params = {"q": city}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching weather data.")

    data = response.json()
    if "location" not in data or "current" not in data:
        raise HTTPException(status_code=404, detail="Invalid city or missing data.")

    return data


def to_xml(data: dict) -> str:
    """
    Convert weather JSON data to XML string.
    """
    root = ET.Element("root")

    ET.SubElement(root, "Temperature").text = f"{data['Weather']}"
    ET.SubElement(root, "City").text = data["City"]
    ET.SubElement(root, "Latitude").text = str(data["Latitude"])
    ET.SubElement(root, "Longitude").text = str(data["Longitude"])

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


@app.post("/getCurrentWeather")
def get_current_weather(request_data: WeatherRequest):
    """
    Fetch current weather details for a given city.
    Supports JSON and XML output.
    """
    city = request_data.city
    output_format = request_data.output_format.lower()

    weather_data = get_weather_data(city)

    response_data = {
        "Weather": f"{weather_data['current']['temp_c']} C",
        "Latitude": weather_data["location"]["lat"],
        "Longitude": weather_data["location"]["lon"],
        "City": f"{weather_data['location']['name']}, {weather_data['location']['country']}",
    }

    if output_format == "json":
        return JSONResponse(content=response_data)

    xml_data = to_xml(response_data)
    return Response(content=xml_data, media_type="application/xml")
