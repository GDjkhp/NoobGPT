import motor.motor_asyncio as db_client, os
myclient = db_client.AsyncIOMotorClient(os.getenv('MONGO'))

# level + insult + music
mycol2 = myclient["utils"]["nodeports"]
async def add_database2(server_id: int):
    data = {
        "guild": server_id,
        "prefix": "-",
        "bot_master_role": 0,
        "bot_dj_role": 0,
        "insult_module": True,
        "insult_default": True,
        "xp_module": False,
        "xp_troll": True,
        "xp_channel_mode": False,
        "xp_rate": 1,
        "xp_cooldown": 60,
        "channels": [],
        "xp_roles": [],
        "xp_messages": [],
        "roasts": [],
        "players": []
    }
    await mycol2.insert_one(data)
    return data

async def fetch_database2(server_id: int):
    return await mycol2.find_one({"guild":server_id})

async def get_database2(server_id: int):
    db = await fetch_database2(server_id)
    if db: return db
    return await add_database2(server_id)

async def set_dj_role_db(server_id: int, role_id):
    await mycol2.update_one({"guild":server_id}, {"$set": {"bot_dj_role": role_id}})

async def set_insult(server_id: int, b: bool):
    await mycol2.update_one({"guild":server_id}, {"$set": {"insult_module": b}})

async def set_xp(server_id: int, b: bool):
    await mycol2.update_one({"guild":server_id}, {"$set": {"xp_module": b}})

async def set_cooldown(server_id: int, b):
    await mycol2.update_one({"guild":server_id}, {"$set": {"xp_cooldown": b}})

async def set_rate(server_id: int, b):
    await mycol2.update_one({"guild":server_id}, {"$set": {"xp_rate": b}})

async def set_troll_mode(server_id: int, b: bool):
    await mycol2.update_one({"guild":server_id}, {"$set": {"xp_troll": b}})

async def push_insult(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$push": {"roasts": data}})

async def pull_insult(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$pull": {"roasts": data}})

async def push_xp_msg(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$push": {"xp_messages": data}})

async def pull_xp_msg(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$pull": {"xp_messages": data}})

async def push_role(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$push": {"xp_roles": dict(data)}})

async def pull_role(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$pull": {"xp_roles": dict(data)}})

async def push_channel(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$push": {"channels": dict(data)}})

async def pull_channel(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$pull": {"channels": dict(data)}})

async def set_rank_channel(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$set": {"bot_rank_channel": data}})

async def set_prefix(server_id: int, p):
    await mycol2.update_one({"guild":server_id}, {"$set": {"prefix": p}})

async def set_master_role(server_id: int, data):
    await mycol2.update_one({"guild":server_id}, {"$set": {"bot_master_role": data}})