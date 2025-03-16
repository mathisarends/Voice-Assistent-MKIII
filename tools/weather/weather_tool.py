import asyncio
from typing import Type, Optional, List
import aiohttp
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import python_weather

# TODO: Das hier sollte eigentlich nicht hartverdrahtet werden
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

class WeatherInput(BaseModel):
    """Eingabemodell für das Wetter-Tool."""
    city: Optional[str] = Field(None, description="Stadt, für die das Wetter abgefragt werden soll (optional)")

class WeatherTool(BaseTool):
    """Tool zum Abrufen von Wetterinformationen."""
    
    name: str = "get_weather"
    description: str = """
    Ruft aktuelle Wetterinformationen und Vorhersagen ab.
    
    Wenn keine Stadt angegeben wird, wird automatisch der aktuelle Standort verwendet.
    Das Tool liefert die aktuelle Temperatur, Wetterbedingungen und eine Vorhersage.
    
    Beispiel: "Wie ist das Wetter heute?" oder "Wie wird das Wetter in Hamburg?"
    """
    args_schema: Type[BaseModel] = WeatherInput

    def __init__(self, **data):
        super().__init__(**data)
        # Private Variable für den Weather-Client
        self._weather_client = None

    def _get_weather_client(self, city: Optional[str] = None) -> WeatherClient:
        """Gibt einen Weather-Client zurück, initialisiert ihn bei Bedarf."""
        if not self._weather_client or (city and self._weather_client.city != city):
            self._weather_client = WeatherClient(city)
        return self._weather_client

    def _run(self, city: Optional[str] = None) -> str:
        """Synchrone Version der Ausführung."""
        return asyncio.run(self._arun(city=city))

    async def _arun(self, city: Optional[str] = None) -> str:
        """Asynchrone Version der Ausführung."""
        try:
            # Client für die angegebene oder automatisch ermittelte Stadt
            client = self._get_weather_client(city)
            
            # Wetterdaten abrufen
            weather_data = await client.fetch_weather_data()
            
            # Formatieren und zurückgeben
            return "\n".join(weather_data)
        except Exception as e:
            return f"Fehler beim Abrufen der Wetterdaten: {str(e)}"