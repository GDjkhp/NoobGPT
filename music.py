import wavelink
from discord.ext import commands
import discord
from util_discord import command_check, get_database2, set_dj_role_db, check_if_master_or_admin, check_if_not_owner
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]
fixing=False

async def setup_hook_music(bot: commands.Bot):
    await wavelink.Pool.close()
    nodes = []
    data = await node_list()
    for lava in data:
        nodes.append(wavelink.Node(uri=lava["host"], password=lava["password"], retries=3600)) # 1 hour (1 retry = 60 secs)
    await wavelink.Pool.connect(client=bot, nodes=nodes)
    print("setup_hook_music ok")

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

async def check_if_dj(ctx: commands.Context | discord.Interaction):
    db = await get_database2(ctx.guild.id)
    if db.get("bot_dj_role"):
        if db["bot_dj_role"]:
            if isinstance(ctx, commands.Context): return ctx.guild.get_role(db["bot_dj_role"]) in ctx.author.roles
            if isinstance(ctx, discord.Interaction): return ctx.guild.get_role(db["bot_dj_role"]) in ctx.user.roles
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
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(content="🤨", embed=None, view=None)

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
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
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
                global fixing
                if not fixing: fixing=True
                else: return await interaction.edit_original_response(content="Please try again later.")
                print("ChannelTimeoutException")
                await interaction.edit_original_response(content="An error occured. Reconnecting…")
                await setup_hook_music(self.bot)
                fixing=False
                return await interaction.edit_original_response(content="Please re-run the command.")
            vc.autoplay = wavelink.AutoPlayMode.enabled
        else: vc: wavelink.Player = self.ctx.guild.voice_client
        vc.music_channel = self.ctx.channel

        selected = self.result[int(self.values[0])]
        await vc.queue.put_wait(selected)
        if not vc.playing: await vc.play(vc.queue.get())
        text, desc = "🎵 Song added to the queue", f'`{selected.title}` has been added to the queue.'
        await interaction.edit_original_response(content=None, embed=music_embed(text, desc), view=None)

async def voice_channel_connector(ctx: commands.Context | discord.Interaction):
    if isinstance(ctx, commands.Context):
        member = ctx.author
    if isinstance(ctx, discord.Interaction):
        member = ctx.user
    vc = await member.voice.channel.connect(cls=wavelink.Player, timeout=5, self_deaf=True)
    return vc

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
            f"will return in {round(self.bot.latency*1000)}ms",
            f"{len(self.bot.tree.get_commands())} application commands found"
        ]
        await ctx.reply("\n".join(stat_list))

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicUtil(bot))