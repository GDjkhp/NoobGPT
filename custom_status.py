from discord.ext import commands
import discord
import asyncio
import random
import aiohttp
import os
import time
import json

user_id = 729554186777133088
headers = {"authorization": os.getenv("LANYARD")}
loop_status = False

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
        
def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

async def silly_activities(bot: commands.Bot):
    global loop_status
    if loop_status: return
    loop_status = True
    while True:
        try:
            splashes = read_json_file("./res/mandatory_settings_and_splashes.json")["some funny splashes you can modify"]
            strings = [
                f"serving {len(bot.users)} users in {len(bot.guilds)} guilds",
                f"will return in {round(bot.latency*1000)}ms",
                time.strftime("%A, %d %B %Y"),
                "get started: -halp",
                "🔴 = stable, 🟢 = unstable",
                "RADIO ONSEN EUTOPIA",
                "feat. tama and sadako",
                "bot by gdjkhp",
                "made in yokohama, japan",
                "hosted in finland",
                "written in python",
                "powered by pterodactyl",
            ]
            data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
            if data["success"]: 
                strings.append(f"gdjkhp is currently {data['data']['discord_status']}")
                if data["data"]["kv"]: 
                    for key in list(data["data"]["kv"]):
                        strings.append(data["data"]["kv"][key])
            strings.append(random.choice(splashes))
            await bot.change_presence(activity=discord.CustomActivity(name=random.choice(strings)), 
                                    status=discord.Status.dnd)
        except Exception as e: print(e)
        await asyncio.sleep(10)

def kv_embed(kv: dict):
    e = discord.Embed(title="📝 Lanyard", description=f"{len(kv)} found", color=0x00ff00)
    for key, value in kv.items(): e.add_field(name=key, value=value, inline=False)
    return e

async def view_kv(ctx: commands.Context):
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))

async def get_kv(ctx: commands.Context, key: str):
    if not key: return await ctx.reply("no key provided")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    if not data["data"]["kv"] or not data["data"]["kv"].get(key): return await ctx.reply("no results found")
    await ctx.reply(data["data"]["kv"][key])

async def set_kv(ctx: commands.Context, arg: str):
    key = arg.split()[0]
    value = " ".join(arg.split()[1:])
    if not key or not value: return await ctx.reply("no key/value provided")
    await the_real_put(f"https://api.lanyard.rest/v1/users/{user_id}/kv/{key}", value)
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))

async def del_kv(ctx: commands.Context, key: str):
    if not key: return await ctx.reply("no key provided")
    await the_real_delete(f"https://api.lanyard.rest/v1/users/{user_id}/kv/{key}")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{user_id}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))