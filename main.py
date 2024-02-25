import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)
bot = commands.Bot(command_prefix = "-", 
                   intents = intents, 
                   help_command = None, 
                   allowed_mentions = mentions)

# open server (replit legacy hack)
# from request_listener import keep_alive
# keep_alive()

# gde test
from gde_hall_of_fame import main, main_rob
# @tasks.loop(seconds=60)  # task runs every 60 seconds
# async def my_background_task():
#     bot.loop.create_task(main(bot)) # gde bot

# @my_background_task.before_loop
# async def before_my_task():
#     await bot.wait_until_ready()  # wait until the bot logs in

@bot.event
async def on_ready():
    print(f"{bot.user.name} (c) 2024 The Karakters Kompany. All rights reserved.")
    print("Running for the following servers:")
    number = 0
    for guild in bot.guilds:
        number += 1
        print(f"{number}. ", guild)
    print(":)")
    await bot.change_presence(status=discord.Status.dnd)
    bot.loop.create_task(main(bot))
    bot.loop.create_task(main_rob(bot))

# TODO: store the strings on a json file that syncs with the website
from help import HALP
@bot.command()
async def halp(ctx: commands.Context):
    await HALP(ctx, bot.user.avatar)

@bot.command()
async def legal(ctx: commands.Context):
    await ctx.reply(content="EVERY POST I HAVE EVER MADE ON THIS DISCORD IS SATIRE. I DO NOT CONDONE NOR SUPPORT ANY OF THE OPINIONS EXPRESSED ON THIS CHATROOM. Any post associated with this IP is satire and should be treated as such. At no point has anyone associated with this IP has condoned, encouraged, committed, or abated acts of violence or threats of violence against any persons, regardless of racial, ethnic, religious or cultural background. In case of an investigation by any federal entity or similar, I do not have any involvement with the people in it, I do not know how I am here, probably added by a third party, I do not support any actions by the member(s) of this group.")

# arg
from noobarg import start, end
@bot.command()
async def test(ctx: commands.Context, *, arg=None):
    await start(ctx, arg)

@bot.command()
async def a(ctx: commands.Context, *, arg=None):
    await end(ctx, arg)

# discord
@bot.command()
async def ban(ctx: commands.Context, *, arg=None):
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.banner: await ctx.reply(user.banner.url)
        else: await ctx.reply("There is no such thing.")
    except: await ctx.reply("Must be a valid user ID.")

@bot.command()
async def av(ctx: commands.Context, *, arg=None):
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.avatar: await ctx.reply(user.avatar.url)
        else: await ctx.reply("There is no such thing.")
    except: await ctx.reply("Must be a valid user ID.")

# questionable
from sflix import Sflix
@bot.command()
async def tv(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Sflix(ctx, arg))

from gogoanime import Gogoanime
@bot.command()
async def anime(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Gogoanime(ctx, arg))

from ytdlp_ import YTDLP
@bot.command()
async def ytdlp(ctx: commands.Context, arg1=None, arg2=None):
    if not arg1: arg1, arg2 = "mp3", "dQw4w9WgXcQ"
    bot.loop.create_task(YTDLP(ctx, arg1, arg2))

# :|
from gelbooru import R34, GEL, SAFE
@bot.command()
async def r34(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(R34(ctx, arg))
@bot.command()
async def gel(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(GEL(ctx, arg))
@bot.command()
async def safe(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(SAFE(ctx, arg))

from quoteport import quote_this
@bot.command()
async def quote(ctx: commands.Context):
    return await ctx.reply("under development")
    # bot.loop.create_task(quote_this(ctx))

from lex import LEX
@bot.command()
async def lex(ctx: commands.Context, *, arg=None):
    if not arg: return await ctx.reply("Good job finding this command. Bet you've seen this from the source or caught someone using it.")
    await LEX(ctx, arg)

# from place import PLACE
@bot.command()
async def place(ctx: commands.Context, x: str=None, y: str=None, z: str=None):
    return await ctx.reply("under development")
    # bot.loop.create_task(PLACE(ctx, x, y, z))

from weather import Weather
@bot.command()
async def weather(ctx: commands.Context, *, arg=None):
    await Weather(ctx, arg)

# AI
from perplexity import main_perplexity, help_perplexity
@bot.command()
async def perplex(ctx: commands.Context):
    await ctx.reply(help_perplexity())

@bot.command()
async def ll(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 0))

@bot.command()
async def cll(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 1))

@bot.command()
async def mis(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 2))

