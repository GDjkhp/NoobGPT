import discord
from discord.ext import commands
import re
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
import os
from dotenv import load_dotenv
from typing import List
from flask import Flask
from threading import Thread 

from urllib import parse as p
import base64
from Crypto.Cipher import AES
import hashlib
import json

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents = intents)
client, client0 = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
pagelimit = 12
actvid = "https://www.actvid.com"
gogoanime = "https://gogoanime.cl"
base_url = ""

# open server
app = Flask('') 
@app.route('/')
def main(): 
    return "Bot by GDjkhp" 
def run(): 
    app.run(host="0.0.0.0", port=8000) 
def keep_alive(): 
    server = Thread(target=run) 
    server.start()
keep_alive()

@bot.event
async def on_ready():
    print(":)")
    await bot.change_presence(status=discord.Status.dnd)

class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        emby = discord.Embed(title="NoobGPT Official Website", description="https://gdjkhp.github.io/NoobGPT/", color=0x00ff00)
        await destination.send(embed=emby)

bot.help_command = MyNewHelp()

# embed builders
def detail(result) -> list:
    req = client.get(f"https://www.actvid.com{result[1]}")
    soup = BS(req, "lxml")
    desc = soup.find("div", {"class": "description"}).get_text()
    items = soup.find("div", {"class": "elements"}).find_all("div", {"class": "row-line"})
    rel = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[0].get_text().split(": ")[1])
    genre = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[1].get_text().split(": ")[1])
    casts = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[2].get_text().split(": ")[1])
    dur = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[3].get_text().split(": ")[1])
    country = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[4].get_text().split(": ")[1])
    prod = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", items[5].get_text().split(": ")[1])
    return [desc, rel, genre, casts, dur, country, prod]
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
def buildSearch(arg: str, result: list, index: int) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: {arg}", description=f"{len(result)} found.", color=0x00ff00)
    embed.set_thumbnail(url = bot.user.avatar)
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

@bot.command()
async def search(ctx: commands.Context, *, arg):
    await ctx.reply(f"Searching \"{arg}\". Please wait...")
    result = results(searchQuery(arg))
    embed = buildSearch(arg, result, 0)
    await ctx.reply(embed = embed, view = MyView(result, arg, 0))

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
                await interaction.followup.send(embed=embed)
            except: await interaction.followup.send("**UnicodeDecodeError: The Current Key is not correct, Wake up <@729554186777133088> :(**")
            
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
        except: await interaction.followup.send("**UnicodeDecodeError: The Current Key is not correct, Wake up <@729554186777133088> :(**")

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
    source = data["sources"]
    link = f"{source}"
    if link.endswith("==") or link.endswith("="):
        n = json.loads(decrypt(data["sources"], gh_key()))
        return n[0]["file"]
    return source[0]["file"]
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

# gogoanime
@bot.command()
async def anime(ctx: commands.Context, *, arg):
    await ctx.reply(f"Searching \"{arg}\". Please wait...")
    result = resultsAnime(searchAnime(arg))
    embed = buildSearch(arg, result, 0)
    await ctx.reply(embed = embed, view = MyView4(arg, result, 0))

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

