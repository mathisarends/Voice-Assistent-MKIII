import asyncio
from typing import Type, Optional, List
import aiohttp
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import python_weather

FALLBACK_CITY = "Münster"
    
class WeatherClient:
    def __init__(self, city: Optional[str] = None):
        self.city = city or FALLBACK_CITY

    async def _fetch_weather(self):
        """Fetches weather data asynchronously."""
        async with python_weather.Client(unit=python_weather.METRIC) as client:
            return await client.get(self.city)

    async def fetch_weather_data(self) -> List[str]:
        """Fetches weather data and handles errors."""
        try:
            weather = await self._fetch_weather()
            output = [f"Wetter in {self.city}:", f"Aktuelle Temperatur: {weather.temperature}°C"]

            # Original Format mit daily und hourly Daten
            for daily in weather:
                output.append(str(daily))
                for hourly in daily:
                    output.append(f' --> {hourly!r}')
                    
            return output
        
        except Exception as e:
            return [f"❌ Fehler beim Abrufen der Wetterdaten: {str(e)}"]