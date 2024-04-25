from discord.ext import commands
import discord
import asyncio
import random
import aiohttp
import os
import time

user_id = 729554186777133088
headers = {
    "authorization": os.getenv("LANYARD")
}

async def the_real_req(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def the_real_put(url: str, data: str):
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=data) as response:
            return response

async def the_real_delete(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            return response

async def silly_activities(bot: commands.Bot):
    while True:
        data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
        strings = [
            f"G: {len(bot.guilds)} | U: {len(bot.users)}",
            f"gdjkhp is currently {data['data']['discord_status']}",
            time.strftime("%B %d, %Y"),
            "free update: character.ai (-chelp)",
            "get started: -halp",
            "RADIO ONSEN EUTOPIA",
            "feat. tama and sadako",
            "bot by gdjkhp",
            "made in yokohama, japan",
            "hosted in finland",
            "written in python and node.js",
            "powered by pterodactyl",
            "https://gdjkhp.github.io",
            "https://gdjkhp.github.io/NoobGPT",
            "https://github.com/GDjkhp/level-up-loser-python-branch",
            "https://paypal.me/GDjkhp",
            "https://discord.gg/ZbvhQYv9Ka",
            "https://bot-hosting.net/?aff=729554186777133088",
            "https://myanimelist.net/profile/GDjkhp",
            "https://jkhp.newgrounds.com",
        ]
        if data["data"]["kv"]: 
            for key in list(data["data"]["kv"]):
                strings.append(data["data"]["kv"][key])
        await bot.change_presence(activity=discord.CustomActivity(name=random.choice(strings)), 
                                  status=discord.Status.dnd)
        await asyncio.sleep(10)

async def view_kv(ctx: commands.Context):
    if not ctx.author.id == user_id: return await ctx.reply("i know who you are")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(data["data"]["kv"])

async def get_kv(ctx: commands.Context, key: str):
    if not ctx.author.id == user_id: return await ctx.reply("i know who you are")
    if not key: return await ctx.reply("no key provided")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    if not data["data"]["kv"] or not data["data"]["kv"].get(key): return await ctx.reply("no results found")
    await ctx.reply(data["data"]["kv"][key])

async def set_kv(ctx: commands.Context, arg: str):
    if not ctx.author.id == user_id: return await ctx.reply("i know who you are")
    key = arg.split()[0]
    value = " ".join(arg.split()[1:])
    if not key or not value: return await ctx.reply("no key/value provided")
    await the_real_put(f"https://api.lanyard.rest/v1/users/{user_id}/kv/{key}", value)
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(data["data"]["kv"])

async def del_kv(ctx: commands.Context, key: str):
    if not ctx.author.id == user_id: return await ctx.reply("i know who you are")
    if not key: return await ctx.reply("no key provided")
    await the_real_delete(f"https://api.lanyard.rest/v1/users/{user_id}/kv/{key}")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(data["data"]["kv"])