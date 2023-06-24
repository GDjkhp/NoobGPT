import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = "-", 
                   intents = intents, 
                   help_command = None, 
                   allowed_mentions = discord.AllowedMentions().none())

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
                   value='Play minesweeper (Deprecated)', inline=False)
    emby.add_field(name='`-bard [prompt]`', 
                   value='Google Bard chat completion.', inline=False)
    emby.add_field(name='`-anime [query]`', 
                   value='Search and stream Anime using Gogoanime.', inline=False)
    emby.add_field(name='`-search [query]`', 
                   value='Search and stream TV shows and movies using Actvid.', inline=False)
    emby.add_field(name='`-aki (optional: [category = people/animals/objects] [language])`', 
                   value='Play Akinator.', inline=False)
    emby.add_field(name='`-ytdlp (optional: [format = mp3/m4a]) [link]`', 
                   value='Downloads and coverts a YouTube video below 25MB.', inline=False)
    emby.add_field(name='`-tic`', 
                   value='Play tic-tac-toe with someone. (Deprecated)', inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', inline=False)
    emby.set_thumbnail(url=bot.user.avatar)
    emby.set_footer(text='Hi Mom! Look I\'m famous!\nBot by GDjkhp', icon_url='https://i.imgur.com/ZbnJAHI.gif')
    await ctx.reply(embed=emby)

from actvid import Actvid
@bot.command()
async def search(ctx: commands.Context, *, arg):
    msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    await Actvid(msg, arg)

from gogoanime import Gogoanime
@bot.command()
async def anime(ctx: commands.Context, *, arg):
    msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    await Gogoanime(msg, arg)

from tictactoe import TicTacToe
@bot.command()
async def tic(ctx: commands.Context):
    """Starts a tic-tac-toe game with yourself."""
    await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

from ytdlp_ import YTDLP
@bot.command()
async def ytdlp(ctx: commands.Context, arg1, arg2=None):
    await YTDLP(ctx, arg1, arg2)

# bard
from bard import Bard
os.environ['_BARD_API_KEY'] = os.getenv("BARD")
@bot.command()
async def bard(ctx: commands.Context, *, arg):
    response = Bard(timeout=60).get_answer(arg)
    await ctx.reply(response['content'][:2000])
    if response['images']:
        img = list(response['images'])
        for i in range(len(img)):
            await ctx.reply(img[i])

# :|
from gelbooru import R34, GEL, SAFE
@bot.command()
async def r34(ctx: commands.Context, *, arg):
    await R34(ctx, arg)
@bot.command()
async def gel(ctx: commands.Context, *, arg):
    await GEL(ctx, arg)
@bot.command()
async def safe(ctx: commands.Context, *, arg):
    await SAFE(ctx, arg)

# aki
from aki import Aki
@bot.command(name='aki')
# @commands.max_concurrency(1, per=BucketType.default, wait=False)
async def aki(ctx: commands.Context, arg1='people', arg2='en'):
    await Aki(ctx, arg1, arg2)

# lexica art
from lex import LEX
@bot.command()
async def lex(ctx: commands.Context, *, arg):
    await LEX(ctx, arg)

bot.run(os.getenv("TOKEN"))