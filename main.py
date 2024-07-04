import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()
from level_insult import *

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)
bot = commands.Bot(command_prefix = get_prefix, 
                   intents = intents, 
                   help_command = None, 
                   allowed_mentions = mentions)

# open server (replit legacy hack)
# from request_listener import keep_alive
# keep_alive()

from gde_hall_of_fame import *
from c_ai_discord import *
from custom_status import *
from music import setup_hook_music, set_dj_role
@bot.event
async def on_ready():
    print(f"{bot.user.name} (c) 2024 The Karakters Kompany. All rights reserved.")
    print("Running for the following servers:")
    number = 0
    for guild in bot.guilds:
        number += 1
        print(f"{number}. {guild} ({guild.id})")
    print(":)")
    bot.loop.create_task(silly_activities(bot))
    bot.loop.create_task(main(bot))
    bot.loop.create_task(main_rob(bot))
    bot.loop.create_task(c_ai_init())
    await setup_hook_music(bot)
    await bot.load_extension('youtubeplayer')

import wavelink
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Wavelink Node connected: {payload.node} | Resumed: {payload.resumed}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f"Joined {guild.name} ({guild.id})")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"Left {guild.name} ({guild.id})")

@bot.event
async def on_message(message: discord.Message):
    # bot.loop.create_task(main_styx(bot, message))
    bot.loop.create_task(c_ai(bot, message))
    bot.loop.create_task(insult_user(bot, message))
    bot.loop.create_task(earn_xp(bot, message))
    await bot.process_commands(message)

# stckovrflw
@bot.event
async def on_command_error(ctx, command):
    pass

# guthib (no longer needed)
# @bot.tree.error
# async def on_app_command_error(interaction, error):
#     pass

# personal
@bot.command()
async def dj(ctx: commands.Context):
    bot.loop.create_task(set_dj_role(ctx))

@bot.command(name="rmusic")
async def reload_music(ctx: commands.Context):
    if not ctx.author.id == 729554186777133088: return
    await setup_hook_music(bot)

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
from util_discord import *
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
async def prefix(ctx: commands.Context, arg=None):
    bot.loop.create_task(set_prefix_cmd(ctx, arg))

@bot.command()
async def botmaster(ctx: commands.Context, arg=None):
    bot.loop.create_task(add_master_user(ctx, arg))

@bot.command()
async def ban(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(banner(ctx, bot, arg))

@bot.command()
async def av(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(avatar(ctx, bot, arg))

@bot.command()
async def legal(ctx: commands.Context):
    bot.loop.create_task(copypasta(ctx))

# insults
@bot.command()
async def insult(ctx: commands.Context):
    bot.loop.create_task(toggle_insult(ctx))

@bot.command()
async def insultview(ctx: commands.Context):
    bot.loop.create_task(view_insults(ctx))

@bot.command()
async def insultadd(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(add_insult(ctx, arg))

@bot.command()
async def insultdel(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(del_insult(ctx, arg))

@bot.command()
async def insulthelp(ctx: commands.Context):
    bot.loop.create_task(help_insult(ctx))

# xp level system
@bot.command()
async def xp(ctx: commands.Context):
    bot.loop.create_task(toggle_xp(ctx))

@bot.command()
async def rank(ctx: commands.Context, arg=None):
    bot.loop.create_task(user_rank(ctx, arg))

@bot.command()
async def levels(ctx: commands.Context):
    bot.loop.create_task(guild_lead(ctx))

@bot.command()
async def xproleadd(ctx: commands.Context, arg=None):
    bot.loop.create_task(add_xp_role(ctx, arg))

@bot.command()
async def xproleedit(ctx: commands.Context, role_id=None, keep=None, multiplier=None, cooldown=None):
    bot.loop.create_task(edit_xp_role(ctx, role_id, keep, multiplier, cooldown))

@bot.command()
async def xproledel(ctx: commands.Context, arg=None):
    bot.loop.create_task(delete_xp_role(ctx, arg))

@bot.command()
async def lvlmsgview(ctx: commands.Context):
    bot.loop.create_task(view_lvlmsgs(ctx))

@bot.command()
async def lvlmsgadd(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(add_lvl_msg(ctx, arg))

@bot.command()
async def lvlmsgdel(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(del_lvl_msg(ctx, arg))

@bot.command()
async def lvlmsgtroll(ctx: commands.Context):
    bot.loop.create_task(toggle_troll(ctx))

@bot.command()
async def xphelp(ctx: commands.Context):
    bot.loop.create_task(help_level(ctx))

@bot.command()
async def xpchan(ctx: commands.Context):
    bot.loop.create_task(toggle_special_channel(ctx))

@bot.command()
async def xpchanedit(ctx: commands.Context, rate=None, cd=None):
    bot.loop.create_task(edit_special_channel(ctx, rate, cd))

@bot.command()
async def xprankchan(ctx: commands.Context):
    bot.loop.create_task(rank_channel(ctx))

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

from quoteport import quote_this
@bot.command()
async def quote(ctx: commands.Context):
    bot.loop.create_task(quote_this(ctx))

from weather import Weather
@bot.command()
async def weather(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(Weather(ctx, arg))

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

# AI
from perplexity import *
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

from openai_ import *
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

@bot.command(aliases=['c.ai'])
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

@bot.command()
async def cping(ctx: commands.Context, *, arg=None):
    bot.loop.create_task(set_mention_mode(ctx, arg))

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

# arg
# from noobarg import start, end
# @bot.command()
# async def test(ctx: commands.Context, *, arg=None):
#     bot.loop.create_task(start(ctx, arg))

# @bot.command()
# async def a(ctx: commands.Context, *, arg=None):
#     bot.loop.create_task(end(ctx, arg))

bot.run(os.getenv("TOKEN"))