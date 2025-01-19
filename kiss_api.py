import discord
from discord.ext import commands
from discord import app_commands
from util_discord import command_check, get_guild_prefix, check_if_not_owner, description_helper
import kisskh_
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]
kiss = "https://kisskh.id"
kiss_api = kisskh_.KissKHApi(kiss)
provider="https://gdjkhp.github.io/img/kisskh.png"
ubel="https://gdjkhp.github.io/ubel/?url=" # FIXME: it works on my machine
pagelimit=12

async def get_domain():
    global kiss
    cursor = mycol.find()
    data = await cursor.to_list(None)
    kiss = data[0]["kiss"]

async def set_domain(ctx: commands.Context, arg: str):
    await mycol.update_one({}, {"$set": {"kiss": arg}})
    await get_domain()
    await ctx.reply(kiss)

async def kisskh_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}kiss <query>`")
    await get_domain()
    kiss_api.set_base_url(kiss)
    results = await kiss_api.search_dramas_by_query(arg)
    if not results: return await ctx.reply("none found")
    await ctx.reply(embed=buildSearch(arg, results, 0), view=SearchView(ctx, arg, results, 0))

class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, r: int):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success, row=r)
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        await interaction.delete_original_response()

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

# search
class nextPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(embed=buildSearch(self.arg, self.result, self.index), 
                                                view=SearchView(self.ctx, self.arg, self.result, self.index))

class SearchView(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int):
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

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: kisskh_.Search):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i].title}"[:100], value=i, 
                                                      description=str(result[i].id)[:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        id = self.result[int(self.values[0])].id
        selected = await kiss_api.get_drama(id)
        await interaction.edit_original_response(embed=buildKiss(selected), view=EpisodeView(self.ctx, selected, 0))

# episode
class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx = details, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=EpisodeView(self.ctx, self.details, self.index))

class EpisodeView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: kisskh_.Drama, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(details.episodes)
        while i < len(details.episodes):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonEpisode(ctx, i, details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪"))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(details.episodes):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️"))
            max_page = get_max_page(len(details.episodes))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, details: kisskh_.Drama, row: int):
        super().__init__(label=str(details.episodes[index].number), style=discord.ButtonStyle.primary, row=row)
        self.index, self.ctx, self.details = index, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        link = await kiss_api.get_stream_url(self.details.episodes[self.index].id)
        msg_content = f"{self.details.title}: Episode {self.details.episodes[self.index].number}"
        await interaction.followup.send(msg_content, view=WatchView([link]), ephemeral=True)

class WatchView(discord.ui.View):
    def __init__(self, links: list):
        super().__init__(timeout=None)
        for x in links[:25]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x, emoji="🎞️",
                                            label=f"Watch Full HD Movies & TV Shows"))

# utils
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

def buildSearch(arg: str, result: kisskh_.Search, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i].title}`", value=f"{result[i].episodes_count} episode/s")
        i += 1
    return embed

def buildKiss(details: kisskh_.Drama) -> discord.Embed:
    desc = [
        f"**Type:** {details.type}",
        f"**Episodes:** {details.episodes_count}",
        f"**Country:** {details.country}",
        f"**Release Date:** {details.release_date}",
        f"**Status:** {details.status}",
        f"\n{details.description}",
    ]
    embed = discord.Embed(title=details.title, description="\n".join(desc), color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url=details.thumbnail)
    embed.set_footer(text="Note: Play .m3u8 files with VLC/MPV media player :)")
    return embed

class CogKisskh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rkiss(self, ctx: commands.Context, arg=None):
        if check_if_not_owner(ctx): return
        await set_domain(ctx, arg)

    @commands.hybrid_command(description=f"{description_helper['emojis']['tv']} kisskh")
    @app_commands.describe(query="Search query")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def kiss(self, ctx: commands.Context, *, query:str=None):
        await kisskh_search(ctx, query)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogKisskh(bot))