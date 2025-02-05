import wavelink
from discord.ext import commands
from discord import app_commands
from youtubeplayer import *
from util_discord import description_helper

# min_music for noobgpt (only essential commands)
# list np play pause resume stop skip autoplay shuffle remove clear dj repeat swap replace move
class YouTubePlayerMin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        vc: wavelink.Player = payload.player
        if not vc: return
        if not vc.queue.mode == wavelink.QueueMode.loop:
            embed = music_now_playing_embed(self.bot, vc.current)
            await vc.music_channel.send(embed=embed)

    @commands.command(name="mreset")
    async def reset(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        n: wavelink.Node = wavelink.Pool.get_node(identifier=self.bot.node_id)
        if n: await n.close(eject=True)
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

    # queue
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

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['remove']}")
    @app_commands.describe(index="Track number you want to remove (Must be a valid integer)")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def remove(self, ctx: commands.Context, index: str):
        await queue_remove(ctx, index)

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

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubePlayerMin(bot))