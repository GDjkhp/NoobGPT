import discord
from discord.ext import commands
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

from gde_hall_of_fame import main, main_rob, main_styx
from c_ai_discord import add_char, delete_char, t_chan, t_adm, c_ai, set_rate, c_help, t_mode, view_char, c_ai_init, edit_char, reset_char
from custom_status import silly_activities, view_kv, get_kv, set_kv, del_kv
@bot.event
async def on_ready():
    print(f"{bot.user.name} (c) 2024 The Karakters Kompany. All rights reserved.")
    print("Running for the following servers:")
    number = 0
    for guild in bot.guilds:
        number += 1
        print(f"{number}. ", guild)
    print(":)")
    bot.loop.create_task(silly_activities(bot))
    bot.loop.create_task(main(bot))
    bot.loop.create_task(main_rob(bot))
    bot.loop.create_task(c_ai_init())

@bot.event
async def on_message(message: discord.Message):
    # bot.loop.create_task(main_styx(bot, message))
    bot.loop.create_task(c_ai(bot, message))
    await bot.process_commands(message)

# stckovrflw
@bot.event
async def on_command_error(ctx, command):
    pass

# guthib
@bot.tree.error
async def on_app_command_error(interaction, error):
    pass

# personal
@bot.command()
async def kvview(ctx: commands.Context):
    bot.loop.create_task(view_kv(ctx))

@bot.command()
async def kvget(ctx: commands.Context, key=None):
    bot.loop.create_task(get_kv(ctx, key))

