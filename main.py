import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)
bot = commands.Bot(command_prefix = "-", 
                   intents = intents, 
                   help_command = None, 
                   allowed_mentions = mentions)

# open server (replit legacy hack)
# from request_listener import keep_alive
# keep_alive()

# gde test
from gde_hall_of_fame import main

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
    bot.loop.create_task(main(bot)) # gde bot

# TODO: store the strings on a json file that syncs with the website
@bot.command()
async def halp(ctx: commands.Context):
    emby = discord.Embed(title="NoobGPT", 
                         description="A **very simple yet complicated** multi-purpose Discord bot that does pretty much nothing but insult you.", 
                         url="https://gdjkhp.github.io/NoobGPT/", color=0x00ff00)
    emby.add_field(name='`-ask [prompt]`', 
                   value='OpenAI GPT-3.5-Turbo (ChatGPT) chat completion.', inline=False)
    emby.add_field(name='`-gpt [prompt]`', 
                   value='OpenAI GPT-3 text completion.', inline=False)
    emby.add_field(name='`-imagine [prompt]`', 
                   value='OpenAI Dall-E image generation.', inline=False)
    emby.add_field(name='`-quote`', 
                   value='Reply to a message to make it a quote.', inline=False)
    emby.add_field(name='`-ms`', 
                   value='Play minesweeper. (Deprecated)', inline=False)
    emby.add_field(name='`-bard [prompt]`', 
                   value='[Google Bard](https://bard.google.com) chat completion. (Deprecated)', inline=False)
    emby.add_field(name='`-anime [query]`', 
                   value='Search and watch Anime using [Gogoanime](https://gogoanimehd.io).', inline=False)
    emby.add_field(name='`-tv [query]`', 
                   value='Search and watch TV shows and movies using [SFlix](https://sflix.se).', inline=False)
    emby.add_field(name='`-aki (optional: [category = people/animals/objects] [language])`', 
                   value='Play a guessing game of [Akinator](https://akinator.com).', inline=False)
    emby.add_field(name='`-ytdlp (optional: [format = mp3/m4a]) [link]`', 
                   value='Download or convert a YouTube video under 25MB discord limit. [Supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)', inline=False)
    emby.add_field(name='`-tic`', 
                   value='Play tic-tac-toe with someone. (Deprecated)', inline=False)
    emby.add_field(name='`-hang (optional: [mode = all/hardcore/me] [count = 1-50] [type = any/word/quiz] [category = any/9-32] [difficulty = any/easy/medium/hard])`', 
                   value='Play the word puzzle game of hangman.', inline=False)
    emby.add_field(name='`-place (optional: [x = 0-499] [y = 0-499] [zoom = 16x])`', 
                   value='Play the Reddit social experiment event about placing pixels on a canvas.', inline=False)
    emby.add_field(name='`-quiz (optional: [mode = all/anon/me] [version = any/v1/v2] [count = 1-50] [category = any/9-32] [difficulty = any/easy/medium/hard] [type = any/multiple/boolean])`', 
                   value='Play a game of quiz.', inline=False)
    emby.add_field(name='`-ban [userid]`', 
                   value='Return a user\'s Discord profile banner.', inline=False)
    emby.add_field(name='`-av [userid]`', 
                   value='Return a user\'s Discord profile avatar.', inline=False)
    emby.add_field(name='`-palm [prompt]`', 
                   value='Google AI PaLM language model. (Legacy)', inline=False)
    emby.add_field(name='`-petals`', 
                   value='Run large language models at home, BitTorrent‑style.', inline=False)
    emby.add_field(name='`-weather [query]`', 
                   value='Check weather forecast using [weather-api](https://github.com/robertoduessmann/weather-api).', inline=False)
    emby.add_field(name='`-ge [prompt = text/image]`', 
                   value='Google AI Gemini language model.', inline=False)
    emby.add_field(name='`/help`', 
                   value='Show music commands help page.', inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', inline=False)
    emby.set_thumbnail(url='https://i.imgur.com/ZbnJAHI.gif')
    emby.set_footer(text='Bot by GDjkhp\n© The Karakters Kompany, 2023', icon_url=bot.user.avatar)
    await ctx.reply(embed=emby)

from sflix import Sflix
@bot.command()
async def tv(ctx: commands.Context, *, arg=None):
    # return await ctx.reply(f"Parser is currently broken. It's not much but consider [watching it here](https://actvid.rs/).")
    msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    await Sflix(msg, arg)

from gogoanime import Gogoanime
@bot.command()
async def anime(ctx: commands.Context, *, arg=None):
    if arg: msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    else: msg = await ctx.reply("Imagine something that doesn't exist. Must be sad. You are sad. You don't belong here.\nLet's all love lain.")
    await Gogoanime(msg, arg if arg else "serial experiments lain")

from tictactoe import TicTacToe
@bot.command()
async def tic(ctx: commands.Context):
    """Starts a tic-tac-toe game with yourself."""
    await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

from ytdlp_ import YTDLP
@bot.command()
async def ytdlp(ctx: commands.Context, arg1=None, arg2=None):
    if not arg1: arg1, arg2 = "mp3", "dQw4w9WgXcQ"
    bot.loop.create_task(YTDLP(ctx, arg1, arg2))

# bard (legacy)
@bot.command()
async def bard(ctx: commands.Context, *, arg=None):
    await ctx.reply("This command requires cookies. Use `-palm` instead.")

# palm (alternative to bard)
from googleai import PALM_LEGACY
@bot.command()
async def palm(ctx: commands.Context, *, arg=None):
    await GEMINI_REST(ctx, arg, True)

# gemini
from googleai import GEMINI_REST
@bot.command()
async def ge(ctx: commands.Context, *, arg=None):
    await GEMINI_REST(ctx, arg, False)

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

# aki
from aki import Aki
@bot.command(name='aki')
# @commands.max_concurrency(1, per=BucketType.default, wait=False)
async def aki(ctx: commands.Context, arg1='people', arg2='en'):
    await Aki(ctx, arg1, arg2)

# lexica art
from lex import LEX
@bot.command()
async def lex(ctx: commands.Context, *, arg=None):
    if not arg: return await ctx.reply("Good job finding this command. Bet you've seen this from the source or caught someone using it.")
    await LEX(ctx, arg)

from quiz import QUIZ
@bot.command()
async def quiz(ctx: commands.Context, mode: str=None, v: str=None, count: str=None, cat: str=None, diff: str=None, ty: str=None):
    await QUIZ(ctx, mode, v, count, cat, diff, ty)

# banner
@bot.command()
async def ban(ctx: commands.Context, *, arg=None):
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.banner: await ctx.reply(user.banner.url)
        else: await ctx.reply("There is no such thing.")
    except: await ctx.reply("Must be a valid user ID.")

# avatar
@bot.command()
async def av(ctx: commands.Context, *, arg=None):
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user.avatar: await ctx.reply(user.avatar.url)
        else: await ctx.reply("There is no such thing.")
    except: await ctx.reply("Must be a valid user ID.")

# hangman
from hangman import HANG
@bot.command()
async def hang(ctx: commands.Context, mode: str=None, count: str=None, type: str=None):
    await HANG(ctx, mode, count, type, None, None)

# from place import PLACE
@bot.command()
async def place(ctx: commands.Context, x: str=None, y: str=None, z: str=None):
    return await ctx.reply("i love having bugs in my code")
    # bot.loop.create_task(PLACE(ctx, x, y, z))

# petals
from petals import PETALS
@bot.command()
async def petals(ctx: commands.Context):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("Pinging…")
        await msg.edit(content=PETALS())

from petals import BELUGA2
@bot.command()
async def beluga2(ctx: commands.Context, *, arg=None):
    await BELUGA2(ctx, arg)

from petals import LLAMA2
@bot.command()
async def llama2(ctx: commands.Context, *, arg=None):
    await LLAMA2(ctx, arg)

from petals import GUANACO
@bot.command()
async def guanaco(ctx: commands.Context, *, arg=None):
    await GUANACO(ctx, arg)

from petals import LLAMA
@bot.command()
async def llama(ctx: commands.Context, *, arg=None):
    await LLAMA(ctx, arg)

from petals import BLOOMZ
@bot.command()
async def bloomz(ctx: commands.Context, *, arg=None):
    await BLOOMZ(ctx, arg)

from weather import Weather
@bot.command()
async def weather(ctx: commands.Context, *, arg=None):
    await Weather(ctx, arg)

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

from openai_ import chat, image, gpt3
@bot.command()
async def ask(ctx: commands.Context):
    await chat(ctx.message)

@bot.command()
async def imagine(ctx: commands.Context):
    await image(ctx.message)

@bot.command()
async def gpt(ctx: commands.Context):
    await gpt3(ctx.message)

from quoteport import quote_this
@bot.command()
async def quote(ctx: commands.Context):
    bot.loop.create_task(quote_this(ctx))

# the real
from wordle_ import wordle
@bot.command()
async def word(ctx: commands.Context, mode: str=None, count: str=None):
    await wordle(ctx, mode, count)

from rps_game import RPSView
@bot.command()
async def rps(ctx: commands.Context):
    await ctx.reply(":index_pointing_at_the_viewer:", view=RPSView(None, None))

bot.run(os.getenv("TOKEN"))