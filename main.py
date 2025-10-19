from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import requests
import xml.etree.ElementTree as ET
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Weather API", version="1.0.0")

class WeatherRequest(BaseModel):
    city: str = Field(..., description="City name for weather lookup")
    output_format: str = Field(
        "json", description="Response format: 'json' or 'xml'", regex="^(json|xml)$"
    )


def get_coordinates(city: str):
    """
    Get latitude and longitude for a city using Open-Meteo geocoding API.
    """
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    response = requests.get(geo_url, timeout=10)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching coordinates.")

    data = response.json()
    if "results" not in data or not data["results"]:
        raise HTTPException(status_code=404, detail="City not found.")

    city_data = data["results"][0]
    return city_data["latitude"], city_data["longitude"], city_data["name"], city_data.get("country", "")


def get_weather(latitude: float, longitude: float):
    """
    Get current weather using Open-Meteo API.
    """
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    response = requests.get(weather_url, timeout=10)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching weather data.")

    data = response.json()
    return data["current_weather"]["temperature"]


def convert_to_xml(weather: float, city: str, lat: float, lon: float) -> str:
    """
    Convert weather data into XML string.
    """
    root = ET.Element("root")

    temp_elem = ET.SubElement(root, "Temperature")
    temp_elem.text = f"{weather} C"

    city_elem = ET.SubElement(root, "City")
    city_elem.text = city

    lat_elem = ET.SubElement(root, "Latitude")
    lat_elem.text = str(round(lat, 4))

    lon_elem = ET.SubElement(root, "Longitude")
    lon_elem.text = str(round(lon, 4))

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

@app.post("/getCurrentWeather")
def get_current_weather(request_data: WeatherRequest):
    """
    Get current weather, latitude, and longitude for a given city.
    Response format: JSON or XML.
    """
    city = request_data.city
    output_format = request_data.output_format.lower()

    latitude, longitude, city_name, country = get_coordinates(city)
    weather = get_weather(latitude, longitude)
    full_city_name = f"{city_name}, {country}"

    if output_format == "json":
        return JSONResponse(
            content={
                "Weather": f"{weather} C",
                "Latitude": latitude,
                "Longitude": longitude,
                "City": full_city_name,
            }
        )

    xml_response = convert_to_xml(weather, full_city_name, latitude, longitude)
    return Response(content=xml_response, media_type="application/xml")
