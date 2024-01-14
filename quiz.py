import requests
from urllib import parse as p
import random
import discord
from discord.ext import commands

async def QUIZ(ctx: commands.Context, mode: str, v: str, count: str, cat: str, diff: str, ty: str):
    msg = await ctx.reply("Crunching data…")
    params = "```-quiz [mode: <all/anon/me>, version: <any/v1/v2>, count: <1-50>, category: <any/9-32>, difficulty: <any/easy/medium/hard>, type: <any/multiple/boolean>```"
    try: 
        if count and (int(count) > 51 or int(count) < 1): return await msg.edit(content="Items must be 1-50.") 
        if not count: count = "50"
    except: return await msg.edit(content="Must be integer :("+params)
    multi, anon, ck, req = False, False, None, None
    if v == None or v == "v1" or v == "any": 
        req = f"https://opentdb.com/api.php?amount={int(count)}&encode=url3986"
        ck, v = "correct_answer", "v1"
    elif v == "v2": 
        req = f"https://the-trivia-api.com/v2/questions/?limit={int(count)}"
        ck = "correctAnswer"
    else: return await msg.edit(content="Version not found."+params)
    if mode:
        modes = ["all", "anon"]
        a = False
        if mode in modes: 
            multi = True
            a = True
        if mode == "anon": anon = True
        if mode == "me": a = True
        if not a: return await msg.edit(content="Mode not found."+params)
    v2cat = "science,film_and_tv,music,history,geography,art_and_literature,sport_and_leisure,general_knowledge,science,food_and_drink".split(",")
    categories = v2cat if v == "v2" else requests.get("https://opentdb.com/api_category.php").json()["trivia_categories"]
    if cat:
        a = False
        if v == "v1" and any([str(item["id"]) == cat for item in categories]):
            req += f"&category={cat}"
            a = True
        if v == "v2" and any([item == cat for item in categories]):
            req += f"&categories={cat}"
            a = True
        if cat == "any": a = True 
        if not a: return await msg.edit(content=None, embed=BuildCategory(categories))
    if diff:
        d = ["easy", "medium", "hard"]
        a = False
        if diff in d:
            req += f"&difficulties={diff}" if v == "v2" else f"&difficulty={diff}"
            a = True
        if diff == "any": a = True
        if not a: return await msg.edit(content="Difficulty not found!"+params)
    if ty and v == "v1":
        t = ["multiple", "boolean"]
        a = False
        if ty in t:
            req += f"&type={ty}"
            a = True
        if ty == "any": a = True
        if not a: return await msg.edit(content="Type not found!"+params)
    settings = {"multiplayer": multi, "anon": anon, "difficulty": diff, "type": ty, "count": int(count), "correct_key": ck}
    results = requests.get(req).json()["results"] if v == "v1" else requests.get(req).json()
    if not results: return await msg.edit(content="Error crunching questions, try again.")
    results = decodeResults(results, settings["correct_key"])
    players = {}
    players[ctx.author.id] = add_player(ctx.author)
    players[ctx.author.id]["host"] = True
    await msg.edit(content=f"`{settings}`", embed=BuildQuestion(results, 0, ctx, players, settings), 
                   view=QuizView(results, 0, ctx, players, settings))
    
def add_player(p) -> dict:
    return {"score": 0, "choice": -1, "name": p, "emoji": "❓", "host": False, "confirm": -1}

def question_fix(q):
    if isinstance(q, dict): return q["text"]
    return q
    
def decodeResults(results: list, ck: str) -> list:
    fResults = []
    for r in results:
        ch = p.unquote(r[ck])
        ty = p.unquote(r["type"])
        decoded_dict = {}
        for key, value in r.items():
            if isinstance(value, list):
                if ty == "boolean":
                    d = value
                    c = ["True", "False"]
                elif key != "tags" and key != "regions":
                    d = [p.unquote(answer) for answer in value]
                    c = d.copy()
                    c.append(ch)
                    random.shuffle(c)
                else: d = value 
                decoded_dict["choices"] = c
            elif isinstance(value, bool) or isinstance(value, dict): d = value 
            else: d = p.unquote(value)
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
    elif c == 1337: return "🚪"
    elif c == 666: return "💽"
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
    for key, value in d.items(): text += f"\n<@{key}>: {value['score']} {value['emoji']}"
    return text

def parseText(settings: dict, results: list, index: int, players: dict, c: int, ctx: commands.Context) -> str:
    if settings["multiplayer"]:
        text = f"{question_fix(results[index]['question'])}\n{results[index][settings['correct_key']]}"
        text += keysScore(players)
    else:
        z = [420, 69, -1, 1337, 666]
        if not c in z: 
            check = results[index][settings["correct_key"]] == results[index]["choices"][c]
            r = f"\n{question_fix(results[index]['question'])}\n{results[index][settings['correct_key']]}\nScore: {players[ctx.author.id]['score']} "
            text = r+"✅" if check else r+"❌"
        else: text = f"Score: {players[ctx.author.id]['score']}"
    return text

def button_confirm(d, k) -> bool:
    d[k]["confirm"]+=1
    if d[k]["confirm"] < 1: 
        return True
    return False

