import requests
from urllib import parse as p
import random
import discord
from discord.ext import commands

async def QUIZ(ctx: commands.Context, mode: str, cat: str, diff: str, ty: str, count: str):
    msg = await ctx.reply("Crunching data…")
    params = "`-quiz [mode: <all/anon/me>, category: <any/9-32>, difficulty: <any/easy/medium/hard>, type: <multiple/boolean>, count: <1-50>]`"
    categories = requests.get("https://opentdb.com/api_category.php").json()["trivia_categories"]
    try: 
        if count and (int(count) > 51 or int(count) < 1): return await msg.edit(content="Items must be 1-50.") 
        if not count: count = "50"
    except: return await msg.edit(content="Must be integer :(")
    req = f"https://opentdb.com/api.php?amount={int(count)}&encode=url3986"
    multi, anon = False, False
    if mode:
        modes = ["all", "anon"]
        a = False
        if mode in modes: 
            multi = True
            a = True
        if mode == "anon": anon = True
        if mode == "me": a = True
        if not a: 
            modes.append("me")
            return await msg.edit(content=f"Mode not found.\n"+params)
    if cat:
        a = False
        if any([str(item["id"]) == cat for item in categories]):
            req += f"&category={cat}"
            a = True
        if cat == "any": a = True 
        if not a: return await msg.edit(content=None, embed=BuildCategory(categories))
    if diff:
        d = ["easy", "medium", "hard"]
        a = False
        if diff in d:
            req += f"&difficulty={diff}"
            a = True
        if diff == "any": a = True
        if not a:
            d.append("any")
            return await msg.edit(content=f"Difficulty not found!\n`{d}`")
    if ty:
        t = ["multiple", "boolean"]
        a = False
        if ty in t:
            req += f"&type={ty}"
            a = True
        if ty == "any": a = True
        if not a:
            t.append("any")
            return await msg.edit(content=f"Type not found!\n`{t}`")
    results = requests.get(req).json()["results"]
    results = decodeResults(results)
    players = {ctx.author.id: {"score": 0, "choice": -1, "name": ctx.author, "emoji": "❓"}}
    settings = {"multiplayer": multi, "anon": anon, "difficulty": diff, "type": ty, "count": int(count)}
    await msg.edit(content=settings, embed=BuildQuestion(results, 0, ctx, players, settings), 
                   view=QuizView(results, 0, ctx, players, settings))
    
def decodeResults(results: list) -> list:
    fResults = []
    for r in results:
        ch = p.unquote(r["correct_answer"])
        ty = p.unquote(r["type"])
        decoded_dict = {}
        for key, value in r.items():
            if isinstance(value, list):
                if ty == "boolean":
                    d = value
                    c = ["True", "False"]
                else:
                    d = [p.unquote(answer) for answer in value]
                    c = d.copy()
                    c.append(ch)
                    random.shuffle(c)
                decoded_dict["choices"] = c
            else:
                d = p.unquote(value)
            decoded_dict[key] = d
        fResults.append(decoded_dict)
    return fResults

def i2c(c) -> str:
    if c == 0: return "🇦"
    elif c == 1: return "🇧"
    elif c == 2: return "🇨"
    elif c == 3: return "🇩"
    elif c == 69: return "💀"
    elif c == -1: return "❓"
    else: return "❌"

def i2ca(c) -> str:
    a = [0, 1, 2, 3]
    if c in a: return "❓"
    else: return "❌"

def keys(d: dict, anon: bool) -> str:
    text = ""
    for key, value in d.items():
        text += f"\n{value['name']}: {i2c(value['choice'])}" if not anon else f"\n{value['name']}: {i2ca(value['choice'])}"
    return text

def keysScore(d: dict) -> str:
    text = ""
    for key, value in d.items():
        text += f"\n<@{key}>: {value['score']} {value['emoji']}"
    return text

def parseText(multi: bool, results: list, index: int, players: dict, c: int, ctx: commands.Context) -> str:
    if multi:
        text = f"{results[index]['question']}\n{results[index]['correct_answer']}"
        text += keysScore(players)
    else:
        z = [420, 69]
        if not c in z: 
            check = results[index]["correct_answer"] == results[index]["choices"][c]
            r = f"\n{results[index]['question']}\n{results[index]['correct_answer']}\nScore: {players[ctx.author.id]['score']}"
            text = "Correct!"+r if check else "Incorrect!"+r
        else: text = f"Score: {players[ctx.author.id]['score']}"
    return text

