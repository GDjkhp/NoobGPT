import discord
from discord.ext import commands
import aiohttp
from PIL import Image
import io
from util_discord import command_check

BASE_URL = "https://api.mangadex.org"
provider = "https://gdjkhp.github.io/img/mangadex-logo.png"
pagelimit=12

async def help_manga(ctx: commands.Context):
    if await command_check(ctx, "manga", "media"): return
    sources = "`-dex`: mangadex\n"
    sources+= "`-nato`: manganato"
    await ctx.reply(sources)

async def dex_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "manga", "media"): return
    if not arg: return await ctx.reply("usage: `-dex <query>`")
    msg = await ctx.reply("please wait")
    res = await search_manga(arg)
    if not res: return await msg.edit(content="none found")
    await get_statistics(res)
    await msg.edit(view=SearchView(ctx, arg, res, 0), embed=buildSearch(arg, res, 0), content=None)

async def req_real(url: str, params: dict=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()

async def convert_to_webp(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
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
            
async def search_manga(query):
    search_url = f"{BASE_URL}/manga"
    params = {"title": query}
    data = await req_real(search_url, params)
    if data["total"] > 0: return data["data"]

async def get_chapters(manga_id, offset):
    chapters_url = f"{BASE_URL}/manga/{manga_id}/feed"
    params = {"translatedLanguage[]": ["en"], "order[chapter]": "asc", "limit": 500, "offset": offset}
    data = await req_real(chapters_url, params)
    return data["data"]

async def get_pages(chapter_id):
    pages_url = f"{BASE_URL}/at-home/server/{chapter_id}"
    data = await req_real(pages_url)
    pages = []
    for image in data["chapter"]["data"]:
        pages.append(f'https://uploads.mangadex.org/data/{data["chapter"]["hash"]}/{image}')
    return pages

async def get_cover_art(manga):
    cover_id = next((item["id"] for item in manga["relationships"] if item["type"] == "cover_art"), None)
    if not cover_id: return None
    response = await req_real(f"{BASE_URL}/cover/{cover_id}")
    return f'https://uploads.mangadex.org/covers/{manga["id"]}/{response["data"]["attributes"]["fileName"]}'

async def get_author(manga):
    author_url = f"{BASE_URL}/author"
    author_ids = []
    for item in manga["relationships"]:
        if item["id"] in author_ids: continue
        if item["type"] == "author" or item["type"] == "artist":
            author_ids.append(item["id"])
    if not author_ids: return None
    params = {"ids[]": author_ids}
    response = await req_real(author_url, params)
    authors = []
    for author in response["data"]:
        authors.append(author["attributes"]["name"])
    return ", ".join(authors)

async def get_scanlation(chapter):
    group_url = f"{BASE_URL}/group"
    group_ids = []
    for item in chapter["relationships"]:
        if item["id"] in group_ids: continue
        if item["type"] == "scanlation_group":
            group_ids.append(item["id"])
    if not group_ids: return None
    params = {"ids[]": group_ids}
    response = await req_real(group_url, params)
    groups = []
    for group in response["data"]:
        groups.append(group["attributes"]["name"])
    return ", ".join(groups)

async def get_statistics(manga):
    stats_url = f"{BASE_URL}/statistics/manga/"
    ids = []
    for item in manga:
        ids.append(item["id"])
    params = {"manga[]": ids}
    response = await req_real(stats_url, params)
    for item in manga:
        item["stats"] = response["statistics"][item["id"]]

def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        stats = f"⭐{round(result[i]['stats']['rating']['bayesian'], 2)} 🔖{format_number(result[i]['stats']['follows'])}"
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['attributes']['title']['en']}`", value=stats)
        i += 1
    return embed

def buildManga(details: dict, count: int, total: int) -> discord.Embed:
    tags = []
    for tag in details['attributes']['tags']:
        tags.append(tag['attributes']['name']['en'])
    author = f"**Author:** {details['author']}\n"
    year = f"**Year:** {details['attributes']['year']}\n"
    status = f"**Status:** {details['attributes']['status']}\n"
    volumes = f"**Volumes:** {details['attributes']['lastVolume'] if details['attributes']['lastVolume'] else '⁉️'}\n"
    chapters = f"**Chapters:** {details['attributes']['lastChapter'] if details['attributes']['lastChapter'] else '⁉️'}\n"
    genres = f"**Genres:** {', '.join(tags)}\n\n"
    desc = f"{details['attributes']['description']['en'] if details['attributes']['description'] else ''}"
    desc = author+year+status+volumes+chapters+genres+desc
    embed = discord.Embed(title=details['attributes']['title']['en'], description=desc, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_footer(text=f"{min(count, total)}/{total}")
    return embed

def buildPage(pages, pagenumber, chapters, index, details, group) -> discord.Embed:
    title = f'\n{chapters[index]["attributes"]["title"]}' if chapters[index]["attributes"]["title"] else ""
    group = f"\n{group}" if group else ""
    ch = chapters[index]["attributes"]["chapter"] if chapters[index]["attributes"]["chapter"] else "⁉️"
    desc = f'Chapter {ch}{title}\n{group}' # {index+1}/{len(chapters)}
    embed = discord.Embed(title=details['attributes']['title']['en'], description=desc, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_footer(text=f"{pagenumber+1}/{len(pages)}")
    return embed

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

# search
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

class nextPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        await interaction.message.edit(embed=buildSearch(self.arg, self.result, self.index), 
                                       view=SearchView(self.ctx, self.arg, self.result, self.index))
        
class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result):
            stats = f"⭐{round(result[i]['stats']['rating']['bayesian'], 2)} 🔖{format_number(result[i]['stats']['follows'])}"
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i]['attributes']['title']['en']}"[:100], value=i, 
                                                      description=stats)
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        selected = self.result[int(self.values[0])]
        chapters, offset = [], 0
        while True:
            collect = await get_chapters(selected["id"], offset)
            if not collect: break
            chapters += collect
            offset+=500
        selected["cover"] = await convert_to_webp(await get_cover_art(selected))
        selected["author"] = await get_author(selected)
        await interaction.message.delete()
        await interaction.followup.send(embed=buildManga(selected, pagelimit, len(chapters)),
                                        view=ChapterView(self.ctx, selected, chapters, 0), 
                                        file=discord.File(io.BytesIO(selected["cover"]), filename='image.webp'))

# chapter
class nextPageCH(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: dict, index: int, row: int, l: str, chapters: list):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx, self.chapters = details, index, ctx, chapters
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        await interaction.message.delete()
        await interaction.followup.send(embed=buildManga(self.details, self.index+pagelimit, len(self.chapters)),
                                        view=ChapterView(self.ctx, self.details, self.chapters, self.index),
                                        file=discord.File(io.BytesIO(self.details["cover"]), filename='image.webp'))

class ChapterView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, chapters: list, index: int):
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
    def __init__(self, ctx: commands.Context, index: int, chapters: list, details: dict, row: int, l: str = None):
        e = None
        if not l: 
            l = chapters[index]["attributes"]["chapter"] if chapters[index]["attributes"]["chapter"] else "⁉️"
            style = discord.ButtonStyle.primary
        else:
            e, l = l, None
            style = discord.ButtonStyle.success
        super().__init__(label=l, style=style, row=row, emoji=e)
        self.index, self.chapters, self.ctx, self.details = index, chapters, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        pages = await get_pages(self.chapters[self.index]["id"])
        if not pages: 
            await interaction.message.edit(content="no pages found")
            return await interaction.followup.send(view=ChapterView(self.ctx, self.details, self.chapters, (self.index//pagelimit)*pagelimit),
                                                   embed=buildManga(self.details, (self.index//pagelimit)*pagelimit+pagelimit, len(self.chapters)),
                                                   file=discord.File(io.BytesIO(self.details["cover"]), filename='image.webp'))
        group = await get_scanlation(self.chapters[self.index])
        file = await convert_to_webp(pages[0])
        await interaction.message.delete()
        await interaction.followup.send(view=PageView(self.ctx, self.details, pages, self.index, 0, self.chapters, group),
                                        embed=buildPage(pages, 0, self.chapters, self.index, self.details, group), 
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))

# page
class nextPageReal(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: dict, pagenumber: int, row: int, l: str, pages: list, index: int, chapters: list, group: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.pagenumber, self.ctx, self.pages, self.index, self.chapters, self.group = details, pagenumber, ctx, pages, index, chapters, group
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        file = await convert_to_webp(self.pages[self.pagenumber])
        await interaction.message.delete()
        await interaction.followup.send(embed=buildPage(self.pages, self.pagenumber, self.chapters, self.index, self.details, self.group),
                                        view=PageView(self.ctx, self.details, self.pages, self.index, self.pagenumber, self.chapters, self.group),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))

class PageView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, pages: list, index: int, pagenumber: int, chapters: list, group: str):
        super().__init__(timeout=None)
        column, row, pageviewlimit = 0, -1, 8
        i = (pagenumber // pageviewlimit) * pageviewlimit
        while i < len(pages):
            if column % 4 == 0: row += 1
            if (i < ((pagenumber // pageviewlimit) * pageviewlimit)+pageviewlimit): 
                self.add_item(ButtonPage(ctx, i, pages, details, row, index, chapters, group))
            i += 1
            column += 1
        if not pagenumber == 0:
            self.add_item(nextPageReal(ctx, details, 0, 2, "⏪", pages, index, chapters, group))
            self.add_item(nextPageReal(ctx, details, pagenumber - 1, 2, "◀️", pages, index, chapters, group))
        else:
            self.add_item(DisabledButton("⏪", 2))
            self.add_item(DisabledButton("◀️", 2))
        if pagenumber + 1 < len(pages): 
            self.add_item(nextPageReal(ctx, details, pagenumber+1, 2, "▶️", pages, index, chapters, group))
            self.add_item(nextPageReal(ctx, details, len(pages)-1, 2, "⏩", pages, index, chapters, group))
        else:
            self.add_item(DisabledButton("▶️", 2))
            self.add_item(DisabledButton("⏩", 2))
        if index > 0: self.add_item(ButtonChapter(ctx, index-1, chapters, details, 3, "⏮️"))
        else: self.add_item(DisabledButton("⏮️", 3))
        self.add_item(CancelButton(ctx, 3))
        self.add_item(ButtonBack(ctx, details, 3, index, chapters))
        if index < len(chapters): self.add_item(ButtonChapter(ctx, index+1, chapters, details, 3, "⏭️"))
        else: self.add_item(DisabledButton("⏭️", 3))

class ButtonPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, pagenumber: int, pages: list, details: dict, row: int, index: int, chapters: list, group: str):
        super().__init__(label=str(pagenumber+1), style=discord.ButtonStyle.primary, row=row)
        self.pagenumber, self.pages, self.ctx, self.details, self.index, self.chapters, self.group = pagenumber, pages, ctx, details, index, chapters, group
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        file = await convert_to_webp(self.pages[self.pagenumber])
        await interaction.message.delete()
        await interaction.followup.send(view=PageView(self.ctx, self.details, self.pages, self.index, self.pagenumber, self.chapters, self.group),
                                        embed=buildPage(self.pages, self.pagenumber, self.chapters, self.index, self.details, self.group),
                                        file=discord.File(io.BytesIO(file), filename='image.webp'))

class ButtonBack(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: dict, row: int, index: int, chapters: list):
        super().__init__(emoji="📖", style=discord.ButtonStyle.success, row=row)
        self.ctx, self.details, self.index, self.chapters = ctx, details, index, chapters

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        if interaction.message.attachments: await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(view=None, embed=None, content="please wait")
        await interaction.response.defer()
        await interaction.message.delete()
        await interaction.followup.send(view=ChapterView(self.ctx, self.details, self.chapters, (self.index//pagelimit)*pagelimit), 
                                        embed=buildManga(self.details, (self.index//pagelimit)*pagelimit+pagelimit, len(self.chapters)),
                                        file=discord.File(io.BytesIO(self.details["cover"]), filename='image.webp'))