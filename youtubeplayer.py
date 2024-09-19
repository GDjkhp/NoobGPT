import wavelink
from discord.ext import commands
from discord import app_commands
from music import *
from util_discord import command_check, description_helper

async def music_help(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    texts = [
        "# Player commands",
        "`-play <query>` Play music. Supports YouTube, Spotify, SoundCloud, Apple Music.",
        "`-nowplaying` Now playing.",
        "`-pause` Pause music.",
        "`-resume` Resume music.",
        "`-skip` Skip music.",
        "`-stop` Stop music and disconnect from voice channel.",
        "`-volume <value>` Set volume.",
        "`-summon` Join voice channel.",
        "`-dj` Create DJ role.",
        "# Queue commands",
        "`-search <query>` Search music. Defaults to YouTube.",
        "`-list <page>` Show queue.",
        "`-shuffle` Shuffle queue.",
        "`-reset` Reset queue.",
        "`-peek` Peek track.",
        "`-remove <index>` Remove a track from the queue.",
        "`-replace <index> <query>` Replace track.",
        "`-swap <index1> <index2>` Swap tracks.",
        "`-move <index1> <index2>` Move track.",
        "`-repeat <off/one/all>` Repeat music modes.",
        "`-autoplay <partial/enabled/disabled>` Autoplay and recommended music modes.",
        # "`-filters` Show available filters.",
    ]
    await ctx.reply("\n".join(texts))

# player commands
async def music_summon(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not ctx.author.voice:
        return await ctx.reply(f'Join a voice channel first.')
    
    if not ctx.voice_client:
        try: vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except: 
            print("ChannelTimeoutException")
            await setup_hook_music(ctx.bot)
            return
        vc.autoplay = wavelink.AutoPlayMode.enabled

async def music_play(ctx: commands.Context | discord.Interaction, search: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return

    if not await check_if_dj(ctx):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("not a disc jockey")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("not a disc jockey")
        
    vc = ctx.guild.voice_client
    if isinstance(ctx, commands.Context):
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await ctx.reply(f'Join the voice channel with the bot first.')
    if isinstance(ctx, discord.Interaction):
        if not ctx.user.voice or (vc and not ctx.user.voice.channel == vc.channel):
            return await ctx.response.send_message(f'Join the voice channel with the bot first.')
        
    if not search:
        if isinstance(ctx, commands.Context):
            return await ctx.reply("usage: `-play <query>`")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("usage: `-play <query>`")
        
    try: tracks = await wavelink.Playable.search(search)
    except Exception as e:
        if isinstance(ctx, commands.Context):
            return await ctx.reply(f'Error :(\n{e}')
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(f'Error :(\n{e}')
        
    if not tracks:
        if isinstance(ctx, commands.Context):
            return await ctx.reply('No results found.')
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message('No results found.')

    if not ctx.guild.voice_client:
        try:
            if isinstance(ctx, commands.Context):
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            if isinstance(ctx, discord.Interaction):
                vc = await ctx.user.voice.channel.connect(cls=wavelink.Player)
        except: 
            print("ChannelTimeoutException")
            await setup_hook_music(ctx.bot)
            return
        vc.autoplay = wavelink.AutoPlayMode.enabled
    vc.music_channel = ctx.message.channel

    if isinstance(tracks, wavelink.Playlist):
        added: int = await vc.queue.put_wait(tracks)
        text, desc = f"🎵 Added the playlist **`{tracks.name}`**", f'Added {added} songs to the queue.'
    else:
        await vc.queue.put_wait(tracks[0])
        text, desc = "🎵 Song added to the queue", f'`{tracks[0].title}` has been added to the queue.'

    if not vc.playing: await vc.play(vc.queue.get())
    embed = music_embed(text, desc)
    if isinstance(ctx, commands.Context):
        await ctx.reply(embed=embed)
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(embed=embed)

async def music_pause(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

    await vc.pause(True)
    embed = music_embed("⏸️ Music paused", "The music has been paused")
    await ctx.reply(embed=embed)

async def music_resume(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

    await vc.pause(False)
    embed = music_embed("▶️ Music Resumed", "The music has been resumed.")
    await ctx.reply(embed=embed)

async def music_skip(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

    if vc.queue.is_empty:
        if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
            vc.queue = vc.auto_queue.copy()
        else: return await ctx.reply("There are no songs in the queue to skip")
    await vc.skip()

async def music_stop(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

    await vc.disconnect()
    embed = music_embed("⏹️ Music stopped", "The music has been stopped.")
    await ctx.reply(embed=embed)

async def music_nowplaying(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if vc.playing: await ctx.reply(embed=music_now_playing_embed(vc.current))

async def music_volume(ctx: commands.Context, value: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not value: value = "100"
    if not value.isdigit(): return await ctx.reply("not a digit :(")
    value: int = int(value)
    await vc.set_volume(value)
    await ctx.reply(embed=music_embed(f"{'🔊' if value > 0 else '🔇'} Volume", f"Volume is now set to `{value}`"))

# queue commands
async def queue_search(ctx: commands.Context | discord.Interaction, search: str, source: str="ytmsearch:"):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return

    if not await check_if_dj(ctx):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("not a disc jockey")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("not a disc jockey")
    
    vc = ctx.guild.voice_client
    if isinstance(ctx, commands.Context):
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await ctx.reply(f'Join the voice channel with the bot first.')
    if isinstance(ctx, discord.Interaction):
        if not ctx.user.voice or (vc and not ctx.user.voice.channel == vc.channel):
            return await ctx.response.send_message(f'Join the voice channel with the bot first.')

    if not search:
        if isinstance(ctx, commands.Context):
            return await ctx.reply("usage: `-search <query>`")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("usage: `-search <query>`")
    
    try: tracks = await wavelink.Playable.search(search, source=source)
    except Exception as e:
        if isinstance(ctx, commands.Context):
            return await ctx.reply(f'Error :(\n{e}')
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(f'Error :(\n{e}')
    
    if not tracks:
        if isinstance(ctx, commands.Context):
            return await ctx.reply('No results found.')
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message('No results found.')
    
    if isinstance(ctx, commands.Context):
        await ctx.reply(embed=search_embed(search, tracks, 0), view=SearchView(ctx, search, tracks, 0))
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(embed=search_embed(search, tracks, 0), view=SearchView(ctx, search, tracks, 0))

async def queue_list(ctx: commands.Context, page: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    current_queue = vc.queue
    if current_queue.is_empty:
        if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
            current_queue = vc.auto_queue
        else: return await ctx.reply(embed=music_embed("📜 Playlist", "The queue is empty."))
    if not page: page = "1"
    if not page.isdigit() or not int(page): return await ctx.reply("not a digit :(")
    page: int = int(page)
    total = 0
    for t in current_queue: total += t.length
    index = page - 1  # page 1 = index 0
    items_per_page = 5
    queue_context = current_queue[index * items_per_page:(index + 1) * items_per_page]
    queue_list = "\n".join([f"{i + 1 + (items_per_page * index)}. `{track.title}` ({format_mil(track.length)})" for i, track in enumerate(queue_context)])
    embed = music_embed("📜 Playlist", queue_list)
    total_pages = (len(current_queue) + items_per_page - 1) // items_per_page
    embed.set_footer(text=f"Page {page}/{total_pages}, Queue: {len(current_queue)} ({format_mil(total)})")
    await ctx.reply(embed=embed)

async def queue_loop(ctx: commands.Context, mode: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

    if mode == 'off':
        vc.queue.mode = wavelink.QueueMode.normal
        text, desc = "❌ Repeat disabled", "wavelink.QueueMode.normal"
    elif mode == 'one':
        vc.queue.mode = wavelink.QueueMode.loop
        text, desc = "🔂 Repeat one", "wavelink.QueueMode.loop"
    elif mode == 'all':
        vc.queue.mode = wavelink.QueueMode.loop_all
        text, desc = "🔁 Repeat all", "wavelink.QueueMode.loop_all"
    else:
        return await ctx.reply("Mode not found.\nUsage: `-repeat <off/one/all>`")
    embed = music_embed(text, desc)
    await ctx.reply(embed=embed)

async def queue_autoplay(ctx: commands.Context, mode: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')

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
        return await ctx.reply("Mode not found.\nUsage: `-autoplay <partial/enabled/disabled>`")
    embed = music_embed(text, desc)
    await ctx.reply(embed=embed)

async def queue_shuffle(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    
    if vc.queue:
        vc.queue.shuffle()
        embed = music_embed("🔀 Queue has been shuffled", f"{len(vc.queue)} songs has been randomized.")
        await ctx.reply(embed=embed)

async def queue_reset(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    vc.queue.reset()
    await ctx.reply(embed=music_embed("🗑️ Reset queue", "Queue has been reset."))

async def queue_remove(ctx: commands.Context, index: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if not vc.queue.is_empty:
        track = vc.queue.peek(min(int(index)-1, len(vc.queue)-1))
        vc.queue.remove(track)
        await ctx.reply(embed=music_embed("🗑️ Remove track", f"`{track.title}` has been removed."))

async def queue_replace(ctx: commands.Context, index: str, query: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if not vc.queue.is_empty:
        try: tracks = await wavelink.Playable.search(query)
        except Exception as e: return await ctx.reply(f'Error :(\n{e}')
        if not tracks: return await ctx.reply('No results found.')
        real_index = min(int(index)-1, len(vc.queue)-1)
        track = vc.queue.peek(real_index)
        vc.queue[real_index] = tracks[0]
        await ctx.reply(embed=music_embed("➡️ Replace track", 
                                            f"`{track.title}` has been removed and `{tracks[0].title}` has been replaced."))

async def queue_swap(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if not vc.queue.is_empty:
        index1 = min(int(init)-1, len(vc.queue)-1)
        index2 = min(int(dest)-1, len(vc.queue)-1)
        first = vc.queue.peek(index1)
        second = vc.queue.peek(index2)
        vc.queue.swap(index1, index2)
        await ctx.reply(embed=music_embed("🔄 Swap tracks", 
                                            f"`{first.title}` is at position `{index2+1}` and `{second.title}` is at position `{index1+1}`."))

async def queue_peek(ctx: commands.Context, index: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if not vc.queue.is_empty:
        real_index = min(int(index)-1, len(vc.queue)-1)
        track = vc.queue.peek(real_index)
        await ctx.reply(embed=music_embed("🎵 Track index", f"{real_index+1}. {track.title} ({format_mil(track.length)})"))

async def queue_move(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    vc: wavelink.Player = ctx.voice_client
    if not vc: return
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first.')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if not vc.queue.is_empty:
        index1 = min(int(init)-1, len(vc.queue)-1)
        index2 = min(int(dest)-1, len(vc.queue)-1)
        track = vc.queue.peek(index1)
        vc.queue.remove(track)
        vc.queue.put_at(index2, track)
        await ctx.reply(embed=music_embed("↕️ Move track", f"`{track.title}` is now at position `{index2+1}`."))

async def search_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    tracks = await wavelink.Playable.search(current)
    return [
        app_commands.Choice(name=track.title, value=track.uri) for track in tracks
    ]

async def search_auto_spotify(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    tracks = await wavelink.Playable.search(current, source="spsearch:")
    return [
        app_commands.Choice(name=track.title, value=track.uri) for track in tracks
    ]

async def mode_repeat_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["off", "one", "all"] if current.lower() in mode.lower()
    ]

async def mode_rec_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["partial", "enabled", "disabled"] if current.lower() in mode.lower()
    ]

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

    @commands.hybrid_command(description=f"{description_helper['emojis']['media']} {description_helper['media']['music']}")
    async def music(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Create DJ role")
    async def dj(self, ctx: commands.Context):
        await set_dj_role(ctx)

    # player
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Join voice channel")
    async def summon(self, ctx: commands.Context):
        await music_summon(ctx)

    @commands.command() # alias
    async def p(self, ctx: commands.Context, *, query: str=None):
        await music_play(ctx, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Play music. (YouTube Music)")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=search_auto)
    async def play(self, ctx: commands.Context, *, query:str=None):
        await music_play(ctx, query)

    @app_commands.command(name="play-spotify", description=f"{description_helper['emojis']['music']} Play music. (Spotify)")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=search_auto_spotify)
    async def play_spotify(self, ctx: discord.Interaction, *, query:str=None):
        await music_play(ctx, query)

    @commands.command(aliases=['die', 'dc']) # alias
    async def leave(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Stop music and disconnect from voice channel")
    async def stop(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Pause music")
    async def pause(self, ctx: commands.Context):
        await music_pause(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Resume music")
    async def resume(self, ctx: commands.Context):
        await music_resume(ctx)

    @commands.command() # alias
    async def s(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Skip music")
    async def skip(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.command() # alias
    async def np(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Now playing")
    async def nowplaying(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    # queue
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Search music. (YouTube Music)")
    async def search(self, ctx: commands.Context, *, query: str=None):
        await queue_search(ctx, query)

    @app_commands.command(name="search-spotify", description=f"{description_helper['emojis']['music']} Search music. (Spotify)")
    @app_commands.describe(query="Search query")
    async def search_spotify(self, ctx: discord.Interaction, *, query: str=None):
        await queue_search(ctx, query, "spsearch:")

    @commands.command() # alias
    async def queue(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Show queue")
    @app_commands.describe(page="Page number")
    async def list(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Repeat music modes")
    @app_commands.describe(mode="Repeat mode")
    @app_commands.autocomplete(mode=mode_repeat_auto)
    async def repeat(self, ctx: commands.Context, mode: str):
        await queue_loop(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Autoplay and recommended music modes")
    @app_commands.describe(mode="Autoplay mode")
    @app_commands.autocomplete(mode=mode_rec_auto)
    async def autoplay(self, ctx: commands.Context, mode: str):
        await queue_autoplay(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Shuffle queue")
    async def shuffle(self, ctx: commands.Context):
        await queue_shuffle(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Reset queue")
    async def reset(self, ctx: commands.Context):
        await queue_reset(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Remove a track from the queue")
    @app_commands.describe(index="Track number you want to remove (Must be a valid integer)")
    async def remove(self, ctx: commands.Context, index: str):
        await queue_remove(ctx, index)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Replace track")
    @app_commands.describe(index="Track number you want to replace (Must be a valid integer)", query="Search query")
    async def replace(self, ctx: commands.Context, index: str, *, query: str):
        await queue_replace(ctx, index, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Swap tracks")
    @app_commands.describe(init="First track number you want to swap into (Must be a valid integer)",
                           dest="Second track number you want to swap into (Must be a valid integer)")
    async def swap(self, ctx: commands.Context, init: str, dest: str):
        await queue_swap(ctx, init, dest)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Peek track")
    @app_commands.describe(index="Track number you want to peek into (Must be a valid integer)")
    async def peek(self, ctx: commands.Context, index: str):
        await queue_peek(ctx, index)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Move track")
    @app_commands.describe(init="Track number you want to move from (Must be a valid integer)",
                           dest="Track number you want to move to (Must be a valid integer)")
    async def move(self, ctx: commands.Context, init: str, dest: str):
        await queue_move(ctx, init, dest)

    # filter
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Set volume")
    @app_commands.describe(value="Set value (Must be a valid integer: 0-100)")
    async def volume(self, ctx: commands.Context, value: str=None):
        await music_volume(ctx, value)

    # @commands.hybrid_command(description="")
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
    
    # @commands.hybrid_command(description="")
    # async def timescale(self, ctx: commands.Context, pitch:float=None, speed:float=None, rate:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.timescale.set(pitch=pitch, speed=speed, rate=rate)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Timescale", filters.timescale.payload))

    # @commands.hybrid_command(description="")
    # async def karaoke(self, ctx: commands.Context, level:float=None, mono_level:float=None, filter_band:float=None, filter_width:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.karaoke.set(level=level, mono_level=mono_level, filter_band=filter_band, filter_width=filter_width)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Karaoke", filters.karaoke.payload))

    # @commands.hybrid_command(description="")
    # async def lowpass(self, ctx: commands.Context, smoothing:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.low_pass.set(smoothing=smoothing)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Low Pass", filters.low_pass.payload))

    # @commands.hybrid_command(description="")
    # async def distortion(self, ctx: commands.Context, 
    #                      sin_offset:float=None, sin_scale:float=None, cos_offset:float=None, cos_scale:float=None, 
    #                      tan_offset:float=None, tan_scale:float=None, offset:float=None, scale:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.distortion.set(sin_offset=sin_offset, sin_scale=sin_scale, cos_offset=cos_offset, cos_scale=cos_scale, 
    #                            tan_offset=tan_offset, tan_scale=tan_scale, offset=offset, scale=scale)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Distortion", filters.distortion.payload))

    # @commands.hybrid_command(description="")
    # async def rotation(self, ctx: commands.Context, rotation_hz:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.rotation.set(rotation_hz=rotation_hz)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Rotation", filters.rotation.payload))

    # @commands.hybrid_command(description="")
    # async def channelmix(self, ctx: commands.Context, left_to_left:float=None, left_to_right:float=None, 
    #                      right_to_left:float=None, right_to_right:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.channel_mix.set(left_to_left=left_to_left, left_to_right=left_to_right, 
    #                             right_to_left=right_to_left, right_to_right=right_to_right)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Channel Mix", filters.channel_mix.payload))

    # @commands.hybrid_command(description="")
    # async def tremolo(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.tremolo.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Tremolo", filters.tremolo.payload))

    # @commands.hybrid_command(description="")
    # async def vibrato(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first.')

    #     filters: wavelink.Filters = vc.filters
    #     filters.vibrato.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Vibrato", filters.vibrato.payload))

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubePlayer(bot))