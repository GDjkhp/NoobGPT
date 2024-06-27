import wavelink
from discord.ext import commands
from wavelink import Queue
from music import music_embed

class YouTubePlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = Queue()
        self.vc = None

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        await self.play_next_track()

    async def play_next_track(self):
        if not self.queue.is_empty:
            next_track = self.queue.get()
            await self.vc.play(next_track)
            embed = music_embed(title="🎵 Playing now", description=f'`{next_track.title}` is playing now.')
            await self.music_channel.send(embed=embed)

    @commands.command(name="p")
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        if not ctx.voice_client:
            self.vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            self.vc = ctx.voice_client
    
        tracks: list[wavelink.YouTubeTrack] = await wavelink.YouTubeTrack.search(search)
        if not tracks:
            await ctx.send(f'It was not possible to find the song: `{search}`')
            return
    
        track: wavelink.YouTubeTrack = tracks[0]
        self.queue.put(track)
        self.music_channel = ctx.message.channel
        if not self.vc.is_playing():
            await self.play_next_track()
        else:
            embed = music_embed(title="🎵 Song added to the queue.", description=f'`{track.title}` was added to the queue.')
            await ctx.send(embed=embed)

    @commands.command()
    async def stop(self, ctx: commands.Context) -> None:
        vc: wavelink.Player = ctx.voice_client
        await vc.stop()
        embed = music_embed(title="⏹️ Music stopped", description="The music has been stopped.")
        await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx: commands.Context) -> None:
        vc: wavelink.Player = ctx.voice_client
        await vc.pause()
        embed = music_embed(title="⏸️ Music paused", description="The music has been paused")
        await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx: commands.Context) -> None:
        vc: wavelink.Player = ctx.voice_client
        await vc.resume()
        embed = music_embed(title="▶️ Music Resumed", description="The music has been resumed.")
        await ctx.send(embed=embed)

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        vc: wavelink.Player = ctx.voice_client
        if not self.queue.is_empty:
            await vc.stop()
            next_track = self.queue.pop()
            await vc.play(next_track)
            embed = music_embed(title="⏭️ Song skipped", description=f'Playing the next song in the queue: `{next_track.title}`.')
            await ctx.send(embed=embed)
        else:
            await ctx.send("There are no songs in the queue to skip")

    @commands.command()
    async def list(self, ctx: commands.Context) -> None:
        if not self.queue:
            embed = music_embed(title="📜 Playlist", description="The queue is empty.")
            await ctx.send(embed=embed)
        else:
            queue_list = "\n".join([f"- {track.title}" for track in self.queue])
            embed = music_embed(title="📜 Playlist", description=queue_list)
            await ctx.send(embed=embed)

    @commands.command()
    async def disconnect(self, ctx: commands.Context) -> None:
        vc: wavelink.Player = ctx.voice_client
        await vc.disconnect()

async def setup(bot):
    await bot.add_cog(YouTubePlayer(bot))