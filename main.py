from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime
import discord
from discord.ext import commands
import wavelink

discord.utils.setup_logging()
intents = discord.Intents.default()
intents.message_content = True
# intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)

from level_insult import *
from gde_hall_of_fame import *
from c_ai_discord import *
from custom_status import *
from music import setup_hook_music

noobgpt_modules = [
    "c_ai_discord", "stablehorde", "gpt4free", "perplexity", "openai_", "googleai", # "petals",
    "tictactoe", "aki", "hangman", "quiz", "wordle_", "rps_game",
    "gelbooru", "deeznuts", "sflix", "kissasian", "ytdlp_", "magick_pillow", # "cobalt",
    "gogoanime", "animepahe", "manganato", "mangadex",
    "util_discord", "custom_status", "util_member", "level_insult", "respond_mode", "quoteport", "weather", "help",
]
moosic_modules = [
    "util_discord", "youtubeplayer", "music",
]

class NoobGPT(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = get_prefix, intents = intents, 
                         help_command = None, allowed_mentions = mentions)

    async def on_ready(self):
        print(f"{self.user.name} (c) {datetime.now().year} The Karakters Kompany. All rights reserved.")
        print("Running for the following servers:")
        for number, guild in enumerate(self.guilds, 1):
            print(f"{number}. {guild} ({guild.id})")
        print(":)")

    async def on_guild_join(self, guild: discord.Guild):
        print(f"{self.user.name}: Joined {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild):
        print(f"{self.user.name}: Left {guild.name} ({guild.id})")

    async def on_message(self, message: discord.Message):
        # self.loop.create_task(main_styx(self, message))
        self.loop.create_task(c_ai(self, message))
        self.loop.create_task(insult_user(self, message))
        self.loop.create_task(earn_xp(self, message))
        await self.process_commands(message)

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(main_gde(self))
        self.loop.create_task(main_rob(self))
        for module in noobgpt_modules:
            await self.load_extension(module)

class Moosic(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = get_prefix, intents = intents, 
                         help_command = None, allowed_mentions = mentions)

    async def on_ready(self):
        print(f"{self.user.name} (c) {datetime.now().year} The Karakters Kompany. All rights reserved.")
        print("Running for the following servers:")
        for number, guild in enumerate(self.guilds, 1):
            print(f"{number}. {guild} ({guild.id})")
        print(":)")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"{payload.node} | Resumed: {payload.resumed}")

    async def on_guild_join(self, guild: discord.Guild):
        print(f"{self.user.name}: Joined {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild):
        print(f"{self.user.name}: Left {guild.name} ({guild.id})")

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(setup_hook_music(self))
        for module in moosic_modules:
            await self.load_extension(module)

async def start_bot(bot: commands.Bot, token: str):
    await bot.start(token)

async def main():
    await asyncio.gather(
        start_bot(NoobGPT(), os.getenv("NOOBGPT")),
        start_bot(Moosic(), os.getenv("MOOSIC"))
    )

if __name__ == "__main__":
    asyncio.run(main())