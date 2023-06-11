import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents = intents)

# open server
from request_listener import keep_alive
keep_alive()

@bot.event
async def on_ready():
    print(":)")
    await bot.change_presence(status=discord.Status.dnd)

class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        emby = discord.Embed(title="NoobGPT Official Website", description="https://gdjkhp.github.io/NoobGPT/", color=0x00ff00)
        await destination.send(embed=emby)

bot.help_command = MyNewHelp()

from actvid import Actvid
@bot.command()
async def search(ctx: commands.Context, *, arg):
    msg = await ctx.reply(f"Searching `{arg}` Please wait…")
    await Actvid(msg, arg)

from gogoanime import Gogoanime
@bot.command()
async def anime(ctx: commands.Context, *, arg):
    msg = await ctx.reply(f"Searching `{arg}` Please wait…")
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
    if response['links']:
        for img in range(5): # hard limit
            await ctx.reply(response['links'][img])

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

bot.run(os.getenv("TOKEN"))