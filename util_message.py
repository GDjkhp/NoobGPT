'''
NOTE: noobgpt dystopian arc
this is a social experiment disabled by default.
you need to ask for every user's consent to use this feature.
acquiring message contents without consent should be illegal.
i made this module as proof of concept for discord bots to adapt to this concept.
this is also proof that I DO NOT LOG ANY OF THESE MESSAGES and i only process them per request.
'''

import discord
from discord import app_commands
from discord.ext import commands
from util_database import myclient
mycol = myclient["utils"]["1989"]

async def message_snitcher(msg: discord.Message):
    if msg.author.bot: return
    if "guild activated logger": "take the channel and send a message on message edit/delete/nono"

async def message_warden(msg: discord.Message):
    if msg.author.bot: return
    if msg.content in ["fuck", "shit", "damn", "piss"]: return "nono, delete if possible"

async def message_creditor(msg: discord.Message):
    if msg.author.bot: return
    if "message is nono": "-100 social credit score"
    if "message is helpful and positive": "+1 social credit score"

# utils
async def add_player_db(user_id: int):
    data = {
        "user_id": user_id,
        "silent_mode": False,
        "msg_content_ok": False,
        "social_credit_points": 0
    }
    await mycol.insert_one(data)
    return data

async def fetch_player_db(user_id: int):
    return await mycol.find_one({"user_id":user_id})

async def get_player_db(user_id: int):
    db = await fetch_player_db(user_id)
    if db: return db
    return await add_player_db(user_id)

async def update_player(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"social_credit_points": data}})

async def set_player_silent(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"silent_mode": data}})

async def set_player_consent(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"msg_content_ok": data}})

class TiananmenSquare1989Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(TiananmenSquare1989Cog(bot))