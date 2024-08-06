import wavelink
from discord.ext import commands
from music import *
from util_discord import command_check

class YouTubePlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        vc: wavelink.Player = payload.player
        if not vc: return
        if not vc.queue.mode == wavelink.QueueMode.loop:
            embed = music_now_playing_embed(vc.current)
            await vc.music_channel.send(embed=embed)

    @commands.command(aliases=['mhelp'])
    async def music(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        texts = [
            "`-play <query>` Play music. Supports YouTube, Spotify, SoundCloud, Apple Music.",
            "`-search <query>` Search music. Defaults to YouTube.",
            "`-nowplaying` Now playing.",
            "`-pause` Pause music.",
            "`-resume` Resume music.",
            "`-skip` Skip music.",
            "`-stop` Stop music and disconnect from voice channel.",
            "`-list <page>` Show queue.",
            "`-shuffle` Shuffle queue.",
            "`-reset` Reset queue.",
            "`-peek` Peek track.",
            "`-remove <index>` Remove a track from the queue.",
            "`-replace <index> <query>` Replace track.",
            "`-swap <index1> <index2>` Swap tracks.",
            "`-move <index1> <index2>` Move track.",
            "`-loop <off/one/all>` Loop music modes.",
            "`-autoplay <partial/enabled/disabled>` Autoplay and recommended music modes.",
            "`-volume <value>` Set volume.",
            # "`-filters` Show available filters.",
            "`-summon` Join voice channel.",
            "`-dj` Create DJ role."
        ]
        await ctx.reply("\n".join(texts))

    @commands.command()
    async def dj(self, ctx: commands.Context):
        await set_dj_role(ctx)

    @commands.command()
    async def summon(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not ctx.author.voice:
            return await ctx.send(f'Join a voice channel first.')
        
        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            vc.autoplay = wavelink.AutoPlayMode.enabled

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, search: str=None):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc = ctx.voice_client
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await ctx.send(f'Join the voice channel with the bot first.')

        if not search: return await ctx.reply("usage: `-play <query>`")
        try: tracks = await wavelink.Playable.search(search)
        except Exception as e: return await ctx.send(f'Error :(\n{e}')
        if not tracks: return await ctx.send('No results found.')

        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            vc.autoplay = wavelink.AutoPlayMode.enabled
        vc.music_channel = ctx.message.channel
        
        if isinstance(tracks, wavelink.Playlist):
            added: int = await vc.queue.put_wait(tracks)
            text, desc = f"🎵 Added the playlist **`{tracks.name}`**", f'Added {added} songs to the queue.'
        else:
            await vc.queue.put_wait(tracks[0])
            text, desc = "🎵 Song added to the queue", f'`{tracks[0].title}` has been added to the queue.'
        embed = music_embed(text, desc)
        await ctx.send(embed=embed)
        if not vc.playing: await vc.play(vc.queue.get())

    @commands.command()
    async def search(self, ctx: commands.Context, *, search: str=None):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc = ctx.voice_client
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await ctx.send(f'Join the voice channel with the bot first.')

        if not search: return await ctx.reply("usage: `-search <query>`")
        try: tracks = await wavelink.Playable.search(search)
        except Exception as e: return await ctx.send(f'Error :(\n{e}')
        if not tracks: return await ctx.send('No results found.')
        await ctx.send(embed=search_embed(search_embed, tracks, 0), view=SearchView(ctx, search, tracks, 0))

    @commands.command(aliases=['die', 'dc'])
    async def stop(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        await vc.disconnect()
        embed = music_embed("⏹️ Music stopped", "The music has been stopped.")
        await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        await vc.pause(True)
        embed = music_embed("⏸️ Music paused", "The music has been paused")
        await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        await vc.pause(False)
        embed = music_embed("▶️ Music Resumed", "The music has been resumed.")
        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        if vc.queue.is_empty:
            if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
                vc.queue = vc.auto_queue.copy()
            else: return await ctx.send("There are no songs in the queue to skip")
        await vc.skip()

    @commands.command(aliases=['queue'])
    async def list(self, ctx: commands.Context, page: int=1):
        if not ctx.guild: return await ctx.reply("not supported")
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        current_queue = vc.queue
        if current_queue.is_empty:
            if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
                current_queue = vc.auto_queue
            else: return await ctx.send(embed=music_embed("📜 Playlist", "The queue is empty."))
        total = 0
        for t in current_queue: total += t.length
        index = page - 1  # page 1 = index 0
        items_per_page = 5
        queue_context = current_queue[index * items_per_page:(index + 1) * items_per_page]
        queue_list = "\n".join([f"{i + 1 + (items_per_page * index)}. `{track.title}` ({format_mil(track.length)})" for i, track in enumerate(queue_context)])
        embed = music_embed("📜 Playlist", queue_list)
        total_pages = (len(current_queue) + items_per_page - 1) // items_per_page
        embed.set_footer(text=f"Page {page}/{total_pages}, Queue: {len(current_queue)} ({format_mil(total)})")
        await ctx.send(embed=embed)

    @commands.command()
    async def loop(self, ctx: commands.Context, mode: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        if mode == 'off':
            vc.queue.mode = wavelink.QueueMode.normal
            text, desc = "❌ Loop disabled", "wavelink.QueueMode.normal"
        elif mode == 'one':
            vc.queue.mode = wavelink.QueueMode.loop
            text, desc = "🔂 Loop one", "wavelink.QueueMode.loop"
        elif mode == 'all':
            vc.queue.mode = wavelink.QueueMode.loop_all
            text, desc = "🔁 Loop all", "wavelink.QueueMode.loop_all"
        else:
            return await ctx.send("Mode not found.\nUsage: `-loop <off/one/all>`")
        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command()
    async def autoplay(self, ctx: commands.Context, mode: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')

        if mode == 'partial':
            vc.autoplay = wavelink.AutoPlayMode.partial
            text, desc = "❌ Recommendations disabled", "wavelink.AutoPlayMode.partial"
        elif mode == 'enabled':
            vc.autoplay = wavelink.AutoPlayMode.enabled
            text, desc = "✅ Recommendations enabled", "wavelink.AutoPlayMode.enabled"
        elif mode == 'disabled':
            vc.autoplay = wavelink.AutoPlayMode.disabled
            text, desc = "❌ Autoplay disabled", "wavelink.AutoPlayMode.disabled"
        else:
            return await ctx.send("Mode not found.\nUsage: `-autoplay <partial/enabled/disabled>`")
        embed = music_embed(text, desc)
        await ctx.send(embed=embed)

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if vc.playing: await ctx.send(embed=music_now_playing_embed(vc.current))

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        
        if vc.queue:
            vc.queue.shuffle()
            embed = music_embed("🔀 Queue has been shuffled", f"{len(vc.queue)} songs has been randomized.")
            await ctx.send(embed=embed)

    @commands.command()
    async def reset(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        vc.queue.reset()
        await ctx.send(embed=music_embed("🗑️ Reset queue", "Queue has been reset."))

    @commands.command()
    async def remove(self, ctx: commands.Context, index: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not vc.queue.is_empty:
            track = vc.queue.peek(min(int(index)-1, len(vc.queue)-1))
            vc.queue.remove(track)
            await ctx.send(embed=music_embed("🗑️ Remove track", f"`{track.title}` has been removed."))

    @commands.command()
    async def replace(self, ctx: commands.Context, index: str, *, query: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not vc.queue.is_empty:
            try: tracks = await wavelink.Playable.search(query)
            except Exception as e: return await ctx.send(f'Error :(\n{e}')
            if not tracks: return await ctx.send('No results found.')
            real_index = min(int(index)-1, len(vc.queue)-1)
            track = vc.queue.peek(real_index)
            vc.queue[real_index] = tracks[0]
            await ctx.send(embed=music_embed("➡️ Replace track", 
                                             f"`{track.title}` has been removed and `{tracks[0].title}` has been replaced."))

    @commands.command()
    async def swap(self, ctx: commands.Context, init: str, dest: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
        if not vc.queue.is_empty:
            index1 = min(int(init)-1, len(vc.queue)-1)
            index2 = min(int(dest)-1, len(vc.queue)-1)
            first = vc.queue.peek(index1)
            second = vc.queue.peek(index2)
            vc.queue.swap(index1, index2)
            await ctx.send(embed=music_embed("🔄 Swap tracks", 
                                             f"`{first.title}` is at position `{index2+1}` and `{second.title}` is at position `{index1+1}`."))

    @commands.command()
    async def peek(self, ctx: commands.Context, index: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
        if not vc.queue.is_empty:
            real_index = min(int(index)-1, len(vc.queue)-1)
            track = vc.queue.peek(real_index)
            await ctx.send(embed=music_embed("🎵 Track index", f"{real_index+1}. {track.title} ({format_mil(track.length)})"))

    @commands.command()
    async def move(self, ctx: commands.Context, init: str, dest: str):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
        if not vc.queue.is_empty:
            index1 = min(int(init)-1, len(vc.queue)-1)
            index2 = min(int(dest)-1, len(vc.queue)-1)
            track = vc.queue.peek(index1)
            vc.queue.remove(track)
            vc.queue.put_at(index2, track)
            await ctx.send(embed=music_embed("↕️ Move track", f"`{track.title}` is now at position `{index2+1}`."))

    @commands.command()
    async def volume(self, ctx: commands.Context, value:int=100):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return
        vc: wavelink.Player = ctx.voice_client
        if not vc: return
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.send(f'Join the voice channel with the bot first.')
        await vc.set_volume(value)
        await ctx.send(embed=music_embed(f"{'🔊' if value > 0 else '🔇'} Volume", f"Volume is now set to `{value}`"))

    # @commands.command()
    # async def filters(self, ctx: commands.Context, reset: str=None, filter: str=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if reset and reset == "reset":
    #         filters: wavelink.Filters = vc.filters
    #         if filter and filter in ["karaoke", "timescale", "lowpass", "rotation", "distortion", "channelmix", "tremolo", "vibrato"]:
    #             if filter == "karaoke":
    #                 filters.karaoke.reset()
    #             if filter == "timescale":
    #                 filters.timescale.reset()
    #             if filter == "lowpass":
    #                 filters.low_pass.reset()
    #             if filter == "rotation":
    #                 filters.rotation.reset()
    #             if filter == "distortion":
    #                 filters.distortion.reset()
    #             if filter == "channelmix":
    #                 filters.channel_mix.reset()
    #             if filter == "tremolo":
    #                 filters.tremolo.reset()
    #             if filter == "vibrato":
    #                 filters.vibrato.reset()
    #         else: filters.reset()
    #         await vc.set_filters(filters)
    #         return await ctx.reply("all filters have been reset")

    #     texts = [
    #         "`-karaoke <level> <mono_level> <filter_band> <filter_width>`",
    #         "`-timescale <pitch> <speed> <rate>`",
    #         "`-lowpass <smoothing>`",
    #         "`-rotation <rotation_hz>`",
    #         "`-distortion <sin_offset> <sin_scale> <cos_offset> <cos_scale> <tan_offset> <tan_scale> <offset> <scale>`",
    #         "`-channelmix <left_to_left> <left_to_right> <right_to_left> <right_to_right>`",
    #         "`-tremolo <frequency> <depth>`",
    #         "`-vibrato <frequency> <depth>`",
    #         "`-filters reset` will reset all filters",
    #         "`-filters reset <filter>` will reset specific filter"
    #     ]
    #     await ctx.reply("\n".join(texts))
    
    # @commands.command()
    # async def timescale(self, ctx: commands.Context, pitch:float=None, speed:float=None, rate:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.timescale.set(pitch=pitch, speed=speed, rate=rate)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Timescale", filters.timescale.payload))

    # @commands.command()
    # async def karaoke(self, ctx: commands.Context, level:float=None, mono_level:float=None, filter_band:float=None, filter_width:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.karaoke.set(level=level, mono_level=mono_level, filter_band=filter_band, filter_width=filter_width)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Karaoke", filters.karaoke.payload))

    # @commands.command()
    # async def lowpass(self, ctx: commands.Context, smoothing:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.low_pass.set(smoothing=smoothing)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Low Pass", filters.low_pass.payload))

    # @commands.command()
    # async def distortion(self, ctx: commands.Context, 
    #                      sin_offset:float=None, sin_scale:float=None, cos_offset:float=None, cos_scale:float=None, 
    #                      tan_offset:float=None, tan_scale:float=None, offset:float=None, scale:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.distortion.set(sin_offset=sin_offset, sin_scale=sin_scale, cos_offset=cos_offset, cos_scale=cos_scale, 
    #                            tan_offset=tan_offset, tan_scale=tan_scale, offset=offset, scale=scale)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Distortion", filters.distortion.payload))

    # @commands.command()
    # async def rotation(self, ctx: commands.Context, rotation_hz:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.rotation.set(rotation_hz=rotation_hz)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Rotation", filters.rotation.payload))

    # @commands.command()
    # async def channelmix(self, ctx: commands.Context, left_to_left:float=None, left_to_right:float=None, 
    #                      right_to_left:float=None, right_to_right:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.channel_mix.set(left_to_left=left_to_left, left_to_right=left_to_right, 
    #                             right_to_left=right_to_left, right_to_right=right_to_right)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Channel Mix", filters.channel_mix.payload))

    # @commands.command()
    # async def tremolo(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.tremolo.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Tremolo", filters.tremolo.payload))

    # @commands.command()
    # async def vibrato(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.send(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.vibrato.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.send(embed=filter_embed("🎚️ Filter", "Vibrato", filters.vibrato.payload))

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubePlayer(bot))