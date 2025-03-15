from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime
import discord
from discord.ext import commands
import wavelink
import sys
import asyncio

discord.utils.setup_logging()
intents = discord.Intents.default()
intents.message_content = True
# intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)

from level_insult import get_prefix, insult_user, earn_xp
from gde_hall_of_fame import main_gde, main_rob
from c_ai_discord import c_ai
from custom_status import silly_activities
from music import setup_hook_music
from util_message import message_snitcher
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

noobgpt_modules = [
    "c_ai_discord", "stablehorde", "gpt4free", "perplexity", "openai_", "googleai", # "petals",
    "tictactoe", "aki", "hangman", "quiz", "wordle_", "rps_game",
    "gelbooru", "deeznuts", "sflix", "ytdlp_", "magick_pillow", "kiss_api", "hianime_api", "min_music", # "cobalt", "kissasian",
    "animepahe", "manganato", "mangadex", # "gogoanime",
    "custom_status", "level_insult", "respond_mode", "quoteport", "help", # "weather",
    "util_discord", "util_member", "util_message",
]
moosic_modules = [
    "util_discord", "youtubeplayer", "music",
]
zero_modules = noobgpt_modules + ["util_channel"]

class NoobGPT(commands.Bot):
    def __init__(self, token, modules):
        self.token = os.getenv(token)
        self.modules = modules
        self.identifier = token
        self.node_ids = []
        super().__init__(
            command_prefix = get_prefix, intents = intents, help_command = None, allowed_mentions = mentions
        )

    async def on_ready(self):
        print(f"{self.identifier} (c) {datetime.now().year} The Karakters Kompany. All rights reserved.")
        print("Running for the following servers:")
        for number, guild in enumerate(self.guilds, 1):
            print(f"{number}. {guild} ({guild.id})")
        print(":)")

    async def on_guild_join(self, guild: discord.Guild):
        print(f"{self.identifier}: Joined {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild):
        print(f"{self.identifier}: Left {guild.name} ({guild.id})")

    async def on_message(self, message: discord.Message):
        if self.identifier != "MOOSIC":
            # self.loop.create_task(main_styx(self, message))
            self.loop.create_task(c_ai(self, message))
            self.loop.create_task(insult_user(self, message))
            self.loop.create_task(earn_xp(self, message))
        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if self.identifier == "MOOSIC": return
        self.loop.create_task(
            message_snitcher(before, after,"Message updated", f"#{before.channel}", 0x00ff00)
        )

    async def on_message_delete(self, message: discord.Message):
        if self.identifier == "MOOSIC": return
        self.loop.create_task(
            message_snitcher(message, None, "Message deleted", f"#{message.channel}", 0xff0000)
        )

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"{self.identifier}: {payload.node} | Resumed: {payload.resumed}")

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(setup_hook_music(self))
        if self.identifier == "NOOBGPT":
            self.loop.create_task(main_gde(self))
            self.loop.create_task(main_rob(self))
        for module in self.modules:
            await self.load_extension(module)

async def start_bot(bot: NoobGPT):
    await bot.start(bot.token)

async def main():
    await asyncio.gather(
        start_bot(NoobGPT("NOOBGPT", noobgpt_modules)),
        start_bot(NoobGPT("MOOSIC", moosic_modules)),
        start_bot(NoobGPT("KAGURA", noobgpt_modules)),
        start_bot(NoobGPT("ZERO", zero_modules)),
    )

asyncio.run(main())