import wavelink
from discord.ext import commands
from discord import app_commands
from music import *
from help import HALP_MOOSIC
from util_discord import command_check, description_helper, get_guild_prefix

async def music_help(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    await HALP_MOOSIC(ctx)

# player commands
async def music_summon(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not ctx.author.voice:
        return await ctx.reply(f'Join a voice channel first')
    perms = ctx.author.voice.channel.permissions_for(ctx.me)
    if not perms.connect or not perms.speak:
        return await ctx.reply(content="i do not have **connect** or **speak** perms")

    if ctx.voice_client: return await ctx.reply(f"I'm already connected to {ctx.voice_client.channel.jump_url}\nPlease use a different bot (>_<)")
    try:
        vc = await voice_channel_connector(ctx)
    except:
        # if fixing: return await ctx.reply(content="Please try again later")
        print("ChannelTimeoutException")
        msg=await ctx.reply(content="An error occured. Reconnecting…")
        await setup_hook_music(ctx.bot)
        return await msg.edit(content="Please re-run the command")
    vc.autoplay = wavelink.AutoPlayMode.enabled
    await ctx.reply(f"Connected to {vc.channel.jump_url}")

async def music_play(bot: commands.Bot, ctx: commands.Context | discord.Interaction, search: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx):
        if isinstance(ctx, commands.Context): return await ctx.reply("use moosic instead :)", ephemeral=True)
        if isinstance(ctx, discord.Interaction): return await ctx.response.send_message("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)

    if isinstance(ctx, discord.Interaction): 
        await ctx.response.send_message("Loading…")
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply("Loading…")

    if not await check_if_dj(ctx):
        if isinstance(ctx, commands.Context):
            return await msg.edit(content="not a disc jockey and/or in music spam channel")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content="not a disc jockey and/or in music spam channel")

    vc = ctx.guild.voice_client
    if isinstance(ctx, commands.Context):
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await msg.edit(content='Join the voice channel with the bot first')
    if isinstance(ctx, discord.Interaction):
        if not ctx.user.voice or (vc and not ctx.user.voice.channel == vc.channel):
            return await ctx.edit_original_response(content='Join the voice channel with the bot first')

    if isinstance(ctx, discord.Interaction):
        perms = ctx.user.voice.channel.permissions_for(ctx.guild.me)
        if not perms.connect or not perms.speak:
            return await ctx.edit_original_response(content="i do not have **connect** or **speak** perms")
    if isinstance(ctx, commands.Context):
        perms = ctx.author.voice.channel.permissions_for(ctx.me)
        if not perms.connect or not perms.speak:
            return await msg.edit(content="i do not have **connect** or **speak** perms")

    if not search:
        p = await get_guild_prefix(ctx)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"usage: `{p}play <query>`")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"usage: `{p}play <query>`")

    try:
        tracks = await wavelink.Playable.search(search)
    except Exception as e:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f'Error :(\n{e}')
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f'Error :(\n{e}')

    if not tracks:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content='No results found')
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content='No results found')

    for track in tracks:
        if isinstance(ctx, commands.Context):
            track.extras = {"requester": ctx.author.id}
        if isinstance(ctx, discord.Interaction):
            track.extras = {"requester": ctx.user.id}

    if not ctx.guild.voice_client:
        try:
            vc = await voice_channel_connector(ctx)
        except:
            # if fixing: 
            #     if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="Please try again later")
            #     if isinstance(ctx, commands.Context): return await msg.edit(content="Please try again later")
            print("ChannelTimeoutException")
            if isinstance(ctx, discord.Interaction): await ctx.edit_original_response(content="An error occured. Reconnecting…")
            if isinstance(ctx, commands.Context): await msg.edit(content="An error occured. Reconnecting…")
            await setup_hook_music(bot)
            if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="Please re-run the command")
            if isinstance(ctx, commands.Context): return await msg.edit(content="Please re-run the command")

        vc.autoplay = wavelink.AutoPlayMode.enabled
    vc.music_channel = ctx.channel

    if isinstance(tracks, wavelink.Playlist):
        added: int = await vc.queue.put_wait(tracks)
        text, desc = f"🎵 Queue playlist", f'Added `{added}` songs to the queue'
        embed = music_embed(text, desc)
        embed.add_field(name="Name", value=f"[{tracks.name}]({tracks.url})" if tracks.url else tracks.name, inline=False)
        embed.add_field(name="Author", value=tracks.author, inline=False)
        embed.add_field(name="Type", value=tracks.type, inline=False)
        if tracks.artwork: embed.set_thumbnail(url=tracks.artwork)
    else:
        await vc.queue.put_wait(tracks[0])
        text, desc = "🎵 Play music", f'`{tracks[0].author} - {tracks[0].title}` has been added to the queue at position `{len(vc.queue)}`'
        embed = music_embed(text, desc)
    if not vc.playing: await vc.play(vc.queue.get())
    if isinstance(ctx, commands.Context):
        await msg.edit(content=None, embed=embed)
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(embed=embed, content=None)

