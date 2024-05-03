from discord.ext import commands
import aiohttp
from urllib import parse as p

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: print(e)

async def Weather(ctx: commands.Context, arg):
    message = await ctx.reply(f"Calculating…")
    try: results = await req_real('https://goweather.herokuapp.com/weather/'+p.quote_plus(arg))
    except: return await message.edit(content="I tripped.")
    if "message" in results: return await message.edit(content=results["message"]) # rare
    c = f"{arg} ({results['temperature']}, {results['wind']})\n{results['description']}\n"
    for i in results['forecast']:
        c += f"({i['temperature']}, {i['wind']}) "
    await message.edit(content=c)