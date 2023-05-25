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
pagelimit = 3
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
    embed = discord.Embed(title=result[title], description=details[0])
    embed.set_image(url = result[poster])
    detailed(embed, details)
    embed.add_field(name="Stream Link:", value=url)
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildSeasons(season_ids, result) -> discord.Embed():
    details = detail(result)
    embed = discord.Embed(title=result[title], description=details[0])
    embed.set_image(url = result[poster])
    detailed(embed, details)
    embed.add_field(name="Seasons", value=len(season_ids))
    return embed
def buildEpisodes(episodes, season, result) -> discord.Embed():
    embed = discord.Embed(title=f"{result[title]}", description=f"Season {season}")
    embed.set_image(url = result[poster])
    details = detail(result)
    detailed(embed, details)
    embed.add_field(name="Episodes", value=len(episodes))
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildAnime(details: list) -> discord.Embed():
    embed = discord.Embed(title=details[title], description=details[desc], color=0x00ff00)
    embed.set_image(url = details[poster])
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
async def search(ctx, *, arg):
    await ctx.reply(f"Searching \"{arg}\". Please wait...")
    result = results(searchQuery(arg))
    embed = buildSearch(arg, result, 0)
    await ctx.reply(embed = embed, view = MyView(result, arg, 0))

# search
class MyView(discord.ui.View):
    def __init__(self, result: list, arg: str, index: int):
        super().__init__(timeout=None)
        i = index
        while i < len(result):
            if (i < index+pagelimit): self.add_item(ButtonSelect(i + 1, result[i]))
            if (i == index+pagelimit): self.add_item(ButtonNextSearch(arg, result, i))
            i += 1

class ButtonSelect(discord.ui.Button):
    def __init__(self, index: int, result: list):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
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
    def __init__(self, arg: str, result: list, index: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.result = result
        self.index = index
        self.arg = arg

    async def callback(self, interaction: discord.Interaction):
        embed = buildSearch(self.arg, self.result, self.index)
        await interaction.response.edit_message(embed = embed, view = MyView(self.result, self.arg, self.index))

# season
class MyView2(discord.ui.View):
    def __init__(self, result: list, season_ids: list, index: int):
        super().__init__(timeout=None)
        i = index
        while i < len(season_ids):
            if (i < index+pagelimit): self.add_item(ButtonSelect2(i + 1, season_ids[i], result))
            if (i == index+pagelimit): self.add_item(ButtonNextSeason(result, season_ids, i))
            i += 1

class ButtonSelect2(discord.ui.Button):
    def __init__(self, index: int, season_id: str, result: list):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
        self.result = result
        self.season_id = season_id
        self.index = index
    
    async def callback(self, interaction: discord.Interaction):
        z = f"https://www.actvid.com/ajax/v2/season/episodes/{self.season_id}"
        rf = client.get(z)
        episodes = [i["data-id"] for i in BS(rf, "lxml").select(".nav-item > a")]
        embed = buildEpisodes(episodes, self.index, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView3(self.season_id, episodes, self.result, 0, self.index))

class ButtonNextSeason(discord.ui.Button):
    def __init__(self, result: list, season_ids: list, index: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.result, self.season_ids, self.index = result, season_ids, index
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildSeasons(self.season_ids, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView2(self.result, self.season_ids, self.index))

# episode
class MyView3(discord.ui.View):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int):
        super().__init__(timeout=None)
        i = index
        while i < len(episodes):
            if (i < index+pagelimit): self.add_item(ButtonSelect3(i + 1, season_id, episodes[i], season, result[title]))
            if (i == index+pagelimit): self.add_item(ButtonNextEp(season_id, episodes, result, i, season))
            i += 1

class ButtonNextEp(discord.ui.Button):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.season_id, self.episodes, self.result, self.index, self.season = season_id, episodes, result, index, season
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildEpisodes(self.episodes, self.season, self.result)
        await interaction.response.edit_message(embed = embed, view = MyView3(self.season_id, self.episodes, self.result, self.index, self.season))

class ButtonSelect3(discord.ui.Button):
    def __init__(self, index: int, season_id: str, episode: str, season: int, title: str):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
        self.episode = episode
        self.season_id = season_id
        self.season = season
        self.title = title
        self.index = index
    
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
async def anime(ctx, *, arg):
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
    client.set_headers(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Referer": f"{url}",
            "Accept-Language": "en-GB,en;q=0.5",
        }
    )
    drylink = client.get(f"{domain}{pass_md}").text
    streamlink = f"{drylink}zUEJeL3mUN?token={token}"
    print(streamlink)
    return streamlink

