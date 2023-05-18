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

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents = intents)
client = HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
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

# search anime
@bot.command()
async def anime(ctx, *, arg):
    await ctx.reply(f"Searching \"{arg}\". Please wait...")
    result = resultsAnime(searchAnime(arg))
    embed = discord.Embed()
    for ix, vl in enumerate(result):
        embed.add_field(name=f"[{ix + 1}] {vl[title]}", value=f"{vl[url]}", inline=True)
    await ctx.reply(embed = embed, view = MyView4(result, 0))

def searchAnime(q: str):
    return q.replace(" ", "-")
def resultsAnime(data: str) -> list:
    req = client.get(f"{gogoanime}/search.html?keyword={data}")
    soup = BS(req, "lxml")
    items = soup.find("ul", {"class": "items"}).findAll("li")
    img = [items[i].find("img")["src"] for i in range(len(items))]
    urls = [items[i].find("a")["href"] for i in range(len(items))]
    title = [items[i].find("a")["title"] for i in range(len(items))]
    ids = [items[i].find("a")["title"] for i in range(len(items))]
    mov_or_tv = ["TV" for i in range(len(items))]
    return [list(sublist) for sublist in zip(title, urls, ids, mov_or_tv, img)]
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
    def __init__(self, result: list, index: int):
        super().__init__(timeout=None)
        i = index
        while i < len(result):
            if (i < index+24): self.add_item(ButtonSelect4(i + 1, result[i]))
            if (i == index+24): self.add_item(nextPage(result, i))
            i += 1

class ButtonSelect4(discord.ui.Button):
    def __init__(self, index: int, result: list):
        super().__init__(label=index, style=discord.ButtonStyle.primary)
        self.result = result
    
    async def callback(self, interaction: discord.Interaction):
        # await interaction.response.send_message(f"You clicked the button [{self.label}] {self.result[title]} ({self.result[mv_tv]})!") # Send a message when the button is clicked
        req = client.get(f"{gogoanime}{self.result[url]}")
        soup = BS(req, "lxml")
        episodes = soup.find("ul", {"id": "episode_page"}).find_all("a")[-1]["ep_end"]
        desc: str = soup.find_all("p", {"class": "type"})[1].get_text().replace("Plot Summary:", "")
        embed = discord.Embed(title=self.result[title], description=desc)
        embed.set_image(url = self.result[poster])
        await interaction.response.edit_message(embed = embed, view = MyView5(int(episodes), self.result[url], 0, self.result[poster], desc, self.result[title]))

class nextPage(discord.ui.Button):
    def __init__(self, result: list, index: int):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.result = result
        self.index = index
    
    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed()
        i = self.index
        while i < len(self.result):
            if (i < self.index+24): embed.add_field(name=f"[{i + 1}] {self.result[i][title]}", value=f"{self.result[i][url]}", inline=True)
            i += 1
        await interaction.response.edit_message(embed = embed, view = MyView4(self.result, self.index))

# episode
class MyView5(discord.ui.View):
    def __init__(self, episodes: int, sUrl: str, index: int, poster: str, desc: str, title: str):
        super().__init__(timeout=None)
        i = index
        while i < episodes:
            if (i < index+24): self.add_item(ButtonSelect5(i + 1, sUrl))
            if (i == index+24): self.add_item(nextPageEP(episodes, sUrl, i, poster, desc, title))
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
    def __init__(self, episodes: int, sUrl: str, index: int, poster: str, desc: str, title: str):
        super().__init__(label=">", style=discord.ButtonStyle.success)
        self.episodes = episodes
        self.index = index
        self.sUrl = sUrl
        self.poster = poster
        self.desc = desc
        self.title = title
    
    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.title, description=self.desc)
        embed.set_image(url = self.poster)
        await interaction.response.edit_message(embed = embed, view = MyView5(self.episodes, self.sUrl, self.index, self.poster, self.desc, self.title))

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
import requests

session = requests.Session()
session.headers = {
            "Host": "bard.google.com",
            "X-Same-Domain": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://bard.google.com",
            "Referer": "https://bard.google.com/",
        }
session.cookies.set("__Secure-1PSID", os.getenv("BARD"))

@bot.command()
async def bard(ctx, *, arg):
    bard = Bard(session=session, timeout=60)
    await ctx.reply(bard.get_answer(arg)['content'])

bot.run(os.getenv("TOKEN"))