# __init__.py
import asyncio
import os
import logging
from typing import Optional
from app.weather_service import WeatherService
from app.database_service import DatabaseService


logger = logging.getLogger(__name__)


class WeatherBot:
    def __init__(self):
        # Атрибуты объявляем сразу, даже если пока None
        self.weather_service: Optional[WeatherService] = None
        self.database_service: Optional[DatabaseService] = None
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
