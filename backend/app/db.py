from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://mongo:27017"  # docker-compose 기준 mongo 서비스명
DB_NAME = "driving_db"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
