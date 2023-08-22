import discord
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
import re
from urllib import parse as p

client, client0 = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
desc, ep, animetype, released, genre = 2, 3, 5, 6, 7
pagelimit = 12
gogoanime = "https://gogoanimehd.io"

async def Gogoanime(msg: discord.Message, arg: str):
    try: result = resultsAnime(searchAnime(arg))
    except: return await msg.edit(content="Error! Domain changed most likely.")
    embed = buildSearch(arg, result, 0)
    await msg.edit(content=f"Search results: `{arg}`", view = MyView4(arg, result, 0))

def buildAnime(details: list) -> discord.Embed():
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
def buildSearch(arg: str, result: list, index: int) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    # embed.set_thumbnail(url = bot.user.avatar)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] {result[i][title]}", value=f"{result[i][url]}")
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
    def __init__(self, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(arg, result, 0, 3, "⏪"))
            self.add_item(nextPage(arg, result, index - pagelimit, 3, "◀️"))
        if not last_index == len(result):
            self.add_item(nextPage(arg, result, last_index, 3, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(arg, result, max_page, 3, "⏩"))

class SelectChoice(discord.ui.Select):
    def __init__(self, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result = index, result
        while i < len(result): 
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i][title]}", value=i, description=f"{result[i][url]}")
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
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
        await interaction.response.edit_message(content=None, embed = embed, view = MyView5(details, 0))

# legacy code
class ButtonSelect4(discord.ui.Button):
    def __init__(self, index: int, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result = result
    
    async def callback(self, interaction: discord.Interaction):
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
        await interaction.response.edit_message(embed = embed, view = MyView5(details, 0))

class nextPage(discord.ui.Button):
    def __init__(self, arg: str, result: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.index, self.arg = result, index, arg
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view = MyView4(self.arg, self.result, self.index))

# episode
class MyView5(discord.ui.View):
    def __init__(self, details: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, int(details[ep])
        while i < int(details[ep]):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect5(i + 1, details[url], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(details, 0, 3, "⏪"))
            self.add_item(nextPageEP(details, index - pagelimit, 3, "◀️"))
        if not last_index == int(details[ep]):
            self.add_item(nextPageEP(details, last_index, 3, "▶️"))
            max_page = get_max_page(int(details[ep]))
            self.add_item(nextPageEP(details, max_page, 3, "⏩"))

class ButtonSelect5(discord.ui.Button):
    def __init__(self, index: int, sUrl: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.index = index
        self.sUrl = sUrl
    
    async def callback(self, interaction: discord.Interaction):
        url = self.sUrl.split("/")[-1]
        request = client.get(f"{gogoanime}/{url}-episode-{self.index}")
        soup = BS(request, "lxml")
        video = soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        await interaction.response.send_message(f"{url}-episode-{self.index}: {video}")
        # url0 = doodstream(
        #     soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        # )
        # await interaction.response.send_message(f"{url}-episode-{self.index}: {url0}")

class nextPageEP(discord.ui.Button):
    def __init__(self, details: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index = details, index
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildAnime(self.details)
        await interaction.response.edit_message(embed = embed, view = MyView5(self.details, self.index))