def BuildCategory(categories: list) -> discord.Embed:
    embed = discord.Embed(title=f"Available categories", color=0x00ff00)
    for c in categories:
        embed.add_field(name=c["name"], value=c["id"], inline=True)
    embed.add_field(name="Random", value="any", inline=True)
    return embed

def BuildQuestion(results: list, index: int, ctx: commands.Context, players: dict, settings: dict):
    embed = discord.Embed(title=f"{index+1}. {results[index]['question']}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(text=f"{index+1}/{len(results)}")
    if not settings["multiplayer"]: 
        if ctx.message.author.avatar: embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
        else: embed.set_author(name=ctx.author)
    else: 
        text = keys(players, settings["anon"])
        embed.set_author(name=text)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context, players: dict, settings: dict):
        super().__init__(timeout=None)
        for c in range(len(results[index]["choices"])):
            self.add_item(ButtonChoice(results, index, ctx, c, players, 0, "CHOICE", settings))
        self.add_item(ButtonChoice(results, index, ctx, -1, players, 1, "CLEAR", settings))
        self.add_item(ButtonChoice(results, index, ctx, random.randint(0, len(results[index]["choices"])-1), players, 1, "RANDOM", settings))
        self.add_item(ButtonChoice(results, index, ctx, 69, players, 2, "PURGE", settings))
        self.add_item(ButtonChoice(results, index, ctx, 420, players, 2, "END", settings))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, c: int, players: dict, row: int, id: str, settings: dict):
        emoji, l = "🔀" if id == "RANDOM" else i2c(c), id
        if id == "CHOICE": l = results[index]["choices"][c]
        super().__init__(emoji=emoji, label=l, row=row)
        self.results, self.index, self.ctx, self.c, self.players, self.id, self.settings = results, index, ctx, c, players, id, settings
    
    async def callback(self, interaction: discord.Interaction):
        if self.id == "END":
            if interaction.user != self.ctx.author: 
                return await interaction.response.send_message(f"Only {self.ctx.message.author.mention} can press this button.", ephemeral=True)
            text = parseText(self.settings["multiplayer"], self.results, self.index, self.players, self.c, self.ctx)
            return await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)
        if self.id == "PURGE":
            if interaction.user != self.ctx.author: 
                return await interaction.response.send_message(f"Only {self.ctx.message.author.mention} can press this button.", ephemeral=True)
            keys_to_remove = []
            for k, v in self.players.items():
                if v["choice"] == -1 and v["name"] != self.ctx.author:
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del self.players[k]
            text = keysScore(self.players)
            return await interaction.response.edit_message(content=text,
                                                           embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings), 
                                                           view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
        
        # solo lock
        if not self.settings["multiplayer"] and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.message.author.mention} is playing this game and set to singleplayer.", ephemeral=True)
        
        # register player choice
        if not interaction.user.id in self.players: self.players[interaction.user.id] = {"score": 0, "choice": self.c, "name": interaction.user, "emoji": "❓"}
        else: self.players[interaction.user.id]["choice"] = self.c
        
        # listen for player input
        playing = False
        for key, value in self.players.items():
            if value["choice"] == -1: playing = True
        if playing:
            text = keysScore(self.players)
            await interaction.response.edit_message(content=text,
                                                    embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings), 
                                                    view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
        else:
            # multiplayer check
            for key, value in self.players.items():
                check = self.results[self.index]["correct_answer"] == self.results[self.index]["choices"][value["choice"]]
                if check: 
                    value["score"]+=1
                    value["emoji"] = "✅"
                else: value["emoji"] = "❌"
                value["choice"] = -1
            # step
            text = parseText(self.settings["multiplayer"], self.results, self.index, self.players, self.c, self.ctx)
            if self.index+1 < len(self.results): 
                await interaction.response.edit_message(content=text,
                                                        embed=BuildQuestion(self.results, self.index+1, self.ctx, self.players, self.settings), 
                                                        view=QuizView(self.results, self.index+1, self.ctx, self.players, self.settings))
            else: await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)