import discord
from bs4 import BeautifulSoup as BS
import aiohttp
from discord.ext import commands
import os
import re
from util_discord import command_check
from curl_cffi.requests import AsyncSession
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

session = AsyncSession(impersonate='chrome110')
headers = {"cookie": os.getenv('PAHE')}
pagelimit=12
provider="https://gdjkhp.github.io/img/apdoesnthavelogotheysaidapistooplaintheysaid.png"

async def help_anime(ctx: commands.Context):
    if await command_check(ctx, "anime", "media"): return
    sources = ["`-gogo` gogoanime", "`-pahe` animepahe"]
    await ctx.reply("\n".join(sources))

async def new_req_old(url: str, headers: dict, json_mode: bool):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200: 
                return await response.json() if json_mode else await response.read()
async def new_req(url: str, headers: dict, json_mode: bool):
    req = await session.get(url, headers=headers)
    return req.json() if json_mode else req.content
def soupify(data): return BS(data, "lxml")
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        value = f"**{result[i]['type']}** - {result[i]['episodes']} {'episodes' if result[i]['episodes'] > 1 else 'episode'}\n({result[i]['status']})"
        value+= f"\n{result[i]['season']} {result[i]['year']}"
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['title']}`", value=value)
        i += 1
    return embed
def format_links(string: str, links: list):
    items = string.split('\n', 1)[-1].split(', ')
    result = "**External Links:**\n"
    for i in range(len(links)):
        result += f"[{items[i]}]({links[i]}), "
    return result.rstrip(", ")
def enclose_words(texts: list[str]):
    new_list = []
    for word in texts:
        split = word.split(":")
        split[0] = f"**{split[0]}:**"
        new_list.append(" ".join(split))
    return new_list
def buildAnime(details: dict) -> discord.Embed:
    cook_deets = "\n".join(details["details"])
    cook_deets+= f'\n**Genres:** {", ".join(details["genres"])}'
    embed = discord.Embed(title=details['title'], description=cook_deets, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url = details['poster'])
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed

async def pahe_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "anime", "media"): return
    if not arg: return await ctx.reply("usage: `-pahe <query>`")
    results = await new_req(f"https://animepahe.ru/api?m=search&q={arg.replace(' ', '+')}", headers, True)
    if not results: return await ctx.reply("none found")
    await ctx.reply(embed=buildSearch(arg, results["data"], 0), view=SearchView(ctx, arg, results["data"], 0))

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
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i]['title']}"[:100], value=i, 
                                                      description=f"{result[i]['season']} {result[i]['year']}")
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        selected = self.result[int(self.values[0])]
        r_search = await new_req(f"https://animepahe.ru/api?m=release&id={selected['session']}&sort=episode_asc&page=1", headers, True)
        if not r_search.get('data'): return await interaction.message.edit(content="no episodes found", embed=None)
        req = await new_req(f"https://animepahe.ru/play/{selected['session']}/{r_search['data'][0]['session']}", headers, False)
        soup = soupify(req)
        items = soup.find("div", {"class": "clusterize-scroll"}).findAll("a")
        urls = [items[i].get("href") for i in range(len(items))]
        ep_texts = [items[i].text for i in range(len(items))]

        req = await new_req(f"https://animepahe.ru/play/{selected['session']}", headers, False)
        soup = soupify(req)
        details = soup.find("div", {"class": "anime-info"}).findAll("p")
        external = soup.find("p", {"class": "external-links"}).findAll("a")
        genres = soup.find("div", {"class": "anime-genre"}).findAll("li")
        selected["genres"] = [re.sub(r"^\s+|\s+$|\s+(?=\s)", "", genres[i].text) for i in range(len(genres))]
        not_final = [re.sub(r"^\s+|\s+$|\s+(?=\s)", "", details[i].text) for i in range(len(details))]
        externals = [external[i].get("href").replace("//", "https://") for i in range(len(external))]
        selected["details"] = enclose_words(not_final)
        selected["details"][len(selected["details"])-1] = format_links(selected["details"][len(selected["details"])-1], externals)
        await interaction.message.edit(embed=buildAnime(selected), view=EpisodeView(self.ctx, selected, urls, ep_texts, 0))

# episode
class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str, urls: list, ep_texts: list):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx, self.urls, self.ep_texts = details, index, ctx, urls, ep_texts
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        await interaction.message.edit(view=EpisodeView(self.ctx, self.details, self.urls, self.ep_texts, self.index))

class EpisodeView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, urls: list, ep_texts: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(urls)
        while i < len(urls):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonEpisode(ctx, i, urls[i], ep_texts[i], details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪", urls, ep_texts))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️", urls, ep_texts))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(urls):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️", urls, ep_texts))
            max_page = get_max_page(len(urls))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩", urls, ep_texts))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, url_session: str, ep_text: str, details: dict, row: int):
        super().__init__(label=ep_text.replace("Episode ", ""), style=discord.ButtonStyle.primary, row=row)
        self.index, self.url_session, self.ctx, self.details, self.ep_text = index, url_session, ctx, details, ep_text
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(f"https://animepahe.ru{self.url_session}", headers, False)
        soup = soupify(req)
        items = soup.find("div", {"id": "pickDownload"}).findAll("a")
        urls = [items[i].get("href") for i in range(len(items))]
        texts = [items[i].text for i in range(len(items))]
        msg_content = f"{self.details['title']}: {self.ep_text}"
        for x in range(len(urls)):
            msg_content += f"\n{x+1}. {texts[x]}"
        await interaction.followup.send(msg_content, view=DownloadView(self.ctx, urls, self.details, self.index, texts, self.ep_text), 
                                        ephemeral=True)

class ButtonDownload(discord.ui.Button):
    def __init__(self, ctx: commands.Context, url_fake: str, l: str, details: dict, index: int, text: str, ep_text: str):
        super().__init__(label=l+1)
        self.url_fake, self.ctx, self.details, self.index, self.text, self.ep_text = url_fake, ctx, details, index, text, ep_text

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(self.url_fake, None, False)
        soup = soupify(req)
        script_tag = soup.find("script")
        match = re.search(r"https://kwik\.si/f/\w+", script_tag.string)
        if match: 
            await interaction.followup.send(f"[{self.details['title']}: {self.ep_text} [{self.text}]]({match.group()})", 
                                            ephemeral=True)

class DownloadView(discord.ui.View):
    def __init__(self, ctx: commands.Context, urls: list, details: dict, index: int, texts: list, ep_text: str):
        super().__init__(timeout=None)
        for x in range(len(urls)):
            self.add_item(ButtonDownload(ctx, urls[x], x, details, index, texts[x], ep_text))

class CogPahe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pahe(self, ctx: commands.Context, *, arg=None):
        await pahe_search(ctx, arg)

    @commands.command()
    async def anime(self, ctx: commands.Context):
        await help_anime(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogPahe(bot))