# search
class MyView4(discord.ui.View):
    def __init__(self, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(result)
        while i < len(result):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect4(i + 1, result[i], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        row = 4
        if index - pagelimit > -1:
            self.add_item(nextPage(arg, result, 0, row, "<<"))
            self.add_item(nextPage(arg, result, index - pagelimit, row, "<"))
        if not last_index == len(result):
            self.add_item(nextPage(arg, result, last_index, row, ">"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(arg, result, max_page, row, ">>"))

desc, ep, animetype, released, genre = 2, 3, 5, 6, 7
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
        super().__init__(label=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.index, self.arg = result, index, arg
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildSearch(self.arg, self.result, self.index)
        await interaction.response.edit_message(embed = embed, view = MyView4(self.arg, self.result, self.index))

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
        row = 4
        if index - pagelimit > -1:
            self.add_item(nextPageEP(details, 0, row, "<<"))
            self.add_item(nextPageEP(details, index - pagelimit, row, "<"))
        if not last_index == int(details[ep]):
            self.add_item(nextPageEP(details, last_index, row, ">"))
            max_page = get_max_page(int(details[ep]))
            self.add_item(nextPageEP(details, max_page, row, ">>"))

class ButtonSelect5(discord.ui.Button):
    def __init__(self, index: int, sUrl: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.index = index
        self.sUrl = sUrl
    
    async def callback(self, interaction: discord.Interaction):
        url = self.sUrl.split("/")[-1]
        request = client.get(f"{gogoanime}/{url}-episode-{self.index}")
        soup = BS(request, "lxml")
        # url = doodstream(
        #     soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        # )
        video = soup.find("li", {"class": "doodstream"}).find("a")["data-video"]
        await interaction.response.send_message(f"{url}-episode-{self.index}: {video}")

class nextPageEP(discord.ui.Button):
    def __init__(self, details: list, index: int, row: int, l: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index = details, index
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildAnime(self.details)
        await interaction.response.edit_message(embed = embed, view = MyView5(self.details, self.index))

# Defines a custom button that contains the logic of the game.
# The ['TicTacToe'] bit is for type hinting purposes to tell your IDE or linter
# what the type of `self.view` is. It is not required.
class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        # A label is required, but we don't need one so a zero-width space is used
        # The row parameter tells the View which row to place the button under.
        # A View can only contain up to 5 rows -- each row can only have 5 buttons.
        # Since a Tic Tac Toe grid is 3x3 that means we have 3 rows and 3 columns.
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = "It is now O's turn"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = "It is now X's turn"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = 'X won!'
            elif winner == view.O:
                content = 'O won!'
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)

# This is our actual board View
class TicTacToe(discord.ui.View):
    # This tells the IDE or linter that all our children will be TicTacToeButtons
    # This is not required
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self):
        super().__init__()
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        # Our board is made up of 3 by 3 TicTacToeButtons
        # The TicTacToeButton maintains the callbacks and helps steer
        # the actual game.
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

@bot.command()
async def tic(ctx: commands.Context):
    """Starts a tic-tac-toe game with yourself."""
    await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

# ytdlp
import yt_dlp
import glob
@bot.command()
async def ytdlp(ctx: commands.Context, arg1, arg2=None):
    formats = ['mp3']
    if arg2 and not arg1 in formats: return await ctx.reply(f"Unsupported format :(")
    elif not arg2: arg2, arg1 = arg1, None
    ydl_opts = get_ydl_opts(arg1)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(arg2, download=False)
        filename = ydl.prepare_filename(info_dict) if not arg1 else f"{os.path.splitext(ydl.prepare_filename(info_dict))[0]}.{arg1}"
        await ctx.reply(f"Preparing `{filename}`\nLet me cook.")
        error_code = ydl.download(arg2)
        if error_code: 
            print(f"yt-dlp issue: {error_code}")
            await ctx.reply(f"Error {error_code}: An error occured while cooking `{filename}`")
        else: 
            try: await ctx.reply(file=discord.File(filename))
            except discord.errors.HTTPException as error: 
                print(error)
                if error.code == 40005:
                    await ctx.reply(f"Error {error.code}: An error occured while cooking `{filename}`\nFile too large!")
                else: await ctx.reply(f"Error {error.code}: An error occured while cooking `{filename}`")
        os.remove(filename)

def get_ydl_opts(arg):
    if arg == 'mp3':
        return {
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
    elif arg == 'mp4':
        return {
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        }
    else:
        return None


# bard
@bot.command()
async def bard(ctx: commands.Context, *, arg):
    os.environ['_BARD_API_KEY'] = os.getenv("BARD")
    response = Bard(timeout=60).get_answer(arg)
    await ctx.reply(response['content'][:2000])
    if response['links']:
        for img in range(5): # hard limit
            await ctx.reply(response['links'][img])

import os
import string
import random
import json
import re
import requests

SESSION_HEADERS = {
    "Host": "bard.google.com",
    "X-Same-Domain": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Origin": "https://bard.google.com",
    "Referer": "https://bard.google.com/",
}

class Bard:
    """
    Bard class for interacting with the Bard API.
    """

    def __init__(
        self,
        token: str = None,
        timeout: int = 20,
        proxies: dict = None,
        session: requests.Session = None,
        language: str = None,
    ):
        """
        Initialize the Bard instance.

        Args:
            token (str): Bard API token.
            timeout (int): Request timeout in seconds.
            proxies (dict): Proxy configuration for requests.
            session (requests.Session): Requests session object.
            language (str): Language code for translation (e.g., "en", "ko", "ja").
        """
        self.token = token or os.getenv("_BARD_API_KEY")
        self.proxies = proxies
        self.timeout = timeout
        self._reqid = int("".join(random.choices(string.digits, k=4)))
        self.conversation_id = ""
        self.response_id = ""
        self.choice_id = ""
        # Set session
        if session is None:
            self.session = requests.Session()
            self.session.headers = SESSION_HEADERS
            self.session.cookies.set("__Secure-1PSID", self.token)
        else:
            self.session = session
        self.SNlM0e = self._get_snim0e()
        self.language = language or os.getenv("_BARD_API_LANG")

    def get_answer(self, input_text: str) -> dict:
        """
        Get an answer from the Bard API for the given input text.

        Example:
        >>> token = 'xxxxxxxxxx'
        >>> bard = Bard(token=token)
        >>> response = bard.get_answer("나와 내 동년배들이 좋아하는 뉴진스에 대해서 알려줘")
        >>> print(response['content'])

        Args:
            input_text (str): Input text for the query.

        Returns:
            dict: Answer from the Bard API in the following format:
                {
                    "content": str,
                    "conversation_id": str,
                    "response_id": str,
                    "factualityQueries": list,
                    "textQuery": str,
                    "choices": list,
                    "links": list
                    "imgaes": set
                }
        """
        params = {
            "bl": "boq_assistant-bard-web-server_20230419.00_p1",
            "_reqid": str(self._reqid),
            "rt": "c",
        }

        # Make post data structure and insert prompt
        input_text_struct = [
            [input_text],
            None,
            [self.conversation_id, self.response_id, self.choice_id],
        ]
        data = {
            "f.req": json.dumps([None, json.dumps(input_text_struct)]),
            "at": self.SNlM0e,
        }

        # Get response
        resp = self.session.post(
            "https://bard.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate",
            params=params,
            data=data,
            timeout=self.timeout,
            proxies=self.proxies,
        )

        # Post-processing of response
        resp_dict = json.loads(resp.content.splitlines()[3])[0][2]

        if not resp_dict:
            return {"content": f"Response Error: {resp.content}."}
        resp_json = json.loads(resp_dict)

        # Gather image links
        images = set()
        if len(resp_json) >= 3:
            if len(resp_json[4][0]) >= 4 and resp_json[4][0][4] is not None:
                for img in resp_json[4][0][4]:
                    images.add(img[0][0][0])
        parsed_answer = json.loads(resp_dict)

        # Returnd dictionary object
        bard_answer = {
            "content": parsed_answer[0][0],
            "conversation_id": parsed_answer[1][0],
            "response_id": parsed_answer[1][1],
            "factualityQueries": parsed_answer[3],
            "textQuery": parsed_answer[2][0] if parsed_answer[2] else "",
            "choices": [{"id": x[0], "content": x[1]} for x in parsed_answer[4]],
            "links": self._extract_links(parsed_answer[4]),
            "images": images,
        }
        self.conversation_id, self.response_id, self.choice_id = (
            bard_answer["conversation_id"],
            bard_answer["response_id"],
            bard_answer["choices"][0]["id"],
        )
        self._reqid += 100000

        return bard_answer

    def _get_snim0e(self) -> str:
        """
        Get the SNlM0e value from the Bard API response.

        Returns:
            str: SNlM0e value.
        Raises:
            Exception: If the __Secure-1PSID value is invalid or SNlM0e value is not found in the response.
        """
        if not self.token or self.token[-1] != ".":
            raise Exception(
                "__Secure-1PSID value must end with a single dot. Enter correct __Secure-1PSID value."
            )
        resp = self.session.get(
            "https://bard.google.com/", timeout=self.timeout, proxies=self.proxies
        )
        if resp.status_code != 200:
            raise Exception(
                f"Response code not 200. Response Status is {resp.status_code}"
            )
        snim0e = re.search(r"SNlM0e\":\"(.*?)\"", resp.text)
        if not snim0e:
            raise Exception(
                "SNlM0e value not found in response. Check __Secure-1PSID value."
            )
        return snim0e.group(1)

    def _extract_links(self, data: list) -> list:
        """
        Extract links from the given data.

        Args:
            data: Data to extract links from.

        Returns:
            list: Extracted links.
        """
        links = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, list):
                    links.extend(self._extract_links(item))
                elif (
                    isinstance(item, str)
                    and item.startswith("http")
                    and "favicon" not in item
                ):
                    links.append(item)
        return links

    # def auth(self): #Idea Contribution
    #     url = 'https://bard.google.com'
    #     driver_path = "/path/to/chromedriver"
    #     options = uc.ChromeOptions()
    #     options.add_argument("--ignore-certificate-error")
    #     options.add_argument("--ignore-ssl-errors")
    #     options.user_data_dir = "path_to _user-data-dir"
    #     driver = uc.Chrome(options=options)
    #     driver.get(url)
    #     cookies = driver.get_cookies()
    #     # Find the __Secure-1PSID cookie
    #     for cookie in cookies:
    #         if cookie['name'] == '__Secure-1PSID':
    #             print("__Secure-1PSID cookie:")
    #             print(cookie['value'])
    #             os.environ['_BARD_API_KEY']=cookie['value']
    #             break
    #     else:
    #         print("No __Secure-1PSID cookie found")
    #     driver.quit()

# :|
from pygelbooru import Gelbooru

@bot.command()
async def r34(ctx: commands.Context, *, arg):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    tags = re.split(r'\s*,\s*', arg)
    results = await Gelbooru(api='https://api.rule34.xxx/').search_posts(tags=tags)
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = await BuildEmbed(tags, results, 0, False), view = ImageView(tags, results, 0, False))
@bot.command()
async def gel(ctx: commands.Context, *, arg):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    tags = re.split(r'\s*,\s*', arg)
    results = await Gelbooru().search_posts(tags=tags)
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = await BuildEmbed(tags, results, 0, False), view = ImageView(tags, results, 0, False))
@bot.command()
async def safe(ctx: commands.Context, *, arg):
    tags = re.split(r'\s*,\s*', arg)
    results = await Gelbooru(api='https://safebooru.org/').search_posts(tags=tags)
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = await BuildEmbed(tags, results, 0, True), view = ImageView(tags, results, 0, True))

async def BuildEmbed(tags: list, results, index: int, safe: bool) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{tags}`", description=f"{index+1}/{len(results)} found.", color=0x00ff00)
    # if safe and not await Gelbooru(api='https://safebooru.org/').is_deleted(results[index].hash): 
    #     embed.add_field(name="This post was deleted.", value=results[index].hash)
    #     return embed
    embed.add_field(name="Tags", value=f"`{results[index].tags}`", inline=False)
    embed.add_field(name="Source", value=results[index].source, inline=False)
    if results[index].file_url.endswith(".mp4"): embed.add_field(name="Video link:", value=results[index].file_url)
    else: embed.set_image(url = results[index].file_url)
    return embed

class ImageView(discord.ui.View):
    def __init__(self, tags, results, index, safe):
        super().__init__(timeout=None)
        if not index == 0: self.add_item(ButtonAction(tags, safe, results, index - 1, "<"))
        if index + 1 < len(results): self.add_item(ButtonAction(tags, safe, results, index + 1, ">"))

class ButtonAction(discord.ui.Button):
    def __init__(self, tags, safe, results, index, l):
        super().__init__(label=l, style=discord.ButtonStyle.success)
        self.results, self.index, self.tags, self.safe = results, index, tags, safe
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed = await BuildEmbed(self.tags, self.results, self.index, self.safe), \
                                                view = ImageView(self.tags, self.results, self.index, self.safe))

bot.run(os.getenv("TOKEN"))