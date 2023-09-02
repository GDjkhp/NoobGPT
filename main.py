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

# open server
from request_listener import keep_alive
keep_alive()

@bot.event
async def on_ready():
    print(":)")
    await bot.change_presence(status=discord.Status.dnd)

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
                   value='Google Bard chat completion. (Deprecated)', inline=False)
    emby.add_field(name='`-anime [query]`', 
                   value='Search and stream Anime using Gogoanime.', inline=False)
    emby.add_field(name='`-search [query]`', 
                   value='Search and stream TV shows and movies using Actvid.', inline=False)
    emby.add_field(name='`-aki (optional: [category = people/animals/objects] [language])`', 
                   value='Play Akinator.', inline=False)
    emby.add_field(name='`-ytdlp (optional: [format = mp3/m4a]) [link]`', 
                   value='Downloads and converts a YouTube video below 25MB.', inline=False)
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
                   value='Google AI PaLM text generation.', inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', inline=False)
    emby.set_thumbnail(url='https://i.imgur.com/ZbnJAHI.gif')
    emby.set_footer(text='Hi Mom! Look I\'m famous!\nBot by GDjkhp', icon_url=bot.user.avatar)
    await ctx.reply(embed=emby)

from actvid import Actvid
@bot.command()
async def search(ctx: commands.Context, *, arg=None):
    return await ctx.reply(f"Parser is currently broken. It's not much but consider [watching it here](https://actvid.rs/).")
    msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    await Actvid(msg, arg)

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
from bard import Bard
import time
cookie_dict = {
    "__Secure-1PSID": os.getenv("BARD"),
    "__Secure-1PSIDTS": os.getenv("BARD0"),
    # Any cookie values you want to pass session object.
}
@bot.command()
async def bard(ctx: commands.Context, *, arg=None):
    return await ctx.reply("This command requires cookies. Use `-palm` instead.")
    msg = await ctx.reply("Generating response…")
    old = round(time.time() * 1000)
    try: response = Bard(cookie_dict=cookie_dict, timeout=60).get_answer(arg)
    except Exception as e: return await msg.edit(content=f"**Error! :(**\n{e}")
    await ctx.reply(response['content'][:2000])
    if response['images']:
        img = list(response['images'])
        for i in range(len(img)):
            await ctx.reply(img[i])
    await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

# palm (alternative to bard)
import google.generativeai as PALM
PALM.configure(api_key=os.getenv("PALM"))
@bot.command()
async def palm(ctx: commands.Context, *, arg=None):
    if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose."
    msg = await ctx.reply("Generating response…")
    old = round(time.time() * 1000)
    try: 
        text = PALM.generate_text(prompt=arg).result
        if not text: return await msg.edit(content=f"**Error! :(**\nEmpty response.")
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        replyFirst = True
        for chunk in chunks:
            if replyFirst: 
                replyFirst = False
                await ctx.reply(chunk)
            else: await ctx.send(chunk)
    except Exception as e: return await msg.edit(content=f"**Error! :(**\n{e}")
    await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

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
    if not arg: return await ctx.reply("Good job finding this command. Bet you've seen this on source or caught someone using it.")
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

from place import PLACE
@bot.command()
async def place(ctx: commands.Context, x: str=None, y: str=None, z: str=None):
    bot.loop.create_task(PLACE(ctx, x, y, z))

bot.run(os.getenv("TOKEN"))