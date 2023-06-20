import re
import discord
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
from urllib import parse as p
import base64
from Crypto.Cipher import AES
import hashlib
import json

client, client0 = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
pagelimit = 12

async def Actvid(msg: discord.Message, arg: str):
    result = results(searchQuery(arg))
    embed = buildSearch(arg, result, 0)
    await msg.edit(content=None, embed = embed, view = MyView(result, arg, 0))

# embed builders
def detail(result) -> list:
    req = client.get(f"https://www.actvid.com{result[1]}")
    soup = BS(req, "lxml")
    desc = soup.find("div", {"class": "description"}).get_text()
    items = soup.find("div", {"class": "elements"}).find_all("div", {"class": "row-line"})
    details = []
    for item in items:
        detail = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", item.get_text().split(": ")[1])
        details.append(detail)
    return [desc] + details # [desc, rel, genre, casts, dur, country, prod]
def detailed(embed: discord.Embed, details: list):
    embed.add_field(name="Released", value=details[1])
    embed.add_field(name="Duration", value=details[4])
    embed.add_field(name="Country", value=details[5])
    embed.add_field(name="Genre", value=details[2])
    embed.add_field(name="Casts", value=details[3])
    embed.add_field(name="Production", value=details[6])
def buildMovie(url, result) -> discord.Embed():
    details = detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.add_field(name="Stream Link:", value=url)
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildSeasons(season_ids, result) -> discord.Embed():
    details = detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.add_field(name="Seasons", value=len(season_ids))
    return embed
