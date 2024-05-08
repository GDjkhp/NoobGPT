import discord
from discord.ext import commands
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
import re
from urllib import parse as p
import json
import asyncio

client, client0 = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
desc, ep, animetype, released, genre = 2, 3, 5, 6, 7
pagelimit = 12
gogoanime = "https://anitaku.so"

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def get_domain():
    global gogoanime
    data = read_json_file("./res/mandatory_settings_and_splashes.json")
    gogoanime = data["gogoanime"]

async def Gogoanime(ctx: commands.Context, arg: str):
    await asyncio.to_thread(get_domain)
    if arg: msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    else: msg = await ctx.reply("Imagine something that doesn't exist. Must be sad. You are sad. You don't belong here.\nLet's all love lain.")
    try: result = resultsAnime(searchAnime(arg if arg else "serial experiments lain"))
    except: return await msg.edit(content="Error! Domain changed most likely.")
    try: await msg.edit(content=None, embed=buildSearch(arg, result, 0), view = MyView4(ctx, arg, result, 0))
    except Exception as e: return await msg.edit(content=f"**No results found**")

def buildAnime(details: list) -> discord.Embed:
    embed = discord.Embed(title=details[title], description=details[desc], color=0x00ff00)
    valid_url = p.quote(details[poster], safe=":/")
    embed.set_image(url = valid_url)
    embed.add_field(name="Type", value=details[animetype])
    embed.add_field(name="Episodes", value=details[ep])
    embed.add_field(name="Released", value=details[released])
    embed.add_field(name="Genre", value=details[genre])
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed

# legacy code
def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url="https://gdjkhp.github.io/img/logo.png")
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i][title]}`", value=f"{result[i][url]}")
        i += 1
    return embed
def searchAnime(q: str):
    return q.replace(" ", "-")
def resultsAnime(data: str) -> list:
    results = []
    page = 1
    while True:
        req = client.get(f"{gogoanime}/search.html?keyword={data}&page={page}")
        soup = BS(req, "lxml")
        items = soup.find("ul", {"class": "items"}).findAll("li")
        if len(items) == 0: break
        img = [items[i].find("img")["src"] for i in range(len(items))]
        urls = [items[i].find("a")["href"] for i in range(len(items))]
        title = [items[i].find("a")["title"] for i in range(len(items))]
        ids = [items[i].find("a")["title"] for i in range(len(items))]
        mov_or_tv = ["TV" for i in range(len(items))]
        results.extend([list(sublist) for sublist in zip(title, urls, ids, mov_or_tv, img)])
        page += 1
    return results
def doodstream(url):
    domain = re.findall("""([^"']*)\/e""", url)[0]
    req = client.get(url).text
    pass_md = re.findall(r"/pass_md5/[^']*", req)[0]
    token = pass_md.split("/")[-1]
    client0.set_headers(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Referer": f"{url}",
            "Accept-Language": "en-GB,en;q=0.5",
        }
    )
    drylink = client0.get(f"{domain}{pass_md}").text
    streamlink = f"{drylink}zUEJeL3mUN?token={token}"
    print(streamlink)
    return streamlink
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

# search
class MyView4(discord.ui.View):
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
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i][title]}", value=i, description=f"{result[i][url]}")
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        req = client.get(f"{gogoanime}{self.result[int(self.values[0])][url]}")
        soup = BS(req, "lxml")

        episodes: int = soup.find("ul", {"id": "episode_page"}).find_all("a")[-1]["ep_end"]
        types = soup.find_all("p", {"class": "type"})
        desc: str = types[1].get_text().replace("Plot Summary:", "")
        animetype: str = types[0].get_text().split(": ")[1]
        genre: str = types[2].get_text().split(": ")[1]
        released: str = types[3].get_text().split(": ")[1]
        details = [self.result[int(self.values[0])][title], self.result[int(self.values[0])][url], desc, episodes, 
                   self.result[int(self.values[0])][poster], animetype, released, genre]

        embed = buildAnime(details)
        await interaction.message.edit(content=None, embed = embed, view = MyView5(self.ctx, details, 0))

# legacy code
class ButtonSelect4(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result, self.ctx = result, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        req = client.get(f"{gogoanime}{self.result[url]}")
        soup = BS(req, "lxml")

        episodes: int = soup.find("ul", {"id": "episode_page"}).find_all("a")[-1]["ep_end"]
        types = soup.find_all("p", {"class": "type"})
        desc: str = types[1].get_text().replace("Plot Summary:", "")
        animetype: str = types[0].get_text().split(": ")[1]
        genre: str = types[2].get_text().split(": ")[1]
        released: str = types[3].get_text().split(": ")[1]
        details = [self.result[title], self.result[url], desc, episodes, self.result[poster], animetype, released, genre]

        embed = buildAnime(details)
        await interaction.message.edit(embed = embed, view = MyView5(self.ctx, details, 0))

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
        await interaction.message.edit(view = MyView4(self.ctx, self.arg, self.result, self.index))

# episode
class MyView5(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, int(details[ep])
        while i < int(details[ep]):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect5(ctx, i + 1, details[url], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪"))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == int(details[ep]):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️"))
            max_page = get_max_page(int(details[ep]))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonSelect5(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, sUrl: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.index = index
        self.sUrl = sUrl
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        url = self.sUrl.split("/")[-1]
        request = client.get(f"{gogoanime}/{url}-episode-{self.index}")
        soup = BS(request, "lxml")
        video = soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        await interaction.followup.send(f"[{url}-episode-{self.index}]({video})", ephemeral=True)
        # url0 = doodstream(
        #     soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        # )
        # await interaction.followup.send(f"{url}-episode-{self.index}: {url0}")

class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx = details, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.response.defer()
        embed = buildAnime(self.details)
        await interaction.message.edit(embed = embed, view = MyView5(self.ctx, self.details, self.index))

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