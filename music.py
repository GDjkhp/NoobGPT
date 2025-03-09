import secrets
import asyncio
import random
import wavelink
from discord.ext import commands
import discord
from util_discord import command_check, get_database2, set_dj_role_db, set_dj_channel_db, check_if_master_or_admin, check_if_not_owner
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]
fixing=False

async def setup_hook_music(bot: commands.Bot):
    global fixing
    fixing=True
    nodes = []
    data = await node_list()
    for n in bot.node_ids:
        try:
            n = wavelink.Pool.get_node(n)
            if n: await n.close(eject=True)
        except Exception as e: print(e)
    bot.node_ids = []
    for lava in data:
        node_id = secrets.token_urlsafe(12)
        bot.node_ids.append(node_id)
        nodes.append(wavelink.Node(client=bot, uri=lava["host"], password=lava["password"], retries=3, identifier=node_id))
    await wavelink.Pool.connect(nodes=nodes)
    fixing=False
    print(f"{bot.identifier}: setup_hook_music ok")

async def view_nodes(ctx: commands.Context):
    data = await node_list()
    if not data: return await ctx.reply("nodes not found")
    await ctx.reply(embed=nodes_embed(data))

async def add_node(ctx: commands.Context, host: str, password: str):
    await mycol.update_one({}, {"$push": {"nodes": {"host": host, "password": password}}})
    data = await node_list()
    await ctx.reply(embed=nodes_embed(data))

async def delete_node(ctx: commands.Context, index: int):
    data = await node_list()
    if not data: return await ctx.reply("nodes not found")
    await mycol.update_one({}, {"$pull": {"nodes": dict(data[min(index, len(data)-1)])}})
    data = await node_list()
    await ctx.reply(embed=nodes_embed(data))

async def node_list():
    cursor = mycol.find()
    data = await cursor.to_list(None)
    return data[0]["nodes"]

