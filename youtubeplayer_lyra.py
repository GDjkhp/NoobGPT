from discord.ext import commands
from discord import app_commands
from music_lyra import *
from help import HALP_MOOSIC
from util_discord import command_check, description_helper, get_guild_prefix

async def music_help(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    await HALP_MOOSIC(ctx)

# player commands
async def music_summon(bot: commands.Bot, ctx: commands.Context):
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
        vc = await voice_channel_connector(bot, ctx)
    except:
        # if fixing: return await ctx.reply(content="Please try again later")
        print("ChannelTimeoutException")
        return await ctx.reply(content="An error occured.")
    vc.autoplay = AutoPlayMode.enabled
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

    vc: NoobGPTPlayer = ctx.guild.voice_client
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

    # Check if search contains multiple links
    links = extract_links(search)

    if links and len(links) > 1:
        # Handle multiple links
        if not ctx.guild.voice_client:
            try:
                vc = await voice_channel_connector(bot, ctx)
            except:
                print("ChannelTimeoutException")
                if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="An error occured.")
                if isinstance(ctx, commands.Context): return await msg.edit(content="An error occured.")

            vc.autoplay = AutoPlayMode.enabled

        vc.music_channel = ctx.channel

        # Process each link
        queued_count = 0
        failed_links = []
        added_tracks = []

        for link in links:
            try:
                node = pool.get_node(identifier=bot.node_ids[0])
                tracks = await node.get_tracks(link, search_type=lava_lyra.SearchType.ytmsearch)

                if tracks:
                    if isinstance(tracks, lava_lyra.Playlist):
                        added: int = vc.queue.put(tracks)
                        queued_count += added
                        for track in tracks:
                            if isinstance(ctx, commands.Context):
                                track.requester = ctx.author
                            if isinstance(ctx, discord.Interaction):
                                track.requester = ctx.user
                            added_tracks.append(track)
                    else:
                        for track in tracks:
                            if isinstance(ctx, commands.Context):
                                track.requester = ctx.author
                            if isinstance(ctx, discord.Interaction):
                                track.requester = ctx.user
                        vc.queue.put(tracks[0])
                        queued_count += 1
                        added_tracks.append(tracks[0])
                else:
                    failed_links.append(link)
            except Exception as e:
                failed_links.append(link)

        if not vc.is_playing and queued_count > 0:
            await vc.play(vc.queue.get())

        # Create embed with queued tracks
        embed = music_embed(f"🎵 Queue tracks", f"Queued {queued_count} track{'s' if queued_count != 1 else ''}")

        # Add queued tracks to embed
        if added_tracks:
            track_list = "\n".join([f"{i + 1}. `{track.author} - {track.title}` ({format_mil(track.length)})" for i, track in enumerate(added_tracks[:10])])
            embed.add_field(name="Queued Tracks", value=track_list, inline=False)
            if len(added_tracks) > 10:
                embed.add_field(name="More", value=f"... and {len(added_tracks) - 10} more track{'s' if len(added_tracks) - 10 != 1 else ''}", inline=False)

        # Add failed links to embed
        if failed_links:
            failed_text = "\n".join(failed_links[:5])
            embed.add_field(name=f"❌ Failed Links ({len(failed_links)})", value=failed_text, inline=False)
            if len(failed_links) > 5:
                embed.add_field(name="More Failed", value=f"... and {len(failed_links) - 5} more", inline=False)

        if isinstance(ctx, commands.Context):
            await msg.edit(content=None, embed=embed)
        if isinstance(ctx, discord.Interaction):
            await ctx.edit_original_response(content=None, embed=embed)
        return

    # Original single search handling
    try:
        node = pool.get_node(identifier=bot.node_ids[0])
        tracks = await node.get_tracks(search, search_type=lava_lyra.SearchType.ytmsearch)
    except Exception as e:
        # if isinstance(ctx, commands.Context):
        #     return await msg.edit(content=f'Error :(\n{e}')
        # if isinstance(ctx, discord.Interaction):
        #     return await ctx.edit_original_response(content=f'Error :(\n{e}')
        print("ChannelTimeoutException")
        if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="An error occured.")
        if isinstance(ctx, commands.Context): return await msg.edit(content="An error occured.")

    if not tracks:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content='No results found')
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content='No results found')

    for track in tracks:
        if isinstance(ctx, commands.Context):
            track.requester = ctx.author
        if isinstance(ctx, discord.Interaction):
            track.requester = ctx.user

    if not ctx.guild.voice_client:
        try:
            vc = await voice_channel_connector(bot, ctx)
        except:
            # if fixing: 
            #     if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="Please try again later")
            #     if isinstance(ctx, commands.Context): return await msg.edit(content="Please try again later")
            print("ChannelTimeoutException")
            if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="An error occured.")
            if isinstance(ctx, commands.Context): return await msg.edit(content="An error occured.")

        vc.autoplay = AutoPlayMode.enabled
    vc.music_channel = ctx.channel

    if isinstance(tracks, lava_lyra.Playlist):
        added: int = vc.queue.put(tracks)
        text, desc = f"🎵 Queue playlist", f'Added `{added}` songs to the queue'
        embed = music_embed(text, desc)
        embed.add_field(name="Name", value=f"[{tracks.name}]({tracks.uri})" if tracks.uri else tracks.name, inline=False)
        embed.add_field(name="Author", value=tracks.playlist_info, inline=False) # omg there's no helpers
        embed.add_field(name="Type", value=tracks.playlist_type, inline=False)
        if tracks.thumbnail: embed.set_thumbnail(url=tracks.thumbnail)
    else:
        vc.queue.put(tracks[0])
        text, desc = "🎵 Play music", f'`{tracks[0].author} - {tracks[0].title}` has been added to the queue at position `{len(vc.queue)}`'
        embed = music_embed(text, desc)
    if not vc.is_playing: await vc.play(vc.queue.get())
    if isinstance(ctx, commands.Context):
        await msg.edit(content=None, embed=embed)
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(embed=embed, content=None)

