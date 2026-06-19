from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime
import discord
from discord.ext import commands
from discord.gateway import DiscordWebSocket
import wavelink
import lava_lyra
import sys
import asyncio

from request_listener import serve, register_bot
from level_insult import get_prefix, insult_user, earn_xp
from gde_hall_of_fame import main_gde, main_rob
from c_ai_discord import c_ai
from custom_status import silly_activities, phone_status
# from music import setup_hook_music
from music_lyra import setup_hook_music
from util_message import message_snitcher

discord.utils.setup_logging()
intents = discord.Intents.default()
intents.message_content = True
# intents.presences = True
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True)
DiscordWebSocket.identify = phone_status
if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

noobgpt_modules = [
    "c_ai_discord", "stablehorde", "gpt4free", "perplexity", "openai_", "googleai", # "petals",
    "tictactoe", "aki", "hangman", "quiz", "wordle_", "rps_game",
    "gelbooru", "deeznuts", "sflix", "ytdlp_", "magick_pillow", "min_music_lyra", # "kiss_api", "hianime_api", "cobalt", "kissasian",
    "animepahe", "manganato", "mangadex", # "gogoanime",
    "custom_status", "level_insult", "respond_mode", "quoteport", "help", # "weather",
    "util_discord", "util_member", "util_message", # "util_geometryjump",
    "mister_squid", "roshidere", "util_channel", # squid + zero modules
]
moosic_modules = ["util_discord", "youtubeplayer_lyra", "music_lyra"]
# zero_modules = noobgpt_modules + ["util_channel"]
# squid_modules = ["util_discord", "mister_squid", "roshidere"]
exclude_bots = ["MOOSIC", "SQUID"]

