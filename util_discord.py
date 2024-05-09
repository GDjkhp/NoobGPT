from discord.ext import commands
import json

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

async def copypasta(ctx: commands.Context):
    await ctx.reply(read_json_file("./res/mandatory_settings_and_splashes.json")["legal"])

async def avatar(ctx: commands.Context, bot: commands.Bot, arg: str):
    if arg.isdigit():
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.avatar: await ctx.reply(user.avatar.url)
        else: await ctx.reply("There is no such thing.")
    else: await ctx.reply("Must be a valid user ID.")

async def banner(ctx: commands.Context, bot: commands.Bot, arg: str):
    if arg.isdigit():
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.banner: await ctx.reply(user.banner.url)
        else: await ctx.reply("There is no such thing.")
    else: await ctx.reply("Must be a valid user ID.")