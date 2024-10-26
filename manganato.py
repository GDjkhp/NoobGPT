import discord
from discord import app_commands
from discord.ext import commands
from manganelo import get_search_results, fetch_image, SearchResult, StoryPage, Chapter
from PIL import Image
import io
from util_discord import command_check, description_helper, get_guild_prefix

provider = "https://gdjkhp.github.io/img/nt.png"
pagelimit=12

async def nato_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "manga", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}nato <query>`")
    msg = await ctx.reply("please wait")
    res = await get_search_results(arg)
    if not res: return await msg.edit(content="none found")
    await msg.edit(view=SearchView(ctx, arg, res, 0), embed=buildSearch(arg, res, 0), content=None)

async def convert_to_webp(url):
    image_data = await fetch_image(url)
    image = Image.open(io.BytesIO(image_data))
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='WebP')
    image_bytes.seek(0)
    return image_bytes.getvalue()
            
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

def format_number(num):
    if 1000 <= num < 1000000:
        return f"{num // 1000}k"
    elif 1000000 <= num < 1000000000:
        return f"{num // 1000000}m"
    elif 1000000000 <= num < 1000000000000:
        return f"{num // 1000000000}b"
    else:
        return str(num)

def buildSearch(arg: str, result: list[SearchResult], index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        stats = f"⭐{round(result[i].rating, 2)} 👁️{format_number(result[i].views)}"
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i].title}`", value=stats)
        i += 1
    return embed

