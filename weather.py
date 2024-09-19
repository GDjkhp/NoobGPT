from discord.ext import commands
from discord import app_commands
import aiohttp
from urllib import parse as p
from util_discord import command_check, description_helper

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: print(e)

async def Weather(ctx: commands.Context, arg):
    if await command_check(ctx, "weather", "utils"): return
    message = await ctx.reply(f"Calculating…")
    try: results = await req_real('https://goweather.herokuapp.com/weather/'+p.quote_plus(arg))
    except: return await message.edit(content="I tripped.")
    if "message" in results: return await message.edit(content=results["message"]) # rare
    c = f"{arg} ({results['temperature']}, {results['wind']})\n{results['description']}\n"
    for i in results['forecast']:
        c += f"({i['temperature']}, {i['wind']}) "
    await message.edit(content=c)

class CogWeather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["weather"]}')
    @app_commands.describe(query="Location query (e.g. Lucena City)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def weather(self, ctx: commands.Context, *, query:str=None):
        await Weather(ctx, query)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogWeather(bot))