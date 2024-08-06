import wavelink
from discord.ext import commands
import discord
from util_discord import command_check, get_database2, set_dj_role_db, check_if_master_or_admin
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]

async def setup_hook_music(bot: commands.Bot):
    await wavelink.Pool.close()
    data = await node_list()
    nodes = []
    for lava in data:
        nodes.append(wavelink.Node(uri=lava["host"], password=lava["password"], retries=3600)) # 1 hour (1 retry = 60 secs)
    await wavelink.Pool.connect(client=bot, nodes=nodes)

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

async def set_dj_role(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
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

async def check_if_dj(ctx: commands.Context):
    db = await get_database2(ctx.guild.id)
    if db.get("bot_dj_role"):
        if db["bot_dj_role"]:
            return ctx.guild.get_role(db["bot_dj_role"]) in ctx.author.roles
    return True

def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def music_now_playing_embed(track: wavelink.Playable):
    embed = discord.Embed(title="🎵 Now playing", color=0x00ff00,
                          description=f"[{track.title}]({track.uri})" if track.uri else track.title)
    embed.add_field(name="Author", value=track.author, inline=False)
    if track.album.name: embed.add_field(name="Album", value=track.album.name, inline=False)
    embed.add_field(name="Duration", value=format_mil(track.length), inline=False)

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
    else: print(track.source)
    return embed

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

# music search functions
pagelimit=12
def search_embed(arg: str, result: wavelink.Search, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"🔍 Search results: `{result if isinstance(result, wavelink.Playlist) else arg}`",
                          description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url="https://gdjkhp.github.io/img/771384-512.png")
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i].title}`", value=result[i].author)
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
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.delete()

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

class SearchView(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: wavelink.Search, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(ctx, arg, result, 0, "⏪"))
            self.add_item(nextPage(ctx, arg, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 1))
            self.add_item(DisabledButton("◀️", 1))
        if not last_index == len(result):
            self.add_item(nextPage(ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(ctx, arg, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 1))
            self.add_item(DisabledButton("⏩", 1))
        self.add_item(CancelButton(ctx, 1))

class nextPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: wavelink.Search, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        await interaction.message.edit(embed=search_embed(self.arg, self.result, self.index), 
                                       view=SearchView(self.ctx, self.arg, self.result, self.index))

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: wavelink.Search):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result):
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i].title}"[:100], 
                                                      value=i, description=result[i].author[:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if not self.ctx.voice_client:
            vc = await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
            vc.autoplay = wavelink.AutoPlayMode.enabled
        else: vc: wavelink.Player = self.ctx.voice_client
        vc.music_channel = self.ctx.message.channel

        selected = self.result[int(self.values[0])]
        await vc.queue.put_wait(selected)
        text, desc = "🎵 Song added to the queue", f'`{selected.title}` has been added to the queue.'
        await interaction.message.edit(embed=music_embed(text, desc), view=None)
        if not vc.playing: await vc.play(vc.queue.get())