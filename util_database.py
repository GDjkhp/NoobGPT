import motor.motor_asyncio as db_client, os
myclient = db_client.AsyncIOMotorClient(os.getenv('MONGO'))