async def music_pause(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    await vc.pause(True)
    embed = music_embed("⏸️ Pause music", "The music has been paused")
    await ctx.reply(embed=embed)

async def music_resume(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    await vc.pause(False)
    embed = music_embed("▶️ Resume music", "The music has been resumed")
    await ctx.reply(embed=embed)

async def music_skip(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if vc.queue.is_empty:
        if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
            for x in vc.auto_queue:
                await vc.queue.put_wait(x)
            vc.auto_queue.reset()
        else: return await ctx.reply("There are no songs in the queue to skip")
    await ctx.reply(embed=music_embed("⏭️ Skip music", f"`{vc.current.author} - {vc.current.title}` has been skipped"))
    await vc.skip()

async def music_stop(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    await vc.disconnect()
    embed = music_embed("⏹️ Stop music", "The music has been stopped")
    await ctx.reply(embed=embed)

async def music_nowplaying(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if vc.playing: await ctx.reply(embed=music_now_playing_embed(ctx.bot, vc.current))

async def music_volume(ctx: commands.Context, value: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not value: value = "100"
    if not value.isdigit(): return await ctx.reply("not a digit :(")
    value: int = int(value)
    await vc.set_volume(value)
    await ctx.reply(embed=music_embed(f"{'🔊' if value > 0 else '🔇'} Volume", f"Volume is now set to `{value}`"))

# queue commands
async def queue_search(bot: commands.Bot, ctx: commands.Context | discord.Interaction, search: str, source: str="ytmsearch:"):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx):
        if isinstance(ctx, commands.Context): return await ctx.reply("use moosic instead :)", ephemeral=True)
        if isinstance(ctx, discord.Interaction): return await ctx.response.send_message("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): 
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)

    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message("Loading…")
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply("Loading…")

    if not await check_if_dj(ctx):
        if isinstance(ctx, commands.Context):
            return await msg.edit(content="not a disc jockey and/or in music spam channel")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content="not a disc jockey and/or in music spam channel")

    vc = ctx.guild.voice_client
    if isinstance(ctx, commands.Context):
        if not ctx.author.voice or (vc and not ctx.author.voice.channel == vc.channel):
            return await msg.edit(content='Join the voice channel with the bot first')
    if isinstance(ctx, discord.Interaction):
        if not ctx.user.voice or (vc and not ctx.user.voice.channel == vc.channel):
            return await ctx.edit_original_response(content='Join the voice channel with the bot first')

    if not search:
        p = await get_guild_prefix(ctx)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"usage: `{p}search <query>`")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"usage: `{p}search <query>`")

    try:
        tracks = await wavelink.Playable.search(search, source=source)
    except Exception as e:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f'Error :(\n{e}')
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f'Error :(\n{e}')

    if not tracks:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content='No results found')
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content='No results found')

    if isinstance(ctx, commands.Context):
        await msg.edit(content=None, embed=search_embed(search, tracks, 0), view=SearchView(bot, ctx, search, tracks, 0))
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(embed=search_embed(search, tracks, 0), view=SearchView(bot, ctx, search, tracks, 0), content=None)

