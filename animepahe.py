import discord
from bs4 import BeautifulSoup as BS
from curl_cffi.requests import AsyncSession
from discord.ext import commands
import os
import re
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

async def new_req(url: str, use_headers: bool):
    return await session.get(url, headers=headers if use_headers else None)
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        value = f"**{result[i]['type']}** - {result[i]['episodes']} {'episodes' if result[i]['episodes'] > 1 else 'episode'} ({result[i]['status']})"
        value+= f"\n{result[i]['season']} {result[i]['year']}"
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['title']}`", value=value)
        i += 1
    return embed
def buildAnime(details: dict) -> discord.Embed:
    embed = discord.Embed(title=details['title'], description=f"{details['season']} {details['year']}", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url = details['poster'])
    embed.add_field(name="Type", value=details['type'])
    embed.add_field(name="Episodes", value=details['episodes'])
    embed.add_field(name="Status", value=details['status'])
    embed.add_field(name="Score", value=details['score'])
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed

async def pahe_search(ctx: commands.Context, arg: str):
    if not arg: return await ctx.reply("y r u doin this")
    response = await new_req(f"https://animepahe.ru/api?m=search&q={arg.replace(' ', '+')}", True)
    if not response: return await ctx.reply("none found")
    results = response.json()
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
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i]['title']}", value=i, 
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
        req = await new_req(f"https://animepahe.ru/api?m=release&id={selected['session']}&sort=episode_asc&page=1", True)
        r_search = req.json()
        req = await new_req(f"https://animepahe.ru/play/{selected['session']}/{r_search['data'][0]['session']}", True)
        soup = BS(req.content, "lxml")
        items = soup.find("div", {"class": "clusterize-scroll"}).findAll("a")
        urls = [items[i].get("href") for i in range(len(items))]
        await interaction.message.edit(embed=buildAnime(selected), view=EpisodeView(self.ctx, selected, urls, 0))

# episode
class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str, urls: list):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx, self.urls = details, index, ctx, urls
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        await interaction.message.edit(embed=buildAnime(self.details), view=EpisodeView(self.ctx, self.details, self.urls, self.index))

class EpisodeView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, urls: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(urls)
        while i < len(urls):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonEpisode(ctx, i, urls[i], details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪", urls))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️", urls))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(urls):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️", urls))
            max_page = get_max_page(len(urls))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩", urls))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, url_session: list, details: dict, row: int):
        super().__init__(label=index+1, style=discord.ButtonStyle.primary, row=row)
        self.index, self.url_session, self.ctx, self.details = index, url_session, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(f"https://animepahe.ru{self.url_session}", True)
        soup = BS(req.content, "lxml")
        items = soup.find("div", {"id": "pickDownload"}).findAll("a")
        urls = [items[i].get("href") for i in range(len(items))]
        texts = [items[i].text for i in range(len(items))]
        msg_content = f"{self.details['title']}: Episode {self.index+1}"
        for x in range(len(urls)):
            msg_content += f"\n{x+1}. {texts[x]}"
        await interaction.followup.send(msg_content, view=DownloadView(self.ctx, urls, self.details, self.index, texts), ephemeral=True)

class ButtonDownload(discord.ui.Button):
    def __init__(self, ctx: commands.Context, url_fake: str, l: str, details: dict, index: int, text: str):
        super().__init__(label=l+1)
        self.url_fake, self.ctx, self.details, self.l, self.index, self.text = url_fake, ctx, details, l, index, text

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(self.url_fake, False)
        soup = BS(req.content, "lxml")
        script_tag = soup.find("script")
        match = re.search(r"https://kwik\.si/f/\w+", script_tag.string)
        if match: 
            await interaction.followup.send(f"[{self.details['title']}: Episode {self.index+1} [{self.text}]]({match.group()})", 
                                            ephemeral=True)

class DownloadView(discord.ui.View):
    def __init__(self, ctx: commands.Context, urls: list, details: dict, index: int, texts: list):
        super().__init__(timeout=None)
        for x in range(len(urls)):
            self.add_item(ButtonDownload(ctx, urls[x], x, details, index, texts[x]))