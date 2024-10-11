from dotenv import load_dotenv
load_dotenv()
import os
import discord
from discord.ext import commands
from level_insult import *
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
# intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)

from gde_hall_of_fame import *
from c_ai_discord import *
from custom_status import *
from music import setup_hook_music
import wavelink

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

    # stckovrflw (imporved)
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"NoobGPT: {error}")

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(main_gde(self))
        self.loop.create_task(main_rob(self))
        await self.load_extension('custom_status')
        await self.load_extension('util_discord')
        await self.load_extension('util_member')
        await self.load_extension('level_insult')
        await self.load_extension('sflix')
        await self.load_extension('kissasian')
        await self.load_extension('gogoanime')
        await self.load_extension('animepahe')
        await self.load_extension('manganato')
        await self.load_extension('mangadex')
        await self.load_extension('ytdlp_')
        await self.load_extension('cobalt')
        await self.load_extension('quoteport')
        await self.load_extension('weather')
        await self.load_extension('gelbooru')
        await self.load_extension('perplexity')
        await self.load_extension('openai_')
        await self.load_extension('googleai')
        await self.load_extension('petals')
        await self.load_extension('c_ai_discord')
        await self.load_extension('tictactoe')
        await self.load_extension('aki')
        await self.load_extension('hangman')
        await self.load_extension('quiz')
        await self.load_extension('wordle_')
        await self.load_extension('rps_game')
        await self.load_extension('help')

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

    # stckovrflw (imporved)
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"Moosic: {error}")

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(setup_hook_music(self))
        await self.load_extension('youtubeplayer')
        await self.load_extension('music')
        await self.load_extension('util_discord')

async def start_bot(bot: commands.Bot, token: str):
    await bot.start(token)

async def main():
    await asyncio.gather(
        start_bot(NoobGPT(), os.getenv("TOKEN")),
        start_bot(Moosic(), os.getenv("MOOSIC"))
    )

if __name__ == "__main__":
    asyncio.run(main())