async def queue_list(ctx: commands.Context, page: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    current_queue = vc.queue
    if current_queue.is_empty:
        if vc.autoplay == wavelink.AutoPlayMode.enabled and not vc.auto_queue.is_empty:
            current_queue = vc.auto_queue
        else: return await ctx.reply(embed=music_embed("📜 Playlist", "The queue is empty"))
    if not page: page = "1"
    if not page.isdigit(): return await ctx.reply("not a digit :(")
    page: int = int(page)
    total = sum(t.length for t in current_queue)
    items_per_page = 5
    total_pages = (len(current_queue) + items_per_page - 1) // items_per_page
    page = max(1, min(page, total_pages)) # Redirect to last page if requested page is out of range
    index = page - 1  # page 1 = index 0
    queue_context = current_queue[index * items_per_page:(index + 1) * items_per_page]
    queue_list = "\n".join([f"{i + 1 + (items_per_page * index)}. `{track.author} - {track.title}` ({format_mil(track.length)}) - {requester_string(ctx.bot, track)}" for i, track in enumerate(queue_context)])
    embed = music_embed("📜 Playlist", queue_list)
    embed.set_footer(text=f"Page {page}/{total_pages}, Queue: {len(current_queue)} ({format_mil(total)})")
    await ctx.reply(embed=embed)

async def queue_loop(ctx: commands.Context, mode: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if mode == 'off':
        vc.queue.mode = wavelink.QueueMode.normal
        text, desc = "❌ Repeat off", "Queue mode is now set to normal"
    elif mode == 'one':
        vc.queue.mode = wavelink.QueueMode.loop
        text, desc = "🔂 Repeat one", "Queue mode is now set to loop"
    elif mode == 'all':
        vc.queue.mode = wavelink.QueueMode.loop_all
        text, desc = "🔁 Repeat all", "Queue mode is now set to loop all"
    else:
        return await ctx.reply(f"Mode not found.\nUsage: `{await get_guild_prefix(ctx)}repeat <off/one/all>`")
    embed = music_embed(text, desc)
    await ctx.reply(embed=embed)

async def queue_autoplay(ctx: commands.Context, mode: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if mode == 'partial':
        vc.autoplay = wavelink.AutoPlayMode.partial
        text, desc = "❌ Recommendations disabled", "Autoplay mode is now set to partial"
    elif mode == 'enabled':
        vc.autoplay = wavelink.AutoPlayMode.enabled
        text, desc = "✅ Recommendations enabled", "Autoplay mode is now enabled"
    elif mode == 'disabled':
        vc.autoplay = wavelink.AutoPlayMode.disabled
        text, desc = "❌ Autoplay disabled", "Autoplay mode is now disabled"
    else:
        return await ctx.reply(f"Mode not found.\nUsage: `{await get_guild_prefix(ctx)}autoplay <partial/enabled/disabled>`")
    embed = music_embed(text, desc)
    await ctx.reply(embed=embed)

async def queue_shuffle(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🔀 Shuffle queue", "The queue is empty"))
    vc.queue.shuffle()
    embed = music_embed("🔀 Shuffle queue", f"`{len(vc.queue)}` songs have been randomized")
    await ctx.reply(embed=embed)

async def queue_reset(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    vc.queue.reset()
    vc.auto_queue.reset()
    await ctx.reply(embed=music_embed("🗑️ Clear queue", "The queue has been emptied"))

async def queue_remove(ctx: commands.Context, index: str = None, index2: str = None, member: str = None):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🗑️ Remove track", "The queue is empty"))

    # Handle removal by member/requester
    if member:
        tracks_to_remove = []

        # Handle bot recommendations
        if member.lower() == "bot":
            # Find all tracks with no requester (bot recommendations)
            for i in range(len(vc.queue)):
                track = vc.queue.peek(i)
                track_requester = dict(track.extras).get("requester")
                if not track_requester:
                    tracks_to_remove.append(track)

            if not tracks_to_remove:
                return await ctx.reply(embed=music_embed("🗑️ Remove tracks", "No bot recommendations found in queue"))

            # Remove tracks
            for track in tracks_to_remove:
                vc.queue.remove(track)

            count = len(tracks_to_remove)
            await ctx.reply(embed=music_embed("🗑️ Remove tracks", f"Removed {count} bot recommendation{'s' if count != 1 else ''}"))
            return

        # Try to get member object from string (could be ID or mention)
        member_obj = None
        try:
            # If it's a digit, treat as user ID
            if member.isdigit():
                member_obj = ctx.guild.get_member(int(member))
            # If it's a mention, extract ID
            elif member.startswith('<@') and member.endswith('>'):
                member_id = member[2:-1].replace('!', '')
                member_obj = ctx.guild.get_member(int(member_id))
        except:
            pass

        if not member_obj:
            return await ctx.reply("Member not found")

        member_id = str(member_obj.id)

        # Find all tracks queued by the specified member
        for i in range(len(vc.queue)):
            track = vc.queue.peek(i)
            track_requester = dict(track.extras).get("requester")
            if track_requester and str(track_requester) == member_id:
                tracks_to_remove.append(track)

        if not tracks_to_remove:
            return await ctx.reply(embed=music_embed("🗑️ Remove tracks", f"No tracks found queued by {member_obj.display_name}"))

        # Remove tracks
        for track in tracks_to_remove:
            vc.queue.remove(track)

        count = len(tracks_to_remove)
        await ctx.reply(embed=music_embed("🗑️ Remove tracks", f"Removed {count} track{'s' if count != 1 else ''} queued by {member_obj.display_name}"))
        return

    # Require index if not removing by member
    if not index:
        return await ctx.reply(f"Please provide an index or specify a member\nUsage: `{await get_guild_prefix(ctx)}remove <index/member>`")

    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")

    # Handle range removal if index2 is provided
    if index2:
        if not index2.isdigit() or not int(index2): return await ctx.reply("index2 is not a digit :(")

        # Convert to 0-based indexing
        start_idx = int(index) - 1
        end_idx = int(index2) - 1

        # Ensure indices are within bounds
        start_idx = max(0, min(start_idx, len(vc.queue) - 1))
        end_idx = max(0, min(end_idx, len(vc.queue) - 1))

        # Ensure start_idx <= end_idx
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        # Get tracks to remove
        tracks_to_remove = []
        for i in range(start_idx, end_idx + 1):
            tracks_to_remove.append(vc.queue.peek(i))

        # Remove tracks (remove in reverse order to maintain indices)
        for track in reversed(tracks_to_remove):
            vc.queue.remove(track)

        count = len(tracks_to_remove)
        await ctx.reply(embed=music_embed("🗑️ Remove tracks", f"Removed {count} track{'s' if count != 1 else ''} from position {int(index)} to {int(index2)}"))

    # Handle single track removal
    else:
        track = vc.queue.peek(min(int(index)-1, len(vc.queue)-1))
        vc.queue.remove(track)
        await ctx.reply(embed=music_embed("🗑️ Remove track", f"`{track.author} - {track.title}` has been removed"))

async def queue_replace(ctx: commands.Context, index: str, query: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("➡️ Replace track", "The queue is empty"))
    try: tracks = await wavelink.Playable.search(query)
    except Exception as e: return await ctx.reply(f'Error :(\n{e}')
    if not tracks: return await ctx.reply('No results found')
    real_index = min(int(index)-1, len(vc.queue)-1)
    track = vc.queue.peek(real_index)
    vc.queue[real_index] = tracks[0]
    await ctx.reply(embed=music_embed("➡️ Replace track", f"`{track.author} - {track.title}` has been removed and `{tracks[0].author} - {tracks[0].title}` has been replaced"))

async def queue_swap(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🔄 Swap tracks", "The queue is empty"))
    index1 = min(int(init)-1, len(vc.queue)-1)
    index2 = min(int(dest)-1, len(vc.queue)-1)
    first = vc.queue.peek(index1)
    second = vc.queue.peek(index2)
    vc.queue.swap(index1, index2)
    await ctx.reply(embed=music_embed("🔄 Swap tracks", f"`{first.author} - {first.title}` is at position `{index2+1}` and `{second.author} - {second.title}` is at position `{index1+1}`"))

async def queue_peek(ctx: commands.Context, index: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🎵 Track index", "The queue is empty"))
    real_index = min(int(index)-1, len(vc.queue)-1)
    track = vc.queue.peek(real_index)
    await ctx.reply(embed=music_embed("🎵 Track index", f"{real_index+1}. `{track.author} - {track.title}` ({format_mil(track.length)})"))

async def queue_move(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("↕️ Move track", "The queue is empty"))
    index1 = min(int(init)-1, len(vc.queue)-1)
    index2 = min(int(dest)-1, len(vc.queue)-1)
    track = vc.queue.peek(index1)
    vc.queue.remove(track)
    vc.queue.put_at(index2, track)
    await ctx.reply(embed=music_embed("↕️ Move track", f"`{track.author} - {track.title}` is now at position `{index2+1}`"))

async def queue_smart(ctx: commands.Context, count: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not count: count="20"
    if not count.isdigit() or not int(count): return await ctx.reply("not a digit :(")
    await smart_recommendation(vc, max_population=int(count))
    for x in vc.auto_queue:
        await vc.queue.put_wait(x)
    vc.queue.shuffle()
    embed = music_embed("🔀 Smart Shuffle", f"`{len(vc.auto_queue)}` songs have been added")
    vc.auto_queue.reset()
    await ctx.reply(embed=embed)

async def queue_fair(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: wavelink.Player = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if vc.queue.is_empty:
        return await ctx.reply(embed=music_embed("⚖️ Fair Queue", "The queue is empty"))

    # Get all unique requesters in the queue
    requesters = []
    requester_tracks = {}

    # Group tracks by requester
    for track in vc.queue:
        requester_id = requester_string(ctx.bot, track)
        if requester_id not in requesters:
            requesters.append(requester_id)
            requester_tracks[requester_id] = []
        requester_tracks[requester_id].append(track)

    if len(requesters) <= 1:
        return await ctx.reply(embed=music_embed("⚖️ Fair Queue", "Queue is already fair"))

    # Start with a different requester than current if possible
    current_requester = requester_string(ctx.bot, vc.current)
    if current_requester in requesters:
        requesters.remove(current_requester)
        requesters.append(current_requester)

    # Create new fair queue
    new_queue: list[wavelink.Playable] = []
    max_rounds = max(len(tracks) for tracks in requester_tracks.values())

    # Distribute tracks round-robin style
    for round in range(max_rounds):
        for requester in requesters:
            tracks = requester_tracks[requester]
            if round < len(tracks):
                new_queue.append(tracks[round])

    # Clear and refill the queue with fair distribution
    vc.queue.reset()
    for track in new_queue:
        await vc.queue.put_wait(track)

    # Create summary of the new distribution
    distribution = {requester: len(tracks) for requester, tracks in requester_tracks.items()}
    distribution_summary = "\n".join([f"{requester}: {count} tracks" for requester, count in distribution.items()])
    queue_preview = "\n".join([f"{i + 1}. `{track.author} - {track.title}` ({format_mil(track.length)}) - {requester_string(ctx.bot, track)}" for i, track in enumerate(new_queue[:5])])
    description = f"Queue has been reorganized to alternate between users fairly.\n\n**Distribution:**\n{distribution_summary}\n\n**Playlist:**\n{queue_preview}"
    embed = music_embed("⚖️ Fair Queue", description)
    await ctx.reply(embed=embed)

async def search_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current: return []
    tracks = await wavelink.Playable.search(current)
    return [
        app_commands.Choice(name=f"{track.author} - {track.title}"[:100], value=track.uri) for track in tracks
    ][:25]

async def search_auto_spotify(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current: return []
    tracks = await wavelink.Playable.search(current, source="spsearch:")
    return [
        app_commands.Choice(name=f"{track.author} - {track.title}"[:100], value=track.uri) for track in tracks
    ][:25]

async def mode_repeat_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["off", "one", "all"] if current.lower() in mode.lower()
    ]

async def mode_rec_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["partial", "enabled", "disabled"] if current.lower() in mode.lower()
    ]

async def remove_member_auto(interaction: discord.Interaction, current: str):
    if not interaction.guild:
        return []

    # Get the voice client to check the queue
    vc: wavelink.Player = interaction.guild.voice_client
    if not vc or vc.queue.is_empty:
        return []

    # Get unique requesters from the queue
    requesters = set()
    has_bot_recommendations = False

    for i in range(len(vc.queue)):
        track = vc.queue.peek(i)
        requester_id = dict(track.extras).get("requester")
        if requester_id:
            requesters.add(int(requester_id))
        else:
            # Track with no requester = bot recommendation
            has_bot_recommendations = True

    # Get member objects and filter by current input
    choices = []

    # Add bot recommendations option if they exist
    if has_bot_recommendations:
        bot_name = f"{interaction.guild.me.display_name} ({interaction.guild.me.name})"
        if not current or current.lower() in bot_name.lower():
            choices.append(app_commands.Choice(
                name=bot_name,
                value="bot"
            ))

    for requester_id in requesters:
        try:
            member = interaction.guild.get_member(requester_id)
            if member:
                # Filter by current input (name or display name)
                if not current or current.lower() in member.display_name.lower() or current.lower() in member.name.lower():
                    choices.append(app_commands.Choice(
                        name=f"{member.display_name} ({member.name})",
                        value=member.id
                    ))
        except:
            continue

    # Sort by display name and limit to 25 (Discord's limit)
    choices.sort(key=lambda x: x.name.lower())
    return choices[:25]

class CogYouTubePlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        vc: wavelink.Player = payload.player
        if not vc: return
        if not vc.queue.mode == wavelink.QueueMode.loop:
            embed = music_now_playing_embed(self.bot, vc.current)
            await vc.music_channel.send(embed=embed)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['media']['music']}")
    async def music(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.command(aliases=['musichelp', 'helpmusic', 'helpm']) # alias
    async def mhelp(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['dj']}")
    async def dj(self, ctx: commands.Context):
        await set_dj_role(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['djspam']}")
    @app_commands.describe(channel_id="Channel ID")
    async def djspam(self, ctx: commands.Context, channel_id: str=None):
        await set_dj_channel(ctx, channel_id)

    # player
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['summon']}")
    async def summon(self, ctx: commands.Context):
        await music_summon(ctx)

    @commands.command() # alias
    async def p(self, ctx: commands.Context, *, query: str=None):
        await music_play(self.bot, ctx, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Play music (YouTube Music)")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=search_auto)
    async def play(self, ctx: commands.Context, *, query:str=None):
        await music_play(self.bot, ctx, query)

    @app_commands.command(name="play-spotify", description=f"{description_helper['emojis']['music']} Play music (Spotify)")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=search_auto_spotify)
    async def play_spotify(self, ctx: discord.Interaction, *, query:str=None):
        await music_play(self.bot, ctx, query)

    @commands.command(aliases=['die', 'dc']) # alias
    async def leave(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['stop']}")
    async def stop(self, ctx: commands.Context):
        await music_stop(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['pause']}")
    async def pause(self, ctx: commands.Context):
        await music_pause(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['resume']}")
    async def resume(self, ctx: commands.Context):
        await music_resume(ctx)

    @commands.command() # alias
    async def s(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['skip']}")
    async def skip(self, ctx: commands.Context):
        await music_skip(ctx)

    @commands.command() # alias
    async def np(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['nowplaying']}")
    async def nowplaying(self, ctx: commands.Context):
        await music_nowplaying(ctx)

    # queue
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Search music (YouTube Music)")
    async def search(self, ctx: commands.Context, *, query: str=None):
        await queue_search(self.bot, ctx, query)

    @app_commands.command(name="search-spotify", description=f"{description_helper['emojis']['music']} Search music (Spotify)")
    @app_commands.describe(query="Search query")
    async def search_spotify(self, ctx: discord.Interaction, *, query: str=None):
        await queue_search(self.bot, ctx, query, "spsearch:")

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['peek']}")
    @app_commands.describe(index="Track number you want to peek into (Must be a valid integer)")
    async def peek(self, ctx: commands.Context, index: str):
        await queue_peek(ctx, index)

    @commands.command() # alias
    async def queue(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['list']}")
    @app_commands.describe(page="Page number")
    async def list(self, ctx: commands.Context, page: str=None):
        await queue_list(ctx, page)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['repeat']}")
    @app_commands.describe(mode="Repeat mode")
    @app_commands.autocomplete(mode=mode_repeat_auto)
    async def repeat(self, ctx: commands.Context, mode: str):
        await queue_loop(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['player']['autoplay']}")
    @app_commands.describe(mode="Autoplay mode")
    @app_commands.autocomplete(mode=mode_rec_auto)
    async def autoplay(self, ctx: commands.Context, mode: str):
        await queue_autoplay(ctx, mode)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['shuffle']}")
    async def shuffle(self, ctx: commands.Context):
        await queue_shuffle(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['clear']}")
    async def clear(self, ctx: commands.Context):
        await queue_reset(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['smart']}")
    async def smart(self, ctx: commands.Context, count: str=None):
        await queue_smart(ctx, count)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['fair']}")
    async def fair(self, ctx: commands.Context):
        await queue_fair(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['remove']}")
    @app_commands.describe(index="Track number you want to remove (Must be a valid integer)",
                           index2="Track number you want to remove within range (Must be a valid integer)",
                           member="Remove all tracks queued by this member")
    @app_commands.autocomplete(member=remove_member_auto)
    async def remove(self, ctx: commands.Context, index: str=None, index2: str=None, member: str=None):
        await queue_remove(ctx, index, index2, member)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['replace']}")
    @app_commands.describe(index="Track number you want to replace (Must be a valid integer)", query="Search query")
    async def replace(self, ctx: commands.Context, index: str, *, query: str):
        await queue_replace(ctx, index, query)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['swap']}")
    @app_commands.describe(init="First track number you want to swap into (Must be a valid integer)",
                           dest="Second track number you want to swap into (Must be a valid integer)")
    async def swap(self, ctx: commands.Context, init: str, dest: str):
        await queue_swap(ctx, init, dest)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['queue']['move']}")
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
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
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
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.timescale.set(pitch=pitch, speed=speed, rate=rate)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Timescale", filters.timescale.payload))

    # @commands.hybrid_command(description="")
    # async def karaoke(self, ctx: commands.Context, level:float=None, mono_level:float=None, filter_band:float=None, filter_width:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.karaoke.set(level=level, mono_level=mono_level, filter_band=filter_band, filter_width=filter_width)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Karaoke", filters.karaoke.payload))

    # @commands.hybrid_command(description="")
    # async def lowpass(self, ctx: commands.Context, smoothing:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.low_pass.set(smoothing=smoothing)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Low Pass", filters.low_pass.payload))

    # @commands.hybrid_command(description="")
    # async def distortion(self, ctx: commands.Context, 
    #                      sin_offset:float=None, sin_scale:float=None, cos_offset:float=None, cos_scale:float=None, 
    #                      tan_offset:float=None, tan_scale:float=None, offset:float=None, scale:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.distortion.set(sin_offset=sin_offset, sin_scale=sin_scale, cos_offset=cos_offset, cos_scale=cos_scale, 
    #                            tan_offset=tan_offset, tan_scale=tan_scale, offset=offset, scale=scale)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Distortion", filters.distortion.payload))

    # @commands.hybrid_command(description="")
    # async def rotation(self, ctx: commands.Context, rotation_hz:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.rotation.set(rotation_hz=rotation_hz)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Rotation", filters.rotation.payload))

    # @commands.hybrid_command(description="")
    # async def channelmix(self, ctx: commands.Context, left_to_left:float=None, left_to_right:float=None, 
    #                      right_to_left:float=None, right_to_right:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.channel_mix.set(left_to_left=left_to_left, left_to_right=left_to_right, 
    #                             right_to_left=right_to_left, right_to_right=right_to_right)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Channel Mix", filters.channel_mix.payload))

    # @commands.hybrid_command(description="")
    # async def tremolo(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.tremolo.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Tremolo", filters.tremolo.payload))

    # @commands.hybrid_command(description="")
    # async def vibrato(self, ctx: commands.Context, frequency:float=None, depth:float=None):
    #     if not ctx.guild: return await ctx.reply("not supported")
    #     if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    #     vc: wavelink.Player = ctx.voice_client
    #     if not vc: return await ctx.reply("voice client not found")
    #     if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
    #         return await ctx.reply(f'Join the voice channel with the bot first')

    #     filters: wavelink.Filters = vc.filters
    #     filters.vibrato.set(frequency=frequency, depth=depth)
    #     await vc.set_filters(filters)
    #     await ctx.reply(embed=filter_embed("🎚️ Filter", "Vibrato", filters.vibrato.payload))

async def setup(bot: commands.Bot):
    await bot.add_cog(CogYouTubePlayer(bot))