async def set_dj_channel(ctx: commands.Context, chan_id: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    chan = None
    if chan_id:
        if chan_id == "off":
            await set_dj_channel_db(ctx.guild.id, 0)
            return await ctx.reply("dj channel has been disabled!")
        if not chan_id.isdigit(): return await ctx.reply("not a digit :(")
        chan = ctx.guild.get_channel(int(chan_id))
    if not chan: chan = ctx.channel
    await set_dj_channel_db(ctx.guild.id, chan.id)
    await ctx.reply(f"{chan.jump_url} has been set as **THE DJ SPAM CHANNEL!**")

async def set_dj_role(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles permission is disabled :(**")

    db = await get_database2(ctx.guild.id)
    if not db.get("bot_dj_role") or not db["bot_dj_role"]:
        role = await ctx.guild.create_role(name="noobgpt disc jockey", mentionable=False)
        await set_dj_role_db(ctx.guild.id, role.id)
        await ctx.reply(f"dj role <@&{role.id}> has been created")
    else:
        role = ctx.guild.get_role(db["bot_dj_role"])
        if role: await role.delete()
        await set_dj_role_db(ctx.guild.id, 0)
        await ctx.reply("dj role has been removed")

async def check_if_dj(ctx: commands.Context | discord.Interaction):
    db = await get_database2(ctx.guild.id)
    if db.get("bot_dj_channel"):
        if db["bot_dj_channel"]:
            return db["bot_dj_channel"] == ctx.channel.id
    if db.get("bot_dj_role"):
        if db["bot_dj_role"]:
            if isinstance(ctx, commands.Context): r = ctx.author.roles
            if isinstance(ctx, discord.Interaction): r = ctx.user.roles
            return ctx.guild.get_role(db["bot_dj_role"]) in r
    return True

def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def music_now_playing_embed(bot: commands.Context, track: wavelink.Playable):
    embed = discord.Embed(title="🎵 Now playing", color=0x00ff00,
                          description=f"[{track.title}]({track.uri})" if track.uri else track.title)
    embed.add_field(name="Author", value=track.author, inline=False)
    if track.album.name: embed.add_field(name="Album", value=track.album.name, inline=False)
    embed.add_field(name="Duration", value=format_mil(track.length), inline=False)
    embed.add_field(name="Requested by", value=requester_string(bot, track), inline=False)

    if track.artwork: embed.set_thumbnail(url=track.artwork)
    elif track.album.url: embed.set_thumbnail(url=track.album.url)
    elif track.artist.url: embed.set_thumbnail(url=track.artist.url)

    if track.source == "spotify":
        embed.set_author(name="Spotify", icon_url="https://gdjkhp.github.io/img/Spotify_App_Logo.svg.png")
    elif track.source == "youtube":
        embed.set_author(name="YouTube", icon_url="https://gdjkhp.github.io/img/771384-512.png")
    elif track.source == "soundcloud":
        embed.set_author(name="SoundCloud", icon_url="https://gdjkhp.github.io/img/soundcloud-icon.png")
    elif track.source == "bandcamp":
        embed.set_author(name="Bandcamp", icon_url="https://gdjkhp.github.io/img/bandcamp-button-circle-aqua-512.png")
    elif track.source == "applemusic":
        embed.set_author(name="Apple Music", icon_url="https://gdjkhp.github.io/img/applemoosic.png")
    elif track.source == "deezer":
        embed.set_author(name="Deezer", icon_url="https://gdjkhp.github.io/img/deez.png")
    else:
        embed.set_author(name=track.source)
        print(track.source)
    return embed

def requester_string(bot: commands.Bot, track: wavelink.Playable):
    if dict(track.extras).get("requester"): return f"<@{track.extras.requester}>"
    return f"<@{bot.user.id}>"

def filter_embed(title: str, description: str, filter: dict):
    e = discord.Embed(title=title, description=description, color=0x00ff00)
    for key, value in filter.items(): e.add_field(name=key, value=value)
    return e

def nodes_embed(nodes: list[dict]):
    e = discord.Embed(title="🌏 Nodes", description=f"{len(nodes)} found", color=0x00ff00)
    for lava in nodes:
        e.add_field(name=f'`{lava["host"]}`', value=f'`{lava["password"]}`', inline=False)
    return e

def format_mil(milliseconds: int):
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    formatted_time = []
    if days:
        formatted_time.append(f"{days:02}")
    if hours or formatted_time:
        formatted_time.append(f"{hours:02}")
    formatted_time.append(f"{minutes:02}:{seconds:02}")

    return ":".join(formatted_time)

# smart shuffle algorithm
async def get_recommendations(
    vc: wavelink.Player,
    seed_tracks: list[wavelink.Playable] = None,
    max_tracks: int = 20,
    existing_tracks: list[wavelink.Playable] = None
) -> list[wavelink.Playable]:
    """
    Get track recommendations based on seed tracks.

    Parameters:
    - vc: The voice client player
    - seed_tracks: List of tracks to use as seeds
    - max_tracks: Maximum number of tracks to return
    - existing_tracks: Tracks to exclude from results

    Returns:
    - List of recommended tracks
    """
    if not seed_tracks: 
        return []

    if not existing_tracks: 
        existing_tracks = []

    recommended_tracks = []
    attempts = 0
    used_seeds = set()

    while len(recommended_tracks) < max_tracks and len(used_seeds) < len(seed_tracks):
        attempts += 1
        try:
            # Avoid selecting the same seed track repeatedly
            available_seeds = [t for t in seed_tracks if t.identifier not in used_seeds]
            if not available_seeds: break
            track = random.choice(available_seeds)
            query = None
            if track.source == "spotify":
                random_spotify_seeds = [
                    t.identifier for t in seed_tracks
                    if t.source == "spotify"
                    and t.identifier not in used_seeds
                ]
                if not random_spotify_seeds: break
                random.shuffle(random_spotify_seeds)
                for s in random_spotify_seeds[:5]: used_seeds.add(s)
                query = f"sprec:seed_tracks={','.join(random_spotify_seeds[:5])}&limit=100"
            elif track.source == "youtube":
                used_seeds.add(track.identifier)
                query = f"https://music.youtube.com/watch?v={track.identifier}&list=RD{track.identifier}"
            elif track.source == "deezer":
                used_seeds.add(track.identifier)
                query = f"dzrec:{track.identifier}"
            elif track.source == "yandexmusic":
                used_seeds.add(track.identifier)
                query = f"ymrec:{track.identifier}"
            elif track.source == "vkmusic":
                used_seeds.add(track.identifier)
                query = f"vkrec:{track.identifier}"
            else:
                continue # Skip non-supported sources
            if query:
                search = await wavelink.Pool.fetch_tracks(query, node=vc.node)
                if search:
                    tracks = search.tracks.copy() if isinstance(search, wavelink.Playlist) else search
                    # Only add tracks that aren't duplicates
                    new_tracks = [t for t in tracks if t not in existing_tracks and t not in recommended_tracks]
                    recommended_tracks.extend(new_tracks)
                    # Check if we have enough tracks now
                    if len(recommended_tracks) >= max_tracks: break
                else: break
        except Exception as e:
            print(f"Unexpected error in get_recommendations: {e}")
            break
    print(f"Took {attempts} attempts to get {len(recommended_tracks)} recommendations.")
    return recommended_tracks[:max_tracks]

async def smart_recommendation(
    vc: wavelink.Player,
    *,
    populate_track: wavelink.Playable | None = None,
    max_population: int | None = 20,
) -> None:
    """
    Smart recommendation algorithm that populates the auto queue with recommended tracks
    based on player history and current queue.

    Parameters:
    - vc: The voice client player
    - populate_track: Optional specific track to use for recommendations
    - max_population: Maximum number of tracks to add to auto queue
    """
    # Include both history and current queue in weighted selections
    weighted_history: list[wavelink.Playable] = vc.queue.history[::-1][: max(5, 5 * vc._auto_weight)]
    weighted_queue: list[wavelink.Playable] = vc.queue[:max(5, 5 * vc._auto_weight)]
    weighted_upcoming: list[wavelink.Playable] = vc.auto_queue[: max(3, int((5 * vc._auto_weight) / 3))]
    choices: list[wavelink.Playable | None] = [
        *weighted_history,
        *weighted_queue,
        *weighted_upcoming,
        vc.current,
        vc._previous
    ]

    # Filter out None and duplicate tracks
    seeds: list[wavelink.Playable] = [t for t in choices if t is not None and t not in vc.queue]
    random.shuffle(seeds)

    if populate_track:
        seeds.insert(0, populate_track)

    # Consider both history and queue changes
    count: int = len(vc.queue.history) + len(vc.queue)
    changed_by: int = min(3, count) if vc._history_count is None else count - vc._history_count

    if changed_by > 0:
        vc._history_count = count

    # Get recent tracks from both history and queue
    changed_tracks: list[wavelink.Playable] = (
        vc.queue.history[::-1][:changed_by] +
        vc.queue[:changed_by]
    )

    # Prioritize recently changed tracks in seeds
    for track in changed_tracks[:3]:
        if track not in seeds:
            seeds.insert(0, track)

    # Get all tracks to check for duplicates
    history: list[wavelink.Playable] = (
        vc.auto_queue[:40] +
        vc.queue[:40] +
        vc.queue.history[:-41:-1] +
        vc.auto_queue.history[:-61:-1]
    )

    # Get recommendations using our separate function
    recommended_tracks = await get_recommendations(
        vc=vc,
        seed_tracks=seeds,
        max_tracks=max_population,
        existing_tracks=history
    )

    if not recommended_tracks and not vc.auto_queue:
        print(f'Player {vc.guild.id} could not load any songs via AutoPlay.')
        return

    # Add recommended tracks to auto queue
    added: int = 0
    random.shuffle(recommended_tracks) # Randomize to add variety

    for track in recommended_tracks:
        if track in history: continue

        track._recommended = True
        added += await vc.auto_queue.put_wait(track)

        if added >= max_population: break

    print(f'Player {vc.guild.id} added {added} tracks to the auto_queue via AutoPlay.')

# music search functions
pagelimit=12
def search_embed(arg: str, result: wavelink.Search, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"🔍 Search results: `{result if isinstance(result, wavelink.Playlist) else arg}`",
                          description=f"{len(result)} found", color=0x00ff00)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i].title}`", value=f"by `{result[i].author}`")
        i += 1
    return embed

def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, r: int):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success, row=r)
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if isinstance(self.ctx, commands.Context):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", ephemeral=True)
        if isinstance(self.ctx, discord.Interaction):
            if interaction.user != self.ctx.user:
                return await interaction.response.send_message(f"Only <@{self.ctx.user.id}> can interact with this message.", ephemeral=True)
        await interaction.response.defer()
        await interaction.delete_original_response()

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

class SearchView(discord.ui.View):
    def __init__(self, bot: commands.Bot, ctx: commands.Context, arg: str, result: wavelink.Search, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(bot, ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(bot, ctx, arg, result, 0, "⏪"))
            self.add_item(nextPage(bot, ctx, arg, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 1))
            self.add_item(DisabledButton("◀️", 1))
        if not last_index == len(result):
            self.add_item(nextPage(bot, ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(bot, ctx, arg, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 1))
            self.add_item(DisabledButton("⏩", 1))
        self.add_item(CancelButton(ctx, 1))

class nextPage(discord.ui.Button):
    def __init__(self, bot: commands.Bot, ctx: commands.Context, arg: str, result: wavelink.Search, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx, self.bot = result, index, arg, ctx, bot

    async def callback(self, interaction: discord.Interaction):
        if isinstance(self.ctx, commands.Context):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", ephemeral=True)
        if isinstance(self.ctx, discord.Interaction):
            if interaction.user != self.ctx.user:
                return await interaction.response.send_message(f"Only <@{self.ctx.user.id}> can interact with this message.", ephemeral=True)
        await interaction.response.edit_message(embed=search_embed(self.arg, self.result, self.index), 
                                                view=SearchView(self.bot, self.ctx, self.arg, self.result, self.index))

class SelectChoice(discord.ui.Select):
    def __init__(self, bot: commands.Bot, ctx: commands.Context | discord.Interaction, index: int, result: wavelink.Search):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx, self.bot = index, result, ctx, bot
        while i < len(result):
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i].title}"[:100], 
                                                      value=i, description=result[i].author[:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if isinstance(self.ctx, commands.Context):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", ephemeral=True)
        if isinstance(self.ctx, discord.Interaction):
            if interaction.user != self.ctx.user:
                return await interaction.response.send_message(f"Only <@{self.ctx.user.id}> can interact with this message.", ephemeral=True)
        await interaction.response.edit_message(content="Loading…", embed=None, view=None)
        if not self.ctx.guild.voice_client:
            try: 
                vc = await voice_channel_connector(self.ctx)
            except:
                if fixing: return await interaction.edit_original_response(content="Please try again later")
                print("ChannelTimeoutException")
                await interaction.edit_original_response(content="An error occured. Reconnecting…")
                await setup_hook_music(self.bot)
                return await interaction.edit_original_response(content="Please re-run the command")
            vc.autoplay = wavelink.AutoPlayMode.enabled
        else: vc: wavelink.Player = self.ctx.guild.voice_client
        vc.music_channel = self.ctx.channel

        selected = self.result[int(self.values[0])]
        await vc.queue.put_wait(selected)
        if not vc.playing: await vc.play(vc.queue.get())
        text, desc = "🎵 Queue music", f'`{selected.author} - {selected.title}` has been added to the queue'
        await interaction.edit_original_response(content=None, embed=music_embed(text, desc), view=None)

async def voice_channel_connector(ctx: commands.Context | discord.Interaction):
    if isinstance(ctx, commands.Context):
        member = ctx.author
    if isinstance(ctx, discord.Interaction):
        member = ctx.user
    nodes = []
    for n in ctx.bot.node_ids:
        try:
            node = wavelink.Pool.get_node(n)
            nodes.append(node)
        except: pass
    player = wavelink.Player(nodes=nodes)
    vc = await member.voice.channel.connect(cls=player, self_deaf=True)
    return vc

def check_bot_conflict(ctx: commands.Context | discord.Interaction):
    bot = ctx.guild.me
    moosic = bot.guild.get_member(1073823671392686162)
    if moosic:
        if moosic != bot and moosic in ctx.channel.members: return True

class MusicUtil(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def nodeadd(self, ctx: commands.Context, host: str, password: str):
        if check_if_not_owner(ctx): return
        await add_node(ctx, host, password)

    @commands.command()
    async def nodedel(self, ctx: commands.Context, index: int):
        if check_if_not_owner(ctx): return
        await delete_node(ctx, index)

    @commands.command()
    async def nodeview(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        await view_nodes(ctx)

    @commands.command(name="mreset")
    async def reset(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        await setup_hook_music(self.bot)

    @commands.command(name="msync")
    async def sync(self, ctx: commands.Context):
        if check_if_not_owner(ctx): return
        synced = await self.bot.tree.sync()
        await ctx.reply(f"Synced {len(synced)} slash commands")

    @commands.command(name="mstats")
    async def stats(self, ctx: commands.Context):
        stat_list = [
            f"serving {len(self.bot.users)} users in {len(self.bot.guilds)} guilds",
            f"will return in {round(self.bot.latency * 1000) if self.bot.latency != float('inf') else '♾️'}ms",
            f"{len(self.bot.tree.get_commands())} application commands found"
        ]
        await ctx.reply("\n".join(stat_list))

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicUtil(bot))