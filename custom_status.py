from discord.ext import commands
import discord
import asyncio
import random
import aiohttp
import os
import time
import json
from util_discord import check_if_not_owner
headers = {"authorization": os.getenv("LANYARD")}

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
    while True:
        if bot.is_ready():
            try:
                strings = [
                    f"serving {len(bot.users)} users in {len(bot.guilds)} guilds",
                    f"will return in {round(bot.latency*1000)}ms",
                    time.strftime("%A, %d %B %Y"),
                    "🔴 = stable 🟢 = unstable",
                    "RADIO ONSEN EUTOPIA",
                    "bot by gdjkhp",
                    "made in yokohama, japan",
                    "hosted in germany",
                    "written in python",
                    "powered by pterodactyl",
                    "don't make me popular >_<",
                ]
                data = await the_real_req(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}")
                if data["success"]: 
                    strings.append(f"gdjkhp is currently {data['data']['discord_status']}")
                    if data["data"]["kv"]: 
                        for key in list(data["data"]["kv"]):
                            strings.append(data["data"]["kv"][key])
                splashes = read_json_file("./res/mandatory_settings_and_splashes.json")["some funny splashes you can modify"]
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
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))

async def get_kv(ctx: commands.Context, key: str):
    if not key: return await ctx.reply("no key provided")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}")
    if not data["data"]["kv"] or not data["data"]["kv"].get(key): return await ctx.reply("no results found")
    await ctx.reply(data["data"]["kv"][key])

async def set_kv(ctx: commands.Context, arg: str):
    key = arg.split()[0]
    value = " ".join(arg.split()[1:])
    if not key or not value: return await ctx.reply("no key/value provided")
    await the_real_put(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}/kv/{key}", value)
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))

async def del_kv(ctx: commands.Context, key: str):
    if not key: return await ctx.reply("no key provided")
    await the_real_delete(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}/kv/{key}")
    data = await the_real_req(f"https://api.lanyard.rest/v1/users/{os.getenv('OWNER')}")
    await ctx.reply(embed=kv_embed(data["data"]["kv"]))

class LanyardUtil(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def kvview(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        await view_kv(ctx)

    @commands.command()
    async def kvget(self, ctx: commands.Context, key=None):
        if check_if_not_owner(ctx): return
        await get_kv(ctx, key)

    @commands.command()
    async def kvset(self, ctx: commands.Context, *, arg=None):
        if check_if_not_owner(ctx): return
        await set_kv(ctx, arg)

    @commands.command()
    async def kvdel(self, ctx: commands.Context, key=None):
        if check_if_not_owner(ctx): return
        await del_kv(ctx, key)

    @commands.command()
    async def sync(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        synced = await self.bot.tree.sync()
        await ctx.reply(f"Synced {len(synced)} slash commands")

    @commands.command()
    async def stats(self, ctx: commands.Context):
        stat_list = [
            f"serving {len(self.bot.users)} users in {len(self.bot.guilds)} guilds",
            f"will return in {round(self.bot.latency*1000)}ms",
            f"{len(self.bot.tree.get_commands())} application commands found"
        ]
        await ctx.reply("\n".join(stat_list))

async def setup(bot: commands.Bot):
    await bot.add_cog(LanyardUtil(bot))