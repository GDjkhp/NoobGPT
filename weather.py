from discord.ext import commands
import requests
from urllib import parse as p

async def Weather(ctx: commands.Context, arg):
    message = await ctx.reply(f"Calculating…")
    try: results = requests.get('https://goweather.herokuapp.com/weather/'+p.quote_plus(arg)).json()
    except: return await message.edit(content="I tripped.")
    if "message" in results: return await message.edit(content=results["message"]) # rare
    c = f"{arg} ({results['temperature']}, {results['wind']})\n{results['description']}\n"
    if results['forecast']:
        for i in results['forecast']:
            c += f"({i['temperature']}, {i['wind']}) "
    await message.edit(content=c)