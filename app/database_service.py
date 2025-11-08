# database_service.py
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    async def stop(self):
        logger.info("DatabaseService stopped")