async def music_pause(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    await vc.set_pause(True)
    embed = music_embed("⏸️ Pause music", "The music has been paused")
    await ctx.reply(embed=embed)

async def music_resume(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    await vc.set_pause(False)
    embed = music_embed("▶️ Resume music", "The music has been resumed")
    await ctx.reply(embed=embed)

async def music_skip(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if vc.queue.is_empty:
        if vc.autoplay == AutoPlayMode.enabled and not vc.auto_queue.is_empty:
            for x in vc.auto_queue:
                vc.queue.put(x)
            vc.auto_queue.clear()
        else: return await ctx.reply("There are no songs in the queue to skip")
    prev = vc.current
    await vc.stop()
    if prev: await ctx.reply(embed=music_embed("⏭️ Skip music", f"`{prev.author} - {prev.title}` has been skipped"))

async def music_stop(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_dj(ctx): return await ctx.reply("not a disc jockey and/or in music spam channel")
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    await vc.destroy()
    embed = music_embed("⏹️ Stop music", "The music has been stopped")
    await ctx.reply(embed=embed)

async def music_nowplaying(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if vc.is_playing: await ctx.reply(embed=music_now_playing_embed(ctx.bot, vc.current))

async def music_volume(ctx: commands.Context, value: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
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
        node = pool.get_node(identifier=bot.node_ids[0])
        tracks = await node.get_tracks(search, search_type=lava_lyra.SearchType.ytmsearch)
    except Exception as e:
        # if isinstance(ctx, commands.Context):
        #     return await msg.edit(content=f'Error :(\n{e}')
        # if isinstance(ctx, discord.Interaction):
        #     return await ctx.edit_original_response(content=f'Error :(\n{e}')
        print("ChannelTimeoutException")
        if isinstance(ctx, discord.Interaction): return await ctx.edit_original_response(content="An error occured.")
        if isinstance(ctx, commands.Context): return await msg.edit(content="An error occured.")

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
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    current_queue = vc.queue
    if current_queue.is_empty:
        if vc.autoplay == AutoPlayMode.enabled and not vc.auto_queue.is_empty:
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
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if mode == 'off':
        vc.queue.disable_loop()
        text, desc = "❌ Repeat off", "Queue mode is now set to normal"
    elif mode == 'one':
        vc.queue.set_loop_mode(lava_lyra.LoopMode.TRACK)
        text, desc = "🔂 Repeat one", "Queue mode is now set to loop"
    elif mode == 'all':
        vc.queue.set_loop_mode(lava_lyra.LoopMode.QUEUE)
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
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')

    if mode == 'partial':
        vc.autoplay = AutoPlayMode.partial
        text, desc = "❌ Recommendations disabled", "Autoplay mode is now set to partial"
    elif mode == 'enabled':
        vc.autoplay = AutoPlayMode.enabled
        text, desc = "✅ Recommendations enabled", "Autoplay mode is now enabled"
    elif mode == 'disabled':
        vc.autoplay = AutoPlayMode.disabled
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
    vc: NoobGPTPlayer = ctx.voice_client
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
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    vc.queue.clear()
    vc.auto_queue.clear()
    await ctx.reply(embed=music_embed("🗑️ Clear queue", "The queue has been emptied"))

async def queue_remove(ctx: commands.Context, index: str = None, index2: str = None, member: str = None):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
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
                track = vc.queue[i]
                track_requester = track.requester
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
            track = vc.queue[i]
            track_requester = track.requester
            if track_requester and str(track_requester.id) == member_id:
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
            tracks_to_remove.append(vc.queue[i])

        # Remove tracks (remove in reverse order to maintain indices)
        for track in reversed(tracks_to_remove):
            vc.queue.remove(track)

        count = len(tracks_to_remove)
        await ctx.reply(embed=music_embed("🗑️ Remove tracks", f"Removed {count} track{'s' if count != 1 else ''} from position {int(index)} to {int(index2)}"))

    # Handle single track removal
    else:
        track = vc.queue[min(int(index)-1, len(vc.queue)-1)]
        vc.queue.remove(track)
        await ctx.reply(embed=music_embed("🗑️ Remove track", f"`{track.author} - {track.title}` has been removed"))

async def queue_replace(ctx: commands.Context, index: str, query: str): # TODO: source
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("➡️ Replace track", "The queue is empty"))
    try: tracks = await vc.get_tracks(query, search_type=lava_lyra.SearchType.ytmsearch)
    except Exception as e: return await ctx.reply(f'Error :(\n{e}')
    if not tracks: return await ctx.reply('No results found')
    real_index = min(int(index)-1, len(vc.queue)-1)
    track = vc.queue[real_index]
    vc.queue[real_index] = tracks[0] # TODO: let the user choose
    await ctx.reply(embed=music_embed("➡️ Replace track", f"`{track.author} - {track.title}` has been removed and `{tracks[0].author} - {tracks[0].title}` has been replaced"))

async def queue_swap(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🔄 Swap tracks", "The queue is empty"))
    index1 = min(int(init)-1, len(vc.queue)-1)
    index2 = min(int(dest)-1, len(vc.queue)-1)
    first = vc.queue[index1]
    second = vc.queue[index2]
    vc.queue[index1], vc.queue[index2] = vc.queue[index2], vc.queue[index1]
    await ctx.reply(embed=music_embed("🔄 Swap tracks", f"`{first.author} - {first.title}` is at position `{index2+1}` and `{second.author} - {second.title}` is at position `{index1+1}`"))

async def queue_peek(ctx: commands.Context, index: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not index.isdigit() or not int(index): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("🎵 Track index", "The queue is empty"))
    real_index = min(int(index)-1, len(vc.queue)-1)
    track = vc.queue[real_index]
    await ctx.reply(embed=music_embed("🎵 Track index", f"{real_index+1}. `{track.author} - {track.title}` ({format_mil(track.length)})"))

async def queue_move(ctx: commands.Context, init: str, dest: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not init.isdigit() or not dest.isdigit() or not int(init) or not int(dest): return await ctx.reply("not a digit :(")
    if vc.queue.is_empty: return await ctx.reply(embed=music_embed("↕️ Move track", "The queue is empty"))
    index1 = min(int(init)-1, len(vc.queue)-1)
    index2 = min(int(dest)-1, len(vc.queue)-1)
    track = vc.queue[index1]
    vc.queue.remove(track)
    vc.queue.put_at_index(index2, track)
    await ctx.reply(embed=music_embed("↕️ Move track", f"`{track.author} - {track.title}` is now at position `{index2+1}`"))

async def queue_smart(ctx: commands.Context, count: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
    if not vc: return await ctx.reply("voice client not found")
    if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
        return await ctx.reply(f'Join the voice channel with the bot first')
    if not count: count="20"
    if not count.isdigit() or not int(count): return await ctx.reply("not a digit :(")
    # await smart_recommendation(vc, max_population=int(count)) # TODO: rec
    for x in vc.auto_queue:
        vc.queue.put(x)
    vc.queue.shuffle()
    embed = music_embed("🔀 Smart Shuffle", f"`{len(vc.auto_queue)}` songs have been added")
    vc.auto_queue.clear()
    await ctx.reply(embed=embed)

async def queue_fair(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if check_bot_conflict(ctx): return await ctx.reply("use moosic instead :)", ephemeral=True)
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    vc: NoobGPTPlayer = ctx.voice_client
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
    new_queue: list[lava_lyra.Track] = []
    max_rounds = max(len(tracks) for tracks in requester_tracks.values())

    # Distribute tracks round-robin style
    for round in range(max_rounds):
        for requester in requesters:
            tracks = requester_tracks[requester]
            if round < len(tracks):
                new_queue.append(tracks[round])

    # Clear and refill the queue with fair distribution
    vc.queue.clear()
    for track in new_queue:
        vc.queue.put(track)

    # Create summary of the new distribution
    distribution = {requester: len(tracks) for requester, tracks in requester_tracks.items()}
    distribution_summary = "\n".join([f"{requester}: {count} tracks" for requester, count in distribution.items()])
    queue_preview = "\n".join([f"{i + 1}. `{track.author} - {track.title}` ({format_mil(track.length)}) - {requester_string(ctx.bot, track)}" for i, track in enumerate(new_queue[:5])])
    description = f"Queue has been reorganized to alternate between users fairly.\n\n**Distribution:**\n{distribution_summary}\n\n**Playlist:**\n{queue_preview}"
    embed = music_embed("⚖️ Fair Queue", description)
    await ctx.reply(embed=embed)

async def queue_on_start(bot, vc: NoobGPTPlayer):
    if not vc: return
    embed = music_now_playing_embed(bot, vc.current)
    await vc.music_channel.send(embed=embed)
    await get_rekt(vc)

async def queue_on_end(vc: NoobGPTPlayer):
    if not vc: return
    if not vc.queue.is_empty: return await vc.play(vc.queue.get())
    if vc.autoplay == AutoPlayMode.enabled and not vc.auto_queue.is_empty:
        history_ids = [track.identifier for track in vc.history_queue]
        vc.auto_queue.shuffle()
        for x in vc.auto_queue:
            current_ids = [track.identifier for track in vc.queue]
            if x.identifier not in history_ids and x.identifier not in current_ids: vc.queue.put(x)
        vc.auto_queue.clear()
        await queue_on_end(vc)

async def search_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current: return []
    node = pool.get_node(identifier=interaction.client.node_ids[0])
    tracks = await node.get_tracks(current, search_type=lava_lyra.SearchType.ytmsearch)
    return [
        app_commands.Choice(name=f"{track.author} - {track.title}"[:100], value=track.uri) for track in tracks
    ][:25]

async def search_auto_spotify(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current: return []
    node = pool.get_node(identifier=interaction.client.node_ids[0])
    tracks = await node.get_tracks(current, search_type=lava_lyra.SearchType.spsearch)
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
    vc: NoobGPTPlayer = interaction.guild.voice_client
    if not vc or vc.queue.is_empty:
        return []

    # Get unique requesters from the queue
    requesters = set()
    has_bot_recommendations = False

    for i in range(len(vc.queue)):
        track = vc.queue[i]
        requester_id = track.requester
        if requester_id:
            requesters.add(requester_id.id)
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
    async def on_lyra_track_start(self, vc: NoobGPTPlayer, track: lava_lyra.Track):
        await queue_on_start(self.bot, vc)

    @commands.Cog.listener()
    async def on_lyra_track_end(self, vc: NoobGPTPlayer, track: lava_lyra.Track, reason: str):
        await queue_on_end(vc)

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} {description_helper['media']['music']}")
    async def music(self, ctx: commands.Context):
        await music_help(ctx)

    @commands.command(aliases=['musichelp', 'helpmusic', 'helpm', 'help']) # alias
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
        await music_summon(self.bot, ctx)

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

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Apply or reset audio filters")
    async def filters(self, ctx: commands.Context, reset: str = None, filter: str = None):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)

        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")

        # ── reset branch ────────────────────────────────────────────────────────
        valid_filters = ["karaoke", "timescale", "lowpass", "rotation", "distortion", "channelmix", "tremolo", "vibrato"]
        if reset and reset.lower() == "reset":
            if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
                return await ctx.reply(f'Join the voice channel with the bot first')
            if filter and filter.lower() in valid_filters:
                tag = filter.lower()
                if vc.filters.has_filter(filter_tag=tag):
                    await vc.remove_filter(filter_tag=tag, fast_apply=True)
                    return await ctx.reply(f"`{filter}` filter has been reset.")
                else:
                    return await ctx.reply(f"`{filter}` filter is not active.")
            else:
                await vc.reset_filters(fast_apply=True)
                return await ctx.reply("All filters have been reset.")

        # ── help text ────────────────────────────────────────────────────────────
        texts = [
            "`-karaoke <level> <mono_level> <filter_band> <filter_width>`",
            "`-timescale <pitch> <speed> <rate>`",
            "`-lowpass <smoothing>`",
            "`-rotation <rotation_hz>`",
            "`-distortion <sin_offset> <sin_scale> <cos_offset> <cos_scale> <tan_offset> <tan_scale> <offset> <scale>`",
            "`-channelmix <left_to_left> <left_to_right> <right_to_left> <right_to_right>`",
            "`-tremolo <frequency> <depth>`",
            "`-vibrato <frequency> <depth>`",
            "`-filters reset` — reset all filters",
            "`-filters reset <filter>` — reset a specific filter",
        ]
        await ctx.reply("\n".join(texts))
    
    # ── individual filter sub-commands ──────────────────────────────────────────
    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Karaoke filter – removes vocals")
    async def karaoke(
        self, ctx: commands.Context,
        level: float = 1.0,
        mono_level: float = 1.0,
        filter_band: float = 220.0,
        filter_width: float = 100.0,
    ):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        f = lava_lyra.Karaoke(
            tag="karaoke",
            level=level,
            mono_level=mono_level,
            filter_band=filter_band,
            filter_width=filter_width,
        )
        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(
        #     f"Karaoke filter applied — level: `{level}`, mono_level: `{mono_level}`, "
        #     f"filter_band: `{filter_band}`, filter_width: `{filter_width}`"
        # )
        await ctx.reply(embed=filter_embed("🎚️ Filter", "karaoke", {
            "level": level,
            "mono_level": mono_level,
            "filter_band": filter_band,
            "filter_width": filter_width,
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Timescale filter – change pitch / speed / rate")
    async def timescale(
        self, ctx: commands.Context,
        pitch: float = 1.0,
        speed: float = 1.0,
        rate: float = 1.0,
    ):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        try:
            f = lava_lyra.Timescale(tag="timescale", pitch=pitch, speed=speed, rate=rate)
        except lava_lyra.FilterInvalidArgument as e:
            return await ctx.reply(f"Invalid argument: {e}")

        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(f"Timescale filter applied — pitch: `{pitch}`, speed: `{speed}`, rate: `{rate}`")
        await ctx.reply(embed=filter_embed("🎚️ Filter", "timescale", {
            "pitch": pitch, "speed": speed, "rate": rate
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Low-pass filter – suppress high frequencies")
    async def lowpass(self, ctx: commands.Context, smoothing: float = 20.0):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        f = lava_lyra.LowPass(tag="lowpass", smoothing=smoothing)
        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(f"Low-pass filter applied — smoothing: `{smoothing}`")
        await ctx.reply(embed=filter_embed("🎚️ Filter", "lowpass", {"smoothing": smoothing}))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Rotation filter – 8D / rotating audio effect")
    async def rotation(self, ctx: commands.Context, rotation_hz: float = 5.0):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        f = lava_lyra.Rotation(tag="rotation", rotation_hertz=rotation_hz)
        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(f"Rotation filter applied — rotation_hz: `{rotation_hz}`")
        await ctx.reply(embed=filter_embed("🎚️ Filter", "???", {"rotation_hertz": rotation_hz}))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Distortion filter")
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
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        f = lava_lyra.Distortion(
            tag="distortion",
            sin_offset=sin_offset, sin_scale=sin_scale,
            cos_offset=cos_offset, cos_scale=cos_scale,
            tan_offset=tan_offset, tan_scale=tan_scale,
            offset=offset, scale=scale,
        )
        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(
        #     f"Distortion filter applied — sin: `{sin_offset}/{sin_scale}`, "
        #     f"cos: `{cos_offset}/{cos_scale}`, tan: `{tan_offset}/{tan_scale}`, "
        #     f"offset: `{offset}`, scale: `{scale}`"
        # )
        await ctx.reply(embed=filter_embed("🎚️ Filter", "distortion", {
            "sin_offset": sin_offset, "sin_scale": sin_scale,
            "cos_offset": cos_offset, "cos_scale": cos_scale,
            "tan_offset": tan_offset, "tan_scale": tan_scale,
            "offset": offset, "scale": scale,
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Channel mix filter – adjust stereo panning")
    async def channelmix(
        self, ctx: commands.Context,
        left_to_left: float = 1.0,
        left_to_right: float = 0.0,
        right_to_left: float = 0.0,
        right_to_right: float = 1.0,
    ):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        try:
            f = lava_lyra.ChannelMix(
                tag="channelmix",
                left_to_left=left_to_left,
                left_to_right=left_to_right,
                right_to_left=right_to_left,
                right_to_right=right_to_right,
            )
        except ValueError as e:
            return await ctx.reply(f"Invalid argument: {e}")

        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(
        #     f"Channel mix applied — LL: `{left_to_left}`, LR: `{left_to_right}`, "
        #     f"RL: `{right_to_left}`, RR: `{right_to_right}`"
        # )
        await ctx.reply(embed=filter_embed("🎚️ Filter", "channelmix", {
            "left_to_left": left_to_left,
            "left_to_right": left_to_right,
            "right_to_left": right_to_left,
            "right_to_right": right_to_right,
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Tremolo filter – wavering volume effect")
    async def tremolo(self, ctx: commands.Context, frequency: float = 2.0, depth: float = 0.5):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        try:
            f = lava_lyra.Tremolo(tag="tremolo", frequency=frequency, depth=depth)
        except lava_lyra.FilterInvalidArgument as e:
            return await ctx.reply(f"Invalid argument: {e}")

        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(f"Tremolo filter applied — frequency: `{frequency}`, depth: `{depth}`")
        await ctx.reply(embed=filter_embed("🎚️ Filter", "tremolo", {
            "frequency": frequency, "depth": depth
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Vibrato filter – wavering pitch effect")
    async def vibrato(self, ctx: commands.Context, frequency: float = 2.0, depth: float = 0.5):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')

        try:
            f = lava_lyra.Vibrato(tag="vibrato", frequency=frequency, depth=depth)
        except lava_lyra.FilterInvalidArgument as e:
            return await ctx.reply(f"Invalid argument: {e}")

        await vc.add_filter(f, fast_apply=True)
        # await ctx.reply(f"Vibrato filter applied — frequency: `{frequency}`, depth: `{depth}`")
        await ctx.reply(embed=filter_embed("🎚️ Filter", "vibrato", {
            "frequency": frequency, "depth": depth
        }))

    @commands.hybrid_command(description=f"{description_helper['emojis']['music']} Fetch lyrics")
    async def lyrics(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.reply("not supported")
        if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
        vc: NoobGPTPlayer = ctx.voice_client
        if not vc: return await ctx.reply("voice client not found")
        if not ctx.author.voice or not ctx.author.voice.channel == vc.channel:
            return await ctx.reply(f'Join the voice channel with the bot first')
        lyrics = await vc.fetch_lyrics()
        if lyrics:
            strings_by_4096: list[str] = []
            lyric_page = ""
            for l in lyrics.lines:
                if len(lyric_page) + len(l.text) < 4096:
                    lyric_page += f"{l.text}\n"
                else:
                    strings_by_4096.append(lyric_page)
                    lyric_page = ""
            strings_by_4096.append(lyric_page)
            for i, l in enumerate(strings_by_4096):
                embed = discord.Embed(title=vc.current.title, description=l, color=0x00ff00)
                if vc.current.thumbnail: embed.set_thumbnail(url=vc.current.thumbnail)
                embed.set_footer(text=f"page: {i+1}/{len(strings_by_4096)} | lines: {len(lyrics)} | source_name: {lyrics.source_name} | provider: {lyrics.provider} | synced: {lyrics.synced} | name: {lyrics.name} | lang: {lyrics.lang}")
                await ctx.reply(embed=embed)
        else: await ctx.reply("not found :(")

async def setup(bot: commands.Bot):
    await bot.add_cog(CogYouTubePlayer(bot))