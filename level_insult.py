import discord
from discord.ext import commands
import json
import time
import random
import util_database

mycol = util_database.myclient["utils"]["nodeports"]

async def earn_xp(msg: discord.Message):
    if not msg.guild: return
    if msg.author.bot: return
    if msg.content and msg.content[0] == "-": return # ignore commands
    db = await get_database(msg.guild.id)
    if not db["xp_module"]: return
    xp = random.randint(15, 25) # hard
    now = time.time()
    found = False
    for data in db["players"]:
        if data["userID"] == msg.author.id:
            found = True
            if not now - data["lastUpdated"] >= 60: return # seconds
            pull_player(data)
            data["xp"] += xp
            data["lastUpdated"] = now
            if data["xp"] > getTotalXP(data["level"]+1): # level up
                data["level"]+=1
                json_data = read_json_file("./res/mandatory_settings_and_splashes.json")
                text: str = random.choice(json_data["level up loser"]) if db["xp_troll"] else json_data["mee6 default"]
                user_data = {"name": f"<@{msg.author.id}>", "level": data["level"]}
                await msg.channel.send(text.format_map(user_data))
            push_player(data)
            return
    if not found:
        push_player(player_data(xp, msg.author.id, now))

async def user_rank(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return

async def guild_lead(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return

async def insult_user(bot: commands.Bot, msg: discord.Message):
    if msg.guild:
        db = await get_database(msg.guild.id)
        if not db["insult_module"]: return
    if await detect_mentions(msg, bot):
        text = random.choice(read_json_file("./res/mandatory_settings_and_splashes.json")["insults from thoughtcatalog.com"])
        await msg.reply(text)

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

async def detect_mentions(message: discord.Message, bot: commands.Bot):
    if message.mentions:
        if bot.user in message.mentions: return True
    ref_msg = await message.channel.fetch_message(message.reference.message_id) if message.reference else None
    if ref_msg and ref_msg.author == bot.user: return True

def getTotalXP(n):
    return int((5 * (91 * n + 27 * n ** 2 + 2 * n ** 3)) / 6)

# database handling
async def add_database(server_id: int):
    data = {
        "guild": server_id,
        "insult_module": True,
        "insult_default": True,
        "xp_module": False,
        "xp_troll": True,
        "channel_mode": False,
        "channels": [],
        "players": [],
        "roles": [],
        "xp_messages": [],
        "roasts": []
    }
    await mycol.insert_one(data)
    return data

async def fetch_database(server_id: int):
    return await mycol.find_one({"guild":server_id})

async def get_database(server_id: int):
    db = await fetch_database(server_id)
    if db: return db
    return await add_database(server_id)

def player_data(xp, id, time):
    return {
        "xp": xp,
        "level": 0,
        "lastUpdated": time,
        "userID": id,
        "rate": 1,
        "restricted": False
    }

async def push_player(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"players": dict(data)}})

async def pull_player(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"players": dict(data)}})

async def set_insult(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"insult_module": b}})

async def set_xp(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_module": b}})

async def set_mode(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"channel_mode": b}})