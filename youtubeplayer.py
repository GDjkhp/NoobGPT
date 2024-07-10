import wavelink
from discord.ext import commands
from music import music_embed, music_now_playing_embed, check_if_dj, format_mil
from util_discord import command_check

class YouTubePlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = None

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        if not self.vc.queue.mode == wavelink.QueueMode.loop:
            embed = music_now_playing_embed(self.vc.current)
            await self.music_channel.send(embed=embed)

    @commands.command(aliases=['mhelp'])
    async def music(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        texts = [
            "`-play <query>` Play music. Supports YouTube, Spotify, SoundCloud, Apple Music.",
            "`-nowplaying` Now playing.",
            "`-pause` Pause music.",
            "`-resume` Resume music.",
            "`-skip` Skip music.",
            "`-stop` Stop music and disconnect from voice channel.",
            "`-list` Show queue.",
            "`-shuffle` Shuffle queue.",
            "`-reset` Reset queue.",
            "`-peek` Peek track.",
            "`-remove <index>` Remove a track from the queue.",
            "`-replace <index> <query>` Replace track.",
            "`-swap <index1> <index2>` Swap tracks.",
            "`-move <index1> <index2>` Move track.",
            "`-loop <off/one/all>` Loop music modes.",
            "`-autoplay <partial/enabled/disabled>` Autoplay and recommended music modes.",
            "`-summon` Join voice channel.",
            "`-dj` Create DJ role."
        ]
        await ctx.reply("\n".join(texts))

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        if not ctx.voice_client:
            self.vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            self.vc.autoplay = wavelink.AutoPlayMode.enabled
        else: self.vc = ctx.voice_client

        try: tracks = await wavelink.Playable.search(search)
        except Exception as e: return await ctx.send(f'Error :(\n{e}')
        if not tracks: return await ctx.send('No results found.')

        self.music_channel = ctx.message.channel
        if isinstance(tracks, wavelink.Playlist):
            added: int = await self.vc.queue.put_wait(tracks)
            text, desc = f"🎵 Added the playlist **`{tracks.name}`**", f'Added {added} songs to the queue.'
        else:
            await self.vc.queue.put_wait(tracks[0])
            text, desc = "🎵 Song added to the queue", f'`{tracks[0].title}` has been added to the queue.'
        if not self.vc.playing: await self.vc.play(self.vc.queue.get())

        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command(aliases=['die'])
    async def stop(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        if vc: await vc.disconnect()
        embed = music_embed("⏹️ Music stopped", "The music has been stopped.")
        await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
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
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        await vc.pause(False)
        embed = music_embed("▶️ Music Resumed", "The music has been resumed.")
        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')

        vc: wavelink.Player = ctx.voice_client
        if self.vc.queue.is_empty:
            if self.vc.autoplay == wavelink.AutoPlayMode.enabled and not self.vc.auto_queue.is_empty:
                self.vc.queue = self.vc.auto_queue.copy()
            else: return await ctx.send("There are no songs in the queue to skip")
        await vc.skip()

    @commands.command(aliases=['queue'])
    async def list(self, ctx: commands.Context):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if await command_check(ctx, "music", "media"): return

        current_queue = self.vc.queue
        if current_queue.is_empty:
            if self.vc.autoplay == wavelink.AutoPlayMode.enabled and not self.vc.auto_queue.is_empty:
                current_queue = self.vc.auto_queue
            else: return await ctx.send(embed=music_embed("📜 Playlist", "The queue is empty."))
        total = 0
        for t in current_queue: total += t.length
        queue_list = "\n".join([f"- {track.title} ({format_mil(track.length)})" for track in current_queue[:5]]) # TODO: queue paging
        embed = music_embed("📜 Playlist", queue_list)
        embed.set_footer(text=f"Queue: {len(current_queue)} ({format_mil(total)})")
        await ctx.send(embed=embed)

    @commands.command()
    async def loop(self, ctx: commands.Context, mode: str):
        if not self.vc: return
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
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
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
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

    @commands.command(aliases=['np'])
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
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
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
            self.vc.autoplay = wavelink.AutoPlayMode.enabled
        else: self.vc = ctx.voice_client

    @commands.command()
    async def reset(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        self.vc.queue.reset()
        await ctx.send(embed=music_embed("🗑️ Reset queue", "Queue has been reset."))

    @commands.command()
    async def remove(self, ctx: commands.Context, index: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not self.vc.queue.is_empty:
            track = self.vc.queue.peek(min(int(index)-1, len(self.vc.queue)-1))
            self.vc.queue.remove(track)
            await ctx.send(embed=music_embed("🗑️ Remove track", f"`{track.title}` has been removed."))

    @commands.command()
    async def replace(self, ctx: commands.Context, index: str, *, query: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not self.vc.queue.is_empty:
            try: tracks = await wavelink.Playable.search(query)
            except Exception as e: return await ctx.send(f'Error :(\n{e}')
            if not tracks: return await ctx.send('No results found.')
            real_index = min(int(index)-1, len(self.vc.queue)-1)
            track = self.vc.queue.peek(real_index)
            self.vc.queue[real_index] = tracks[0]
            await ctx.send(embed=music_embed("➡️ Replace track", 
                                             f"`{track.title}` has been removed and `{tracks[0].title}` has been replaced."))

    @commands.command()
    async def swap(self, ctx: commands.Context, init: str, dest: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
        if not self.vc.queue.is_empty:
            index1 = min(int(init)-1, len(self.vc.queue)-1)
            index2 = min(int(dest)-1, len(self.vc.queue)-1)
            first = self.vc.queue.peek(index1)
            second = self.vc.queue.peek(index2)
            self.vc.queue.swap(index1, index2)
            await ctx.send(embed=music_embed("🔄 Swap tracks", 
                                             f"`{first.title}` is at position `{index2+1}` and `{second.title}` is at position `{index1+1}`."))

    @commands.command()
    async def peek(self, ctx: commands.Context, index: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not self.vc.queue.is_empty:
            real_index = min(int(index)-1, len(self.vc.queue)-1)
            track = self.vc.queue.peek(real_index)
            await ctx.send(embed=music_embed("🎵 Track index", f"{real_index+1}. {track.title} ({format_mil(track.length)})"))

    @commands.command()
    async def move(self, ctx: commands.Context, init: str, dest: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice: return await ctx.send(f'Join a voice channel first.')
        if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
        if not self.vc.queue.is_empty:
            index1 = min(int(init)-1, len(self.vc.queue)-1)
            index2 = min(int(dest)-1, len(self.vc.queue)-1)
            track = self.vc.queue.peek(index1)
            self.vc.queue.remove(track)
            self.vc.queue.put_at(index2, track)
            await ctx.send(embed=music_embed("↕️ Move track", f"`{track.title}` is now at position `{index2+1}`."))

    # TODO: filters

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubePlayer(bot))