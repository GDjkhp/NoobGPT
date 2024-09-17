from dotenv import load_dotenv
load_dotenv()
import os
import discord
from discord.ext import commands
from level_insult import *

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)
bot = commands.Bot(command_prefix = get_prefix, intents = intents, 
                   help_command = None, allowed_mentions = mentions)

# open server (replit legacy hack)
# from request_listener import keep_alive
# keep_alive()

from gde_hall_of_fame import *
from c_ai_discord import *
from custom_status import *
from music import setup_hook_music

@bot.event
async def on_ready():
    print(f"{bot.user.name} (c) 2024 The Karakters Kompany. All rights reserved.")
    print("Running for the following servers:")
    for number, guild in enumerate(bot.guilds, 1):
        print(f"{number}. {guild} ({guild.id})")
    print(":)")

import wavelink
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"{payload.node} | Resumed: {payload.resumed}")

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
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(error)

# guthib (no longer needed, for slash commands)
# @bot.tree.error
# async def on_app_command_error(interaction, error):
#     pass
    
@bot.event
async def setup_hook():
    bot.loop.create_task(silly_activities(bot))
    bot.loop.create_task(main(bot))
    bot.loop.create_task(main_rob(bot))
    await setup_hook_music(bot)
    await bot.load_extension('youtubeplayer')
    await bot.load_extension('music')
    await bot.load_extension('custom_status')
    await bot.load_extension('util_discord')
    await bot.load_extension('level_insult')
    await bot.load_extension('sflix')
    await bot.load_extension('kissasian')
    await bot.load_extension('gogoanime')
    await bot.load_extension('animepahe')
    await bot.load_extension('manganato')
    await bot.load_extension('mangadex')
    await bot.load_extension('ytdlp_')
    await bot.load_extension('cobalt')
    await bot.load_extension('quoteport')
    await bot.load_extension('weather')
    await bot.load_extension('gelbooru')
    await bot.load_extension('perplexity')
    await bot.load_extension('openai_')
    await bot.load_extension('googleai')
    await bot.load_extension('petals')
    await bot.load_extension('c_ai_discord')
    await bot.load_extension('tictactoe')
    await bot.load_extension('aki')
    await bot.load_extension('hangman')
    await bot.load_extension('quiz')
    await bot.load_extension('wordle_')
    await bot.load_extension('rps_game')
    await bot.load_extension('help')

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