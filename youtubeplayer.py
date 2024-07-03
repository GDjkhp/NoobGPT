import wavelink
from discord.ext import commands
from music import music_embed, music_now_playing_embed
from util_discord import command_check

class YouTubePlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = None

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        if not self.vc.queue.mode == wavelink.QueueMode.loop and self.vc.queue:
            embed = music_now_playing_embed(self.vc.queue[0])
            await self.music_channel.send(embed=embed)

    @commands.command(name="p")
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        if not ctx.voice_client:
            self.vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            self.vc.autoplay = wavelink.AutoPlayMode.enabled
        else: self.vc = ctx.voice_client

        tracks = await wavelink.Playable.search(search)
        if not tracks:
            await ctx.send(f'No results found.')
            return

        self.music_channel = ctx.message.channel
        if isinstance(tracks, wavelink.Playlist):
            added: int = await self.vc.queue.put_wait(tracks)
            text, desc = f"🎵 Added the playlist **`{tracks.name}`**", f'Added {added} songs to the queue.'
        else:
            track = tracks[0]
            await self.vc.queue.put_wait(track)
            text, desc = "🎵 Song added to the queue", f'`{track.title}` has been added to the queue.'
        if not self.vc.playing: await self.vc.play(self.vc.queue.get())

        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        await vc.stop()
        embed = music_embed("⏹️ Music stopped", "The music has been stopped.")
        await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        await vc.pause(True)
        embed = music_embed("⏸️ Music paused", "The music has been paused")
        await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        await vc.pause(False)
        embed = music_embed("▶️ Music Resumed", "The music has been resumed.")
        await ctx.send(embed=embed)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        if not self.vc.queue.is_empty:
            await vc.stop()
            next_track = self.vc.queue.get()
            await vc.play(next_track)
            embed = music_embed("⏭️ Song skipped", f'Playing the next song in the queue: `{next_track.title}`.')
            await ctx.send(embed=embed)
        else:
            await ctx.send("There are no songs in the queue to skip")

    @commands.command()
    async def list(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return

        if not self.vc.queue:
            embed = music_embed("📜 Playlist", "The queue is empty.")
            await ctx.send(embed=embed)
        else:
            queue_list = "\n".join([f"- {track.title}" for track in self.vc.queue])
            embed = music_embed("📜 Playlist", queue_list)
            await ctx.send(embed=embed)

    @commands.command(name="die")
    async def disconnect(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        if vc: await vc.disconnect()

    @commands.command()
    async def loop(self, ctx: commands.Context, mode: str):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        if mode == 'off':
            self.vc.queue.mode = wavelink.QueueMode.normal
            text, desc = "❌ Loop disabled", "wavelink.QueueMode.normal"
        elif mode == 'one':
            self.vc.queue.mode = wavelink.QueueMode.loop
            text, desc = "🔂 Loop one", "wavelink.QueueMode.loop"
        elif mode == 'all':
            self.vc.queue.mode = wavelink.QueueMode.loop_all
            text, desc = "🔁 Loop all", "wavelink.QueueMode.loop_all"
        else:
            await ctx.send("Mode not found.\nUsage: `-loop <off/one/all>`")
            return
        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command()
    async def autoplay(self, ctx: commands.Context, mode: str):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        if mode == 'partial':
            self.vc.autoplay = wavelink.AutoPlayMode.partial
            text, desc = "❌ Recommendations disabled", "wavelink.AutoPlayMode.partial"
        elif mode == 'enabled':
            self.vc.autoplay = wavelink.AutoPlayMode.enabled
            text, desc = "✅ Recommendations enabled", "wavelink.AutoPlayMode.enabled"
        elif mode == 'disabled':
            self.vc.autoplay = wavelink.AutoPlayMode.disabled
            text, desc = "❌ Autoplay disabled", "wavelink.AutoPlayMode.disabled"
        else:
            await ctx.send("Mode not found.\nUsage: `-autoplay <partial/enabled/disabled>`")
            return
        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command(name="np")
    async def nowplaying(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if self.vc.playing: await ctx.send(embed=music_now_playing_embed(self.vc.current))

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        
        if self.vc.queue:
            self.vc.queue.shuffle()
            embed = music_embed("🔀 Queue has been shuffled", f"{len(self.vc.queue)} songs has been randomized.")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def summon(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not ctx.voice_client:
            self.vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else: self.vc = ctx.voice_client

    # TODO: dj role, filters, queue ops (move, delete, remove, swap, put at, peek)

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubePlayer(bot))