@bot.command()
async def kvset(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(set_kv(ctx, arg))

@bot.command()
async def kvdel(ctx: commands.Context, key=None):
    bot.loop.create_task(del_kv(ctx, key))

# TODO: store the strings in a json file that syncs with the website
from help import HALP
@bot.command()
async def halp(ctx: commands.Context):
    bot.loop.create_task(HALP(ctx, bot.user.avatar))

# discord
from util_discord import avatar, banner, copypasta, command_channel_mode, command_enable, command_disable, command_view, config_commands
@bot.command()
async def config(ctx: commands.Context):
    bot.loop.create_task(config_commands(ctx))

@bot.command()
async def channel(ctx: commands.Context):
    bot.loop.create_task(command_channel_mode(ctx))

@bot.command()
async def enable(ctx: commands.Context, arg=None):
    bot.loop.create_task(command_enable(ctx, arg))

@bot.command()
async def disable(ctx: commands.Context, arg=None):
    bot.loop.create_task(command_disable(ctx, arg))

@bot.command()
async def view(ctx: commands.Context):
    bot.loop.create_task(command_view(ctx))

@bot.command()
async def ban(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(banner(ctx, bot, arg))

@bot.command()
async def av(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(avatar(ctx, bot, arg))

@bot.command()
async def legal(ctx: commands.Context):
    bot.loop.create_task(copypasta(ctx))

# arg
from noobarg import start, end
@bot.command()
async def test(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(start(ctx, arg))

@bot.command()
async def a(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(end(ctx, arg))

# questionable
from sflix import Sflix
@bot.command()
async def flix(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Sflix(ctx, arg))

from kissasian import kiss_search, help_tv
@bot.command()
async def kiss(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(kiss_search(ctx, arg))

@bot.command()
async def tv(ctx: commands.Context):
    bot.loop.create_task(help_tv(ctx))

from gogoanime import Gogoanime
@bot.command()
async def gogo(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Gogoanime(ctx, arg))

from animepahe import pahe_search, help_anime
@bot.command()
async def pahe(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(pahe_search(ctx, arg))

@bot.command()
async def anime(ctx: commands.Context):
    bot.loop.create_task(help_anime(ctx))

from mangadex import dex_search, help_manga
@bot.command()
async def manga(ctx: commands.Context):
    bot.loop.create_task(help_manga(ctx))

@bot.command()
async def dex(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(dex_search(ctx, arg))

from manganato import nato_search
@bot.command()
async def nato(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(nato_search(ctx, arg))

from ytdlp_ import YTDLP
@bot.command()
async def ytdlp(ctx: commands.Context, arg1=None, arg2=None):
    bot.loop.create_task(YTDLP(ctx, arg1, arg2))

from cobalt import COBALT_API
@bot.command()
async def cob(ctx: commands.Context, *, arg:str=""):
    bot.loop.create_task(COBALT_API(ctx, arg.split()))

# :|
from gelbooru import R34, GEL, SAFE, help_booru
@bot.command()
async def booru(ctx: commands.Context):
    bot.loop.create_task(help_booru(ctx))
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
    bot.loop.create_task(quote_this(ctx))

# from lex import LEX
# @bot.command()
# async def lex(ctx: commands.Context, *, arg=None):
#     bot.loop.create_task(LEX(ctx, arg))

from weather import Weather
@bot.command()
async def weather(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Weather(ctx, arg))

# AI
from perplexity import main_perplexity, help_perplexity, main_anthropic, main_mistral, help_claude, help_mistral
@bot.command()
async def claude(ctx: commands.Context):
    bot.loop.create_task(help_claude(ctx))

@bot.command()
async def mistral(ctx: commands.Context):
    bot.loop.create_task(help_mistral(ctx))

@bot.command()
async def perplex(ctx: commands.Context):
    bot.loop.create_task(help_perplexity(ctx))

@bot.command()
async def m7b(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 0))

@bot.command()
async def mx7b(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 1))

@bot.command()
async def mx22b(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 2))

@bot.command()
async def ms(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 3))

@bot.command()
async def mm(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 4))

@bot.command()
async def ml(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 5))

@bot.command()
async def mcode(ctx: commands.Context):
    bot.loop.create_task(main_mistral(ctx, 6))

@bot.command()
async def cla(ctx: commands.Context):
    bot.loop.create_task(main_anthropic(ctx, 0))

@bot.command()
async def c3o(ctx: commands.Context):
    bot.loop.create_task(main_anthropic(ctx, 1))

@bot.command()
async def c3s(ctx: commands.Context):
    bot.loop.create_task(main_anthropic(ctx, 2))

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

from openai_ import chat, image, gpt3, help_openai
@bot.command()
async def ask(ctx: commands.Context):
    bot.loop.create_task(chat(ctx))

@bot.command()
async def imagine(ctx: commands.Context):
    bot.loop.create_task(image(ctx))

@bot.command()
async def gpt(ctx: commands.Context):
    bot.loop.create_task(gpt3(ctx))

@bot.command()
async def openai(ctx: commands.Context):
    bot.loop.create_task(help_openai(ctx))

from googleai import GEMINI_REST, help_google
@bot.command()
async def palm(ctx: commands.Context):
    bot.loop.create_task(GEMINI_REST(ctx, 0, True))

@bot.command()
async def ge(ctx: commands.Context):
    bot.loop.create_task(GEMINI_REST(ctx, 1, False))

@bot.command()
async def flash(ctx: commands.Context):
    bot.loop.create_task(GEMINI_REST(ctx, 2, False))

@bot.command()
async def googleai(ctx: commands.Context):
    bot.loop.create_task(help_google(ctx))

from petals import PETALS, petalsWebsocket
@bot.command()
async def petals(ctx: commands.Context):
    bot.loop.create_task(PETALS(ctx))

@bot.command()
async def beluga2(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(petalsWebsocket(ctx, arg, 7))

# CHARACTER AI
@bot.command()
async def cadd(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(add_char(ctx, arg, 0))

@bot.command()
async def crec(ctx: commands.Context):
    bot.loop.create_task(add_char(ctx, None, 2))

@bot.command()
async def ctren(ctx: commands.Context):
    bot.loop.create_task(add_char(ctx, None, 1))

@bot.command()
async def cdel(ctx: commands.Context):
    bot.loop.create_task(delete_char(ctx))

@bot.command()
async def cadm(ctx: commands.Context):
    bot.loop.create_task(t_adm(ctx))

@bot.command()
async def cchan(ctx: commands.Context):
    bot.loop.create_task(t_chan(ctx))

@bot.command()
async def crate(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(set_rate(ctx, arg))

@bot.command()
async def chelp(ctx: commands.Context):
    bot.loop.create_task(c_help(ctx))

@bot.command()
async def cmode(ctx: commands.Context):
    bot.loop.create_task(t_mode(ctx))

@bot.command()
async def cchar(ctx: commands.Context):
    bot.loop.create_task(view_char(ctx))

@bot.command()
async def cedit(ctx: commands.Context, rate=None):
    bot.loop.create_task(edit_char(ctx, rate))

@bot.command()
async def cres(ctx: commands.Context):
    bot.loop.create_task(reset_char(ctx))

# the real games
from tictactoe import Tic
@bot.command()
async def tic(ctx: commands.Context):
    bot.loop.create_task(Tic(ctx))

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

from rps_game import game_rps
@bot.command()
async def rps(ctx: commands.Context):
    bot.loop.create_task(game_rps(ctx))

# from place import PLACE
# @bot.command()
# async def place(ctx: commands.Context, x: str=None, y: str=None, z: str=None):
#     bot.loop.create_task(PLACE(ctx, x, y, z))

bot.run(os.getenv("TOKEN"))