def BuildCategory(categories) -> discord.Embed:
    embed = discord.Embed(title=f"Available categories", color=0x00ff00)
    for c in categories:
        if isinstance(c, dict): embed.add_field(name=c["name"], value=c["id"], inline=True)
        else: embed.add_field(name=c, value="", inline=True)
    embed.add_field(name="Random", value="any", inline=True)
    return embed

def BuildQuestion(results: list, index: int, ctx: commands.Context, players: dict, settings: dict):
    embed = discord.Embed(title=f"{index+1}. {question_fix(results[index]['question'])}", 
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
        self.add_item(ButtonChoice(results, index, ctx, random.randint(0, len(results[index]["choices"])-1), players, 1, "RANDOM", settings))
        self.add_item(ButtonChoice(results, index, ctx, -1, players, 1, "CLEAR", settings))
        self.add_item(ButtonChoice(results, index, ctx, 69, players, 2, "PURGE", settings))
        self.add_item(ButtonChoice(results, index, ctx, 1337, players, 2, "LEAVE", settings))
        self.add_item(ButtonChoice(results, index, ctx, 420, players, 2, "END", settings))
        self.add_item(ButtonChoice(results, index, ctx, 666, players, 2, "UPDATE", settings))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, c: int, players: dict, row: int, id: str, settings: dict):
        emoji, l = "🔀" if id == "RANDOM" else i2c(c), id
        if id == "CHOICE": l = results[index]["choices"][c]
        super().__init__(emoji=emoji, label=l[:80], row=row)
        self.results, self.index, self.ctx, self.c, self.players, self.id, self.settings = results, index, ctx, c, players, id, settings
    
    async def callback(self, interaction: discord.Interaction):
        # get host
        host_id = None
        a = False
        for k, v in self.players.items():
            if v["host"]: 
                host_id = k
                a = True
        if not a:
            k = next(iter(self.players))
            self.players[k]["host"] = True
        if self.id == "LEAVE":
            a = False
            keys_to_remove = []
            for k, v in self.players.items():
                if k == interaction.user.id:
                    keys_to_remove.append(k)
                    a = True
            if not a: return await interaction.response.send_message(content="Just stop.", ephemeral=True)
            if button_confirm(self.players, interaction.user.id): 
                return await interaction.response.send_message(content=f"Hey <@{interaction.user.id}>, press the button again to confirm.", 
                                                               ephemeral=True)
            text = parseText(self.settings, self.results, self.index, self.players, self.c, self.ctx)
            for k in keys_to_remove: del self.players[k]
            if not self.players:
                return await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)
            text = keysScore(self.players)
            purge = f"<@{interaction.user.id}> left."
            return await interaction.response.edit_message(content=purge+text,
                                                           embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings), 
                                                           view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
        if self.id == "END":
            if interaction.user.id != host_id: 
                return await interaction.response.send_message(f"Only <@{host_id}> can press this button.", ephemeral=True)
            if button_confirm(self.players, interaction.user.id): 
                return await interaction.response.send_message(content=f"Hey <@{interaction.user.id}>, press the button again to confirm.", 
                                                               ephemeral=True)
            text = parseText(self.settings, self.results, self.index, self.players, self.c, self.ctx)
            return await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)
        if self.id == "PURGE":
            if interaction.user.id != host_id: 
                return await interaction.response.send_message(f"Only <@{host_id}> can press this button.", ephemeral=True)
            if button_confirm(self.players, interaction.user.id): 
                return await interaction.response.send_message(content=f"Hey <@{interaction.user.id}>, press the button again to confirm.", 
                                                               ephemeral=True)
            keys_to_remove = []
            for k, v in self.players.items():
                if v["choice"] == -1 and not v["host"]:
                    keys_to_remove.append(k)
            for k in keys_to_remove: del self.players[k]
            text = keysScore(self.players)
            purge = f"{self.id}: "
            for i in keys_to_remove: purge += f"<@{i}>"
            if not keys_to_remove: purge="There is no such thing."
            return await interaction.response.edit_message(content=purge+text,
                                                           embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings), 
                                                           view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
        if self.id == "UPDATE":
            if interaction.user.id != host_id: 
                return await interaction.response.send_message(f"Only <@{host_id}> can press this button.", ephemeral=True)
            await interaction.message.edit(content="Message updated.", embed=None, view=None)
            return await interaction.response.send_message(content=keysScore(self.players),
                                                           embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings), 
                                                           view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
            
        # solo lock
        if not self.settings["multiplayer"] and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.message.author.mention} is playing this game and set to singleplayer.", 
                                                           ephemeral=True)
        
        # register player choice
        if not interaction.user.id in self.players: self.players[interaction.user.id] = add_player(interaction.user)
        self.players[interaction.user.id]["choice"] = self.c
        
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
                check = self.results[self.index][self.settings["correct_key"]] == self.results[self.index]["choices"][value["choice"]]
                if check: 
                    value["score"]+=1
                    value["emoji"] = "✅"
                else: value["emoji"] = "❌"
                value["choice"], value["confirm"] = -1, -1
            # step
            text = parseText(self.settings, self.results, self.index, self.players, self.c, self.ctx)
            if self.index+1 < len(self.results): 
                await interaction.response.edit_message(content=text,
                                                        embed=BuildQuestion(self.results, self.index+1, self.ctx, self.players, self.settings), 
                                                        view=QuizView(self.results, self.index+1, self.ctx, self.players, self.settings))
            else: await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)