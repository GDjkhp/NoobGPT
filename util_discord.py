from discord.ext import commands
import json
import util_database
mycol = util_database.myclient["utils"]["commands"]

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

async def copypasta(ctx: commands.Context):
    await ctx.reply(read_json_file("./res/mandatory_settings_and_splashes.json")["legal"])

async def avatar(ctx: commands.Context, bot: commands.Bot, arg: str):
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.avatar: return await ctx.reply(user.avatar.url)
    except: pass
    await ctx.reply("There is no such thing.")

async def banner(ctx: commands.Context, bot: commands.Bot, arg: str):
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.banner: return await ctx.reply(user.banner.url)
    except: pass
    await ctx.reply("There is no such thing.")