@bot.command()
async def mix(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 3))

@bot.command()
async def ssc(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 4))

@bot.command()
async def sso(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 5))

@bot.command()
async def smc(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 6))

@bot.command()
async def smo(ctx: commands.Context):
    bot.loop.create_task(main_perplexity(ctx, 7))

from openai_ import chat, image, gpt3
@bot.command()
async def ask(ctx: commands.Context):
    bot.loop.create_task(chat(ctx.message))

@bot.command()
async def imagine(ctx: commands.Context):
    bot.loop.create_task(image(ctx.message))

@bot.command()
async def gpt(ctx: commands.Context):
    bot.loop.create_task(gpt3(ctx.message))

# bard (legacy)
@bot.command()
async def bard(ctx: commands.Context, *, arg=None):
    await ctx.reply("This command requires cookies. Use `-ge` or `-halp` -> `AI` instead.")

# palm (alternative to bard)
# from googleai import PALM_LEGACY
@bot.command()
async def palm(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(GEMINI_REST(ctx, arg, True))

from googleai import GEMINI_REST
@bot.command()
async def ge(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(GEMINI_REST(ctx, arg, False))

from petals import PETALS
@bot.command()
async def petals(ctx: commands.Context):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("Pinging…")
        await msg.edit(content=PETALS())

from petals import BELUGA2
@bot.command()
async def beluga2(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(BELUGA2(ctx, arg))

from petals import LLAMA2
@bot.command()
async def llama2(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(LLAMA2(ctx, arg))

from petals import GUANACO
@bot.command()
async def guanaco(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(GUANACO(ctx, arg))

from petals import LLAMA
@bot.command()
async def llama(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(LLAMA(ctx, arg))

from petals import BLOOMZ
@bot.command()
async def bloomz(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(BLOOMZ(ctx, arg))

# the real games
from tictactoe import TicTacToe
@bot.command()
async def tic(ctx: commands.Context):
    """Starts a tic-tac-toe game with yourself."""
    await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

from aki import Aki
@bot.command()
# @commands.max_concurrency(1, per=BucketType.default, wait=False)
async def aki(ctx: commands.Context, arg1='people', arg2='en'):
    bot.loop.create_task(Aki(ctx, arg1, arg2))

from hangman import HANG
@bot.command()
async def hang(ctx: commands.Context, mode: str=None, count: str=None, type: str=None):
    bot.loop.create_task(HANG(ctx, mode, count, type, None, None))

from quiz import QUIZ
@bot.command()
async def quiz(ctx: commands.Context, mode: str=None, v: str=None, count: str=None, cat: str=None, diff: str=None, ty: str=None):
    bot.loop.create_task(QUIZ(ctx, mode, v, count, cat, diff, ty))

from wordle_ import wordle
@bot.command()
async def word(ctx: commands.Context, mode: str=None, count: str=None):
    bot.loop.create_task(wordle(ctx, mode, count))

from rps_game import RPSView
@bot.command()
async def rps(ctx: commands.Context):
    await ctx.reply(":index_pointing_at_the_viewer:", view=RPSView(None, None))

@bot.command()
async def ms(ctx: commands.Context):
    await ctx.reply("under development")

@bot.command()
async def chess(ctx: commands.Context):
    await ctx.reply("under development")

bot.run(os.getenv("TOKEN"))