def buildManga(details: StoryPage, count: int, total: int) -> discord.Embed:
    tags = []
    for tag in details.genres:
        tags.append(tag)
    author = f"**Author:** {', '.join(details.authors)}\n"
    genres = f"**Genres:** {', '.join(tags)}\n\n"
    desc = author+genres+details.description
    embed = discord.Embed(title=details.title, description=desc, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_footer(text=f"{min(count, total)}/{total}")
    return embed

def buildPage(pages: list[str], pagenumber: int, chapters: list[Chapter], index: int, details: StoryPage) -> discord.Embed:
    embed = discord.Embed(title=details.title, description=chapters[index].title, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_footer(text=f"{pagenumber+1}/{len(pages)}")
    return embed

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
class SearchView(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: list[SearchResult], index: int):
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
    def __init__(self, ctx: commands.Context, arg: str, result: list[SearchResult], index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(embed=buildSearch(self.arg, self.result, self.index), 
                                                view=SearchView(self.ctx, self.arg, self.result, self.index))
        
class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list[SearchResult]):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result):
            stats = f"⭐{round(result[i].rating, 2)} 👁️{format_number(result[i].views)}"
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i].title}"[:100], value=i, 
                                                      description=stats)
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        selected = await self.result[int(self.values[0])].story_page
        file = await convert_to_webp(selected.icon_url)
        await interaction.followup.send(embed=buildManga(selected, pagelimit, len(selected.chapter_list)),
                                        view=ChapterView(self.ctx, selected, selected.chapter_list, 0), 
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()

# chapter
class nextPageCH(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: StoryPage, index: int, row: int, l: str, chapters: list[Chapter]):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx, self.chapters = details, index, ctx, chapters
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        # if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.response.defer()
        file = await convert_to_webp(self.details.icon_url)
        await interaction.followup.send(embed=buildManga(self.details, self.index+pagelimit, len(self.chapters)),
                                        view=ChapterView(self.ctx, self.details, self.chapters, self.index),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()

class ChapterView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: StoryPage, chapters: list[Chapter], index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(chapters)
        while i < len(chapters):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonChapter(ctx, i, chapters, details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageCH(ctx, details, 0, 3, "⏪", chapters))
            self.add_item(nextPageCH(ctx, details, index - pagelimit, 3, "◀️", chapters))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(chapters):
            self.add_item(nextPageCH(ctx, details, last_index, 3, "▶️", chapters))
            max_page = get_max_page(len(chapters))
            self.add_item(nextPageCH(ctx, details, max_page, 3, "⏩", chapters))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonChapter(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, chapters: list[Chapter], details: StoryPage, row: int, l: str = None):
        e = None
        if not l: 
            l = str(chapters[index].chapter) if chapters[index].chapter else "⁉️"
            style = discord.ButtonStyle.primary
        else:
            e, l = l, None
            style = discord.ButtonStyle.success
        super().__init__(label=l, style=style, row=row, emoji=e)
        self.index, self.chapters, self.ctx, self.details = index, chapters, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        # if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.response.defer()
        pages = await self.details.chapter_list[self.index].download()
        if not pages: 
            await interaction.followup.send(content="no pages found")
            file = await convert_to_webp(self.details.icon_url)
            await interaction.followup.send(view=ChapterView(self.ctx, self.details, self.chapters, (self.index//pagelimit)*pagelimit),
                                            embed=buildManga(self.details, (self.index//pagelimit)*pagelimit+pagelimit, len(self.chapters)),
                                            file=discord.File(io.BytesIO(file), filename='image.webp'))
        else:
            file = await convert_to_webp(pages[0])
            await interaction.followup.send(view=PageView(self.ctx, self.details, pages, self.index, 0, self.chapters),
                                            embed=buildPage(pages, 0, self.chapters, self.index, self.details), 
                                            file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()

# page
class nextPageReal(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: StoryPage, pagenumber: int, row: int, l: str, pages: list, index: int, chapters: list[Chapter]):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.pagenumber, self.ctx, self.pages, self.index, self.chapters = details, pagenumber, ctx, pages, index, chapters
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        # if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.response.defer()
        file = await convert_to_webp(self.pages[self.pagenumber])
        await interaction.followup.send(embed=buildPage(self.pages, self.pagenumber, self.chapters, self.index, self.details),
                                        view=PageView(self.ctx, self.details, self.pages, self.index, self.pagenumber, self.chapters),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()

class PageView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: StoryPage, pages: list, index: int, pagenumber: int, chapters: list[Chapter]):
        super().__init__(timeout=None)
        column, row, pageviewlimit = 0, -1, 8
        i = (pagenumber // pageviewlimit) * pageviewlimit
        while i < len(pages):
            if column % 4 == 0: row += 1
            if (i < ((pagenumber // pageviewlimit) * pageviewlimit)+pageviewlimit): 
                self.add_item(ButtonPage(ctx, i, pages, details, row, index, chapters))
            i += 1
            column += 1
        if not pagenumber == 0:
            self.add_item(nextPageReal(ctx, details, 0, 2, "⏪", pages, index, chapters))
            self.add_item(nextPageReal(ctx, details, pagenumber - 1, 2, "◀️", pages, index, chapters))
        else:
            self.add_item(DisabledButton("⏪", 2))
            self.add_item(DisabledButton("◀️", 2))
        if pagenumber + 1 < len(pages): 
            self.add_item(nextPageReal(ctx, details, pagenumber+1, 2, "▶️", pages, index, chapters))
            self.add_item(nextPageReal(ctx, details, len(pages)-1, 2, "⏩", pages, index, chapters))
        else:
            self.add_item(DisabledButton("▶️", 2))
            self.add_item(DisabledButton("⏩", 2))
        if index > 0: self.add_item(ButtonChapter(ctx, index-1, chapters, details, 3, "⏮️"))
        else: self.add_item(DisabledButton("⏮️", 3))
        self.add_item(CancelButton(ctx, 3))
        self.add_item(ButtonBack(ctx, details, 3, index, chapters))
        if index+1 < len(chapters): self.add_item(ButtonChapter(ctx, index+1, chapters, details, 3, "⏭️"))
        else: self.add_item(DisabledButton("⏭️", 3))

class ButtonPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, pagenumber: int, pages: list, details: StoryPage, row: int, index: int, chapters: list[Chapter]):
        super().__init__(label=str(pagenumber+1), style=discord.ButtonStyle.primary, row=row)
        self.pagenumber, self.pages, self.ctx, self.details, self.index, self.chapters = pagenumber, pages, ctx, details, index, chapters
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        # if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.response.defer()
        file = await convert_to_webp(self.pages[self.pagenumber])
        await interaction.followup.send(view=PageView(self.ctx, self.details, self.pages, self.index, self.pagenumber, self.chapters, self.group),
                                        embed=buildPage(self.pages, self.pagenumber, self.chapters, self.index, self.details, self.group),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()

class ButtonBack(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: StoryPage, row: int, index: int, chapters: list[Chapter]):
        super().__init__(emoji="📖", style=discord.ButtonStyle.success, row=row)
        self.ctx, self.details, self.index, self.chapters = ctx, details, index, chapters

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        # if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.response.defer()
        file = await convert_to_webp(self.details.icon_url)
        await interaction.followup.send(view=ChapterView(self.ctx, self.details, self.chapters, (self.index//pagelimit)*pagelimit), 
                                        embed=buildManga(self.details, (self.index//pagelimit)*pagelimit+pagelimit, len(self.chapters)),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))
        await interaction.delete_original_response()
        
class CogNato(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f"{description_helper['emojis']['manga']} manganato")
    @app_commands.describe(query="Search query")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def nato(self, ctx: commands.Context, *, query:str=None):
        await nato_search(ctx, query)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogNato(bot))