def buildEpisodes(episodes, season, result) -> discord.Embed():
    embed = discord.Embed(title=f"{result[title]}", description=f"Season {season}", color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    details = detail(result)
    detailed(embed, details)
    embed.add_field(name="Episodes", value=len(episodes))
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildSearch(arg: str, result: list, index: int) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    # embed.set_thumbnail(url = bot.user.avatar)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] {result[i][title]}", value=f"{result[i][url]}")
        i += 1
    return embed

# actvid
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def parse(txt: str) -> str:
    return re.sub(r"\W+", "-", txt.lower())
def searchQuery(q) -> str:
    return client.get(f"https://www.actvid.com/search/{parse(q)}").text
def results(html: str) -> list:
    soup = BS(html, "lxml")
    img = [i["data-src"] for i in soup.select(".film-poster-img")]
    urls = [i["href"] for i in soup.select(".film-poster-ahref")]
    mov_or_tv = [
        "MOVIE" if i["href"].__contains__("/movie/") else "TV"
        for i in soup.select(".film-poster-ahref")
    ]
    title = [
        re.sub(
            pattern="full|/tv/|/movie/|hd|watch|[0-9]{2,}",
            repl="",
            string=" ".join(i.split("-")),
        )
        for i in urls
    ]
    ids = [i.split("-")[-1] for i in urls]
    return [list(sublist) for sublist in zip(title, urls, ids, mov_or_tv, img)]

# search
class MyView(discord.ui.View):
    def __init__(self, result: list, arg: str, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(result)
        while i < len(result):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect(i + 1, result[i], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        row = 4
        if index - pagelimit > -1:
            self.add_item(ButtonNextSearch(arg, result, 0, row, "<<"))
            self.add_item(ButtonNextSearch(arg, result, index - pagelimit, row, "<"))
        if not last_index == len(result):
            self.add_item(ButtonNextSearch(arg, result, last_index, row, ">"))
            max_page = get_max_page(len(result))
            self.add_item(ButtonNextSearch(arg, result, max_page, row, ">>"))

class ButtonSelect(discord.ui.Button):
    def __init__(self, index: int, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result = result
    
    async def callback(self, interaction: discord.Interaction):
        if self.result[mv_tv] == "TV":
            r = client.get(f"https://www.actvid.com/ajax/v2/tv/seasons/{self.result[aid]}")
            season_ids = [i["data-id"] for i in BS(r, "lxml").select(".dropdown-item")]
            embed = buildSeasons(season_ids, self.result)
            await interaction.response.edit_message(embed = embed, view = MyView2(self.result, season_ids, 0))

        else:
            sid = server_id(self.result[aid])
            iframe_url, tv_id = get_link(sid)
            iframe_link, iframe_id = rabbit_id(iframe_url)

            await interaction.response.defer()
            try:
                url = cdn_url(iframe_link, iframe_id)
                embed = buildMovie(url, self.result)
                await interaction.message.edit(embed=embed, view=None)
            except: await interaction.message.edit(content="**UnicodeDecodeError: The Current Key is not correct. Wake up <@729554186777133088> :(**",
                                                   view=None)
            
class ButtonNextSearch(discord.ui.Button):
    def __init__(self, arg: str, result: list, index: int, row: int, l: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.index, self.arg = result, index, arg

    async def callback(self, interaction: discord.Interaction):
        embed = buildSearch(self.arg, self.result, self.index)
        await interaction.response.edit_message(embed = embed, view = MyView(self.result, self.arg, self.index))

# season
class MyView2(discord.ui.View):
    def __init__(self, result: list, season_ids: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(season_ids)
        while i < len(season_ids):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect2(i + 1, season_ids[i], result, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        row = 4
        if index - pagelimit > -1:
            self.add_item(ButtonNextSeason(result, season_ids, 0, row, "<<"))
            self.add_item(ButtonNextSeason(result, season_ids, index - pagelimit, row, "<"))
        if not last_index == len(season_ids):
            self.add_item(ButtonNextSeason(result, season_ids, last_index, row, ">"))
            max_page = get_max_page(len(season_ids))
            self.add_item(ButtonNextSeason(result, season_ids, max_page, row, ">>"))

class ButtonSelect2(discord.ui.Button):
    def __init__(self, index: int, season_id: str, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result, self.season_id, self.index = result, season_id, index
    
    async def callback(self, interaction: discord.Interaction):
        z = f"https://www.actvid.com/ajax/v2/season/episodes/{self.season_id}"
        rf = client.get(z)
        episodes = [i["data-id"] for i in BS(rf, "lxml").select(".nav-item > a")]
        embed = buildEpisodes(episodes, self.index, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView3(self.season_id, episodes, self.result, 0, self.index))

class ButtonNextSeason(discord.ui.Button):
    def __init__(self, result: list, season_ids: list, index: int, row: int, l: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.season_ids, self.index = result, season_ids, index
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildSeasons(self.season_ids, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView2(self.result, self.season_ids, self.index))

# episode
class MyView3(discord.ui.View):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(episodes)
        while i < len(episodes):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect3(i + 1, season_id, episodes[i], season, result[title], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        row = 4
        if index - pagelimit > -1:
            self.add_item(ButtonNextEp(season_id, episodes, result, 0, season, row, "<<"))
            self.add_item(ButtonNextEp(season_id, episodes, result, index - pagelimit, season, row, "<"))
        if not last_index == len(episodes):
            self.add_item(ButtonNextEp(season_id, episodes, result, last_index, season, row, ">"))
            max_page = get_max_page(len(episodes))
            self.add_item(ButtonNextEp(season_id, episodes, result, max_page, season, row, ">>"))

class ButtonNextEp(discord.ui.Button):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int, row: int, l: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, row=row)
        self.season_id, self.episodes, self.result, self.index, self.season = season_id, episodes, result, index, season
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildEpisodes(self.episodes, self.season, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView3(self.season_id, self.episodes, self.result, self.index, self.season))

class ButtonSelect3(discord.ui.Button):
    def __init__(self, index: int, season_id: str, episode: str, season: int, title: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.episode, self.season_id, self.season, self.title, self.index = episode, season_id, season, title, index
    
    async def callback(self, interaction: discord.Interaction):
        sid = ep_server_id(self.episode)
        iframe_url, tv_id = get_link(sid)
        iframe_link, iframe_id = rabbit_id(iframe_url)
        await interaction.response.defer()
        try:
            url = cdn_url(iframe_link, iframe_id)
            await interaction.followup.send(f"{self.title} [S{self.season}E{self.index}]: {url}")
        except: await interaction.followup.send("**UnicodeDecodeError: The Current Key is not correct. Wake up <@729554186777133088> :(**")

# actvid utils
def server_id(mov_id: str) -> str:
    req = client.get(f"https://www.actvid.com/ajax/movie/episodes/{mov_id}")
    soup = BS(req, "lxml")
    return [i["data-linkid"] for i in soup.select(".nav-item > a")][0]        
def ep_server_id(ep_id: str) -> str:
    req = client.get(
        f"https://www.actvid.com/ajax/v2/episode/servers/{ep_id}/#servers-list"
    )
    soup = BS(req, "lxml")
    return [i["data-id"] for i in soup.select(".nav-item > a")][0]
def get_link(thing_id: str) -> tuple:
    req = client.get(f"https://www.actvid.com/ajax/get_link/{thing_id}").json()[
        "link"
    ]
    print(req)
    return req, rabbit_id(req)
def rabbit_id(url: str) -> tuple:
    parts = p.urlparse(url, allow_fragments=True, scheme="/").path.split("/")
    return (
        re.findall(r"(https:\/\/.*\/embed-4)", url)[0].replace(
            "embed-4", "ajax/embed-4/"
        ),
        parts[-1],
    )
def cdn_url(final_link: str, rabb_id: str) -> str:
    client0.set_headers({"X-Requested-With": "XMLHttpRequest"})
    data = client0.get(f"{final_link}getSources?id={rabb_id}").json()
    n = json.loads(decrypt(data["sources"], gh_key()))
    return n[0]["file"]
def decrypt(data, key):
    k = get_key(base64.b64decode(data)[8:16], key)
    dec_key = k[:32]
    iv = k[32:]
    p = AES.new(dec_key, AES.MODE_CBC, iv=iv).decrypt(base64.b64decode(data)[16:])
    return unpad(p).decode()
def md5(data):
    return hashlib.md5(data).digest()
def gh_key():
    u = client.get(
        "https://raw.githubusercontent.com/enimax-anime/key/e4/key.txt"
    ).text
    return bytes(u, "utf-8")
def get_key(salt, key):
    x = md5(key + salt)
    currentkey = x
    while len(currentkey) < 48:
        x = md5(x + key + salt)
        currentkey += x
    return currentkey
def unpad(s):
    return s[: -ord(s[len(s) - 1 :])]
