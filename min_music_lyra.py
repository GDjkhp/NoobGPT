from discord.ext import commands
from discord import app_commands
from youtubeplayer_lyra import *
from util_discord import description_helper

# min_music for noobgpt (only essential commands)
# list np play pause resume stop skip autoplay shuffle remove clear dj repeat swap replace move
class CogYouTubePlayerMin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_lyra_track_start(self, vc: NoobGPTPlayer, track: lava_lyra.Track):
        await queue_on_start(self.bot, vc)

    @commands.Cog.listener()
    async def on_lyra_track_end(self, vc: NoobGPTPlayer, track: lava_lyra.Track, reason: str):
        await queue_on_end(vc)

    @commands.command(name="mreset")
    async def reset(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        await setup_hook_music(self.bot)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['media']['music']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def music(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.command(aliases=['musichelp', 'helpmusic', 'helpm']) # alias
    async def mhelp(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['dj']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dj(self, ctx: commands.Context):
        await set_dj_role(ctx)

    @commands.command()
    async def djspam(self, ctx: commands.Context, channel_id: str=None):
        await set_dj_channel(ctx, channel_id)

    # player
    @commands.command() # alias
    async def p(self, ctx: commands.Context, *, query: str=None):
        await music_play(self.bot, ctx, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Play music (YouTube Music)")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=search_auto)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def play(self, ctx: commands.Context, *, query:str=None):
        await music_play(self.bot, ctx, query)

    @commands.command(aliases=['die', 'dc']) # alias
    async def leave(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['stop']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def stop(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['pause']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def pause(self, ctx: commands.Context):
        await music_pause(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['resume']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def resume(self, ctx: commands.Context):
        await music_resume(ctx)

    @commands.command() # alias
    async def s(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['skip']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def skip(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.command() # alias
    async def np(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['nowplaying']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def nowplaying(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    @commands.command()
    async def summon(self, ctx: commands.Context):
        await music_summon(self.bot, ctx)

    @commands.command()
    async def lyrics(self, ctx: commands.Context):
        await music_lyrics(ctx)

    # queue
    @commands.command()
    async def search(self, ctx: commands.Context, *, query: str=None):
        await queue_search(self.bot, ctx, query)

    @commands.command()
    @app_commands.describe(index="Track number you want to peek into (Must be a valid integer)")
    async def peek(self, ctx: commands.Context, index: str):
        await queue_peek(ctx, index)

    @commands.command() # alias
    async def queue(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['list']}")
    @app_commands.describe(page="Page number")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def list(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['repeat']}")
    @app_commands.describe(mode="Repeat mode")
    @app_commands.autocomplete(mode=mode_repeat_auto)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def repeat(self, ctx: commands.Context, mode: str):
        await queue_loop(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['autoplay']}")
    @app_commands.describe(mode="Autoplay mode")
    @app_commands.autocomplete(mode=mode_rec_auto)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def autoplay(self, ctx: commands.Context, mode: str):
        await queue_autoplay(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['shuffle']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def shuffle(self, ctx: commands.Context):
        await queue_shuffle(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['clear']}")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def clear(self, ctx: commands.Context):
        await queue_reset(ctx)

    @commands.command()
    async def smart(self, ctx: commands.Context, count: str=None):
        await queue_smart(ctx, count)

    @commands.command()
    async def fair(self, ctx: commands.Context):
        await queue_fair(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['remove']}")
    @app_commands.describe(index="Track number you want to remove (Must be a valid integer)",
                           index2="Track number you want to remove within range (Must be a valid integer)",
                           member="Remove all tracks queued by this member")
    @app_commands.autocomplete(member=remove_member_auto)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def remove(self, ctx: commands.Context, index: str=None, index2: str=None, member: str=None):
        await queue_remove(ctx, index, index2, member)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['replace']}")
    @app_commands.describe(index="Track number you want to replace (Must be a valid integer)", query="Search query")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def replace(self, ctx: commands.Context, index: str, *, query: str):
        await queue_replace(ctx, index, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['swap']}")
    @app_commands.describe(init="First track number you want to swap into (Must be a valid integer)",
                           dest="Second track number you want to swap into (Must be a valid integer)")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def swap(self, ctx: commands.Context, init: str, dest: str):
        await queue_swap(ctx, init, dest)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['move']}")
    @app_commands.describe(init="Track number you want to move from (Must be a valid integer)",
                           dest="Track number you want to move to (Must be a valid integer)")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def move(self, ctx: commands.Context, init: str, dest: str):
        await queue_move(ctx, init, dest)

    @commands.command()
    async def volume(self, ctx: commands.Context, value: str=None):
        await music_volume(ctx, value)

    @commands.command()
    async def filters(self, ctx: commands.Context, reset: str = None, filter: str = None):
        await music_filters(ctx, reset, filter)

    # ── individual filter sub-commands ──────────────────────────────────────────
    @commands.command()
    async def karaoke(
        self, ctx: commands.Context,
        level: float = 1.0,
        mono_level: float = 1.0,
        filter_band: float = 220.0,
        filter_width: float = 100.0,
    ):
        await filter_karaoke(ctx, level, mono_level, filter_band, filter_width)

    @commands.command()
    async def timescale(
        self, ctx: commands.Context,
        pitch: float = 1.0,
        speed: float = 1.0,
        rate: float = 1.0,
    ):
        await filter_timescale(ctx, pitch, speed, rate)

    @commands.command()
    async def lowpass(self, ctx: commands.Context, smoothing: float = 20.0):
        await filter_lowpass(ctx, smoothing)

    @commands.command()
    async def rotation(self, ctx: commands.Context, rotation_hz: float = 5.0):
        await filter_rotation(ctx, rotation_hz)

    @commands.command()
    async def distortion(
        self, ctx: commands.Context,
        sin_offset: float = 0.0,
        sin_scale: float = 1.0,
        cos_offset: float = 0.0,
        cos_scale: float = 1.0,
        tan_offset: float = 0.0,
        tan_scale: float = 1.0,
        offset: float = 0.0,
        scale: float = 1.0,
    ):
        await filter_distortion(ctx, sin_offset, sin_scale, cos_offset, cos_scale, tan_offset, tan_scale, offset, scale)

    @commands.command()
    async def channelmix(
        self, ctx: commands.Context,
        left_to_left: float = 1.0,
        left_to_right: float = 0.0,
        right_to_left: float = 0.0,
        right_to_right: float = 1.0,
    ):
        await filter_channelmix(ctx, left_to_left, left_to_right, right_to_left, right_to_right)

    @commands.command()
    async def tremolo(self, ctx: commands.Context, frequency: float = 2.0, depth: float = 0.5):
        await filter_tremolo(ctx, frequency, depth)

    @commands.command()
    async def vibrato(self, ctx: commands.Context, frequency: float = 2.0, depth: float = 0.5):
        await filter_vibrato(ctx, frequency, depth)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogYouTubePlayerMin(bot))