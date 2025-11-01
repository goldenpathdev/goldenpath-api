"""Initialize database with tables."""
import asyncio
from api.database import init_db

async def main():
    """Create all database tables."""
    print("Creating database tables...")
    await init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