# search
class MyView4(discord.ui.View):
    def __init__(self, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        i = index
        while i < len(result):
            if (i < index+pagelimit): self.add_item(ButtonSelect4(i + 1, result[i]))
            if (i == index+pagelimit): self.add_item(nextPage(arg, result, i))
            i += 1
desc, ep, animetype, released, genre = 2, 3, 5, 6, 7
class ButtonSelect4(discord.ui.Button):
    def __init__(self, index: int, result: list):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
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
    def __init__(self, arg: str, result: list, index: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.result = result
        self.index = index
        self.arg = arg
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildSearch(self.arg, self.result, self.index)
        await interaction.response.edit_message(embed = embed, view = MyView4(self.arg, self.result, self.index))

# episode
class MyView5(discord.ui.View):
    def __init__(self, details: list, index: int):
        super().__init__(timeout=None)
        i = index
        while i < int(details[ep]):
            if (i < index+pagelimit): self.add_item(ButtonSelect5(i + 1, details[url]))
            if (i == index+pagelimit): self.add_item(nextPageEP(details, i))
            i += 1

class ButtonSelect5(discord.ui.Button):
    def __init__(self, index: int, sUrl: str):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
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
    def __init__(self, details: list, index: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.details = details
        self.index = index
    
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

# bard
from bardapi import Bard

@bot.command()
async def bard(ctx, *, arg):
    os.environ['_BARD_API_KEY'] = os.getenv("BARD")
    response = Bard(timeout=60).get_answer(arg)['content']
    await ctx.reply(response[:2000])

# :|
from pygelbooru import Gelbooru

@bot.command()
async def r34(ctx, *, arg):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    results = await Gelbooru(api='https://api.rule34.xxx/').search_posts(tags=[arg])
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = BuildEmbed(str(results[0])), view = ImageView(results, 0))
@bot.command()
async def gel(ctx, *, arg):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    results = await Gelbooru().search_posts(tags=[arg])
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = BuildEmbed(str(results[0])), view = ImageView(results, 0))
@bot.command()
async def safe(ctx, *, arg):
    results = await Gelbooru(api='https://safebooru.org/').search_posts(tags=[arg])
    if len(results) == 0: return await ctx.reply("**No results found.**")
    await ctx.reply(embed = BuildEmbed(str(results[0])), view = ImageView(results, 0))

def BuildEmbed(url: str) -> discord.Embed():
    embed = discord.Embed()
    if url.endswith(".mp4"): embed.add_field(name="Video link:", value=url)
    else: embed.set_image(url = url)
    return embed

class ImageView(discord.ui.View):
    def __init__(self, results, index):
        super().__init__(timeout=None)
        if not index == 0: self.add_item(ButtonPrev(results, index))
        if index + 1 < len(results): self.add_item(ButtonNext(results, index))

class ButtonNext(discord.ui.Button):
    def __init__(self, results, index):
        super().__init__(label="Next >", style=discord.ButtonStyle.success)
        self.results, self.index = results, index
    
    async def callback(self, interaction: discord.Interaction):
        self.index+=1
        await interaction.response.edit_message(embed = BuildEmbed(str(self.results[self.index])), view = ImageView(self.results, self.index))

class ButtonPrev(discord.ui.Button):
    def __init__(self, results, index):
        super().__init__(label="< Prev", style=discord.ButtonStyle.success)
        self.results, self.index = results, index

    async def callback(self, interaction: discord.Interaction):
        self.index-=1
        await interaction.response.edit_message(embed = BuildEmbed(str(self.results[self.index])), view = ImageView(self.results, self.index))

bot.run(os.getenv("TOKEN"))