class NoobGPT(commands.Bot):
    def __init__(self, identifier, modules):
        self.identifier = identifier
        self.token = os.getenv(identifier)
        self.modules = modules
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
        if self.identifier not in exclude_bots:
            # self.loop.create_task(main_styx(self, message))
            self.loop.create_task(c_ai(self, message))
            self.loop.create_task(insult_user(self, message))
            self.loop.create_task(earn_xp(self, message))
        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if self.identifier in exclude_bots: return
        self.loop.create_task(
            message_snitcher(before, after,"Message updated", f"#{before.channel}", 0x00ff00)
        )

    async def on_message_delete(self, message: discord.Message):
        if self.identifier in exclude_bots: return
        self.loop.create_task(
            message_snitcher(message, None, "Message deleted", f"#{message.channel}", 0xff0000)
        )

    # deprecated: wavelink
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"{self.identifier}: {payload.node} | Resumed: {payload.resumed}")

    # lyra: track events
    async def on_lyra_track_start(self, player: lava_lyra.Player, track: lava_lyra.Track):
        print(f"{self.identifier} / on_lyra_track_start:\nplayer - {player} | track - {track}")

    async def on_lyra_track_end(self, player: lava_lyra.Player, track: lava_lyra.Track, reason: str):
        print(f"{self.identifier} / on_lyra_track_end:\nplayer - {player} | track - {track} | reason - {reason}")

    async def on_lyra_track_stuck(self, player: lava_lyra.Player, track: lava_lyra.Track, threshold: float):
        print(f"{self.identifier} / on_lyra_track_stuck:\nplayer - {player} | track - {track} | threshold - {threshold}")

    async def on_lyra_track_exception(self, player: lava_lyra.Player, track: lava_lyra.Track, error: str):
        print(f"{self.identifier} / on_lyra_track_exception:\nplayer - {player} | track - {track} | error - {error}")

    # lyra: websocket events
    async def on_lyra_websocket_closed(self, payload: lava_lyra.WebSocketClosedPayload):
        print(f"{self.identifier} / on_lyra_websocket_closed:\npayload - {payload}")

    async def on_lyra_websocket_open(self, target: str, ssrc: int):
        print(f"{self.identifier} / on_lyra_websocket_open:\ntarget - {target} | ssrc - {ssrc}")

    # lyra: lyrics events
    async def on_lyra_lyrics_found(self, player: lava_lyra.Player, track: lava_lyra.Player, lyrics: lava_lyra.Lyrics):
        print(f"{self.identifier} / on_lyra_lyrics_found:\nplayer - {player} | track - {track} | lyrics - {lyrics}")

    async def on_lyra_lyrics_unavailable(self, player: lava_lyra.Player, track: lava_lyra.Player):
        print(f"{self.identifier} / on_lyra_lyrics_unavailable:\nplayer - {player} | track - {track}")

    async def on_lyra_lyrics_update(self, player: lava_lyra.Player, track: lava_lyra.Player, line: lava_lyra.LyricLine):
        print(f"{self.identifier} / on_lyra_lyrics_update:\nplayer - {player} | track - {track} | line - {line}")

    # lyra: node events
    async def on_lyra_node_connected(self, node_id: str, is_nodelink: bool, reconnect: bool):
        print(f"{self.identifier} / on_lyra_node_connected:\nnode_id - {node_id} | is_nodelink - {is_nodelink} | reconnect - {reconnect}")

    async def on_lyra_node_disconnected(self, node_id: str, is_nodelink: bool, player_count: int):
        print(f"{self.identifier} / on_lyra_node_disconnected:\nnode_id - {node_id} | is_nodelink - {is_nodelink} | player_count - {player_count}")

    async def on_lyra_node_reconnecting(self, node_id: str, is_nodelink: bool, retry_in: float):
        print(f"{self.identifier} / on_lyra_node_reconnecting:\nnode_id - {node_id} | is_nodelink - {is_nodelink} | retry_in - {retry_in}")

    # lyra: player state events
    async def on_lyra_player_created(self, player: lava_lyra.Player, guild_id: int):
        print(f"{self.identifier} / on_lyra_player_created:\nplayer - {player} | guild_id - {guild_id}")

    async def on_lyra_volume_changed(self, player: lava_lyra.Player, volume: int):
        print(f"{self.identifier} / on_lyra_volume_changed:\nplayer - {player} | volume - {volume}")

    async def on_lyra_player_connected(self, player: lava_lyra.Player, voice: dict):
        print(f"{self.identifier} / on_lyra_player_connected:\nplayer - {player} | voice - {voice}")

    async def on_lyra_filters_changed(self, player: lava_lyra.Player, filters: dict):
        print(f"{self.identifier} / on_lyra_filters_changed:\nplayer - {player} | filters - {filters}")

    # lyra: undocumented nodelink exclusive
    async def on_lyra_pause(self, player: lava_lyra.Player, paused: bool):
        print(f"{self.identifier} / on_lyra_pause:\nplayer - {player} | paused - {paused}")

    async def on_lyra_seek(self, player: lava_lyra.Player, position: int):
        print(f"{self.identifier} / on_lyra_seek:\nplayer - {player} | position - {position}")

    async def on_lyra_mix_started(self, player: lava_lyra.Player, mix_id: str, track: lava_lyra.Track, volume: float):
        print(f"{self.identifier} / on_lyra_mix_started:\nplayer - {player} | mix_id - {mix_id} | track - {track} | volume - {volume}")

    async def on_lyra_mix_ended(self, player: lava_lyra.Player, mix_id: str, reason: str):
        print(f"{self.identifier} / on_lyra_mix_ended:\nplayer - {player} | mix_id - {mix_id} | reason - {reason}")

    async def setup_hook(self):
        self.loop.create_task(silly_activities(self))
        self.loop.create_task(setup_hook_music(self))
        if self.identifier == "NOOBGPT":
            self.loop.create_task(main_gde(self))
            self.loop.create_task(main_rob(self))
        for module in self.modules:
            exclude = ["custom_status"]
            if self.identifier != "NOOBGPT" and module in exclude: continue
            await self.load_extension(module)

async def start_bot(bot: NoobGPT):
    register_bot(bot.identifier, bot)
    await bot.start(bot.token)

async def main():
    await asyncio.gather(
        start_bot(NoobGPT("NOOBGPT", noobgpt_modules)),
        start_bot(NoobGPT("MOOSIC", moosic_modules)),
        start_bot(NoobGPT("KAGURA", noobgpt_modules)),
        # start_bot(NoobGPT("ZERO", zero_modules)),
        # start_bot(NoobGPT("SQUID", squid_modules)),
        serve(),
    )

asyncio.run(main())