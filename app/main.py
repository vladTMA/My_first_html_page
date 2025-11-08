# main.py
import asyncio
import logging
import os
import aiohttp

from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.config import MONITORED_CITIES, CITY_NAMES
import pytz
from datetime import datetime
from app.weather_service import WeatherService


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize templates and static files
templates = Jinja2Templates(directory="templates")


class WeatherBot:
    def __init__(self):
        # Все атрибуты объявляем сразу
        self.weather_service: Optional[WeatherService] = None
        self.database_service: Optional[object] = None
        self._stop_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize all services"""
        try:
            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                raise ValueError("OPENWEATHER_API_KEY environment variable is not set")

            self.weather_service = WeatherService(api_key=api_key)
            await self.weather_service.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            await self.stop()
            raise

    async def start(self) -> None:
        """Start all services"""
        await self.initialize()

    async def stop(self) -> None:
        """Stop all services"""
        self._stop_event.set()
        if self.weather_service:
            await self.weather_service.stop()
        if self.database_service:
            # если позже появится логика БД
            await self.database_service.stop()


# Create bot instance
bot = WeatherBot()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    await bot.start()
    yield
    logger.info("Shutting down application...")
    await bot.stop()


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    weather_list = []
    if bot.weather_service:
        for city_id in MONITORED_CITIES:
            try:
                weather = await bot.weather_service.get_weather_by_city(city_id)
                if weather:
                    moscow_tz = pytz.timezone('Europe/Moscow')
                    current_time = datetime.now(moscow_tz)
                    weather_list.append({
                        "name": CITY_NAMES.get(city_id, city_id),
                        "main": {"temp": weather.temperature, "humidity": weather.humidity},
                        "weather": [{"description": weather.description}],
                        "wind": {"speed": weather.wind_speed},
                        "sys": {"country": "RU"},
                        "recorded_at_moscow": current_time
                    })
            except Exception as e:
                weather_list.append({"error": str(e)})

    return templates.TemplateResponse(
        "weather.html",
        {"request": request, "weather_list": weather_list, "db_enabled": bot.database_service is not None}
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "weather_service": bot.weather_service is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/cities")
async def get_cities():
    return {"cities": MONITORED_CITIES}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8083, reload=True)
