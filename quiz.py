import requests
from urllib import parse as p
import random
import discord
from discord.ext import commands

async def QUIZ(ctx: commands.Context, mode: str, cat: str, diff: str, ty: str, count: str):
    categories = requests.get('https://opentdb.com/api_category.php').json()['trivia_categories']
    try: 
        if count and int(count) > 51: return await ctx.reply("Items must be 50 or less.") 
        if not count: count = "50"
    except: return await ctx.reply("Must be integer :(")
    req, multi = f"https://opentdb.com/api.php?amount={int(count)}&encode=url3986", False
    if mode == "all": multi = True
    if cat:
        a = False
        if any([str(item["id"]) == cat for item in categories]):
            req += f"&category={cat}"
            a = True
        if cat == 'any': a = True 
        if not a: return await ctx.reply(embed=BuildCategory(categories))
    if diff:
        d = ['easy', 'medium', 'hard']
        a = False
        if diff in d:
            req += f"&difficulty={diff}"
            a = True
        if diff == 'any': a = True
        if not a:
            d.append('any')
            return await ctx.reply(f"Difficulty not found!\n`{d}`")
    if ty:
        t = ['multiple', 'boolean']
        a = False
        if ty in t:
            req += f"&type={ty}"
            a = True
        if ty == 'any': a = True
        if not a:
            t.append('any')
            return await ctx.reply(f"Type not found!\n`{t}`")
    results = requests.get(req).json()['results']
    results = decodeResults(results)
    # for q in results:
    #     print(f"Category: {q['category']}, Type: {q['type']}, Difficulty: {q['difficulty']}")
    #     print(q['question'])
    #     print(q['choices'])
    #     print(f"Correct: {q['correct_answer']}, Incorrect: {q['incorrect_answers']}")
    await ctx.reply(embed=BuildQuestion(results, 0, ctx, {ctx.author.id: {'score': 0, 'choice': -1, "name": ctx.author}} if multi else None), 
                    view=QuizView(results, 0, ctx, multi, {ctx.author.id: {'score': 0, 'choice': -1, "name": ctx.author}}))
    
def decodeResults(results: list) -> list:
    fResults = []
    for r in results:
        ch = p.unquote(r['correct_answer'])
        ty = p.unquote(r['type'])
        decoded_dict = {}
        for key, value in r.items():
            if isinstance(value, list):
                if ty == 'boolean':
                    d = value
                    c = ["True", "False"]
                else:
                    d = [p.unquote(answer) for answer in value]
                    c = d.copy()
                    c.append(ch)
                    random.shuffle(c)
                decoded_dict['choices'] = c
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
    else: return "❌"

def keys(d: dict, ctx: commands.Context) -> str:
    text = ""
    for key, value in d.items():
        text += f"\n{value['name']}: {i2c(value['choice'])}"
    return text

def keysScore(d: dict) -> str:
    text = ""
    for key, value in d.items():
        text += f"\n<@{key}>: {value['score']}"
    return text

def BuildCategory(categories: list) -> discord.Embed:
    embed = discord.Embed(title=f"Available categories", color=0x00ff00)
    for c in categories:
        embed.add_field(name=c["name"], value=c["id"], inline=True)
    embed.add_field(name="Random", value="any", inline=True)
    return embed

def BuildQuestion(results: list, index: int, ctx: commands.Context, multi: dict):
    embed = discord.Embed(title=f"{index+1}. {results[index]['question']}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(text=f"{index+1}/{len(results)}")
    if not multi: 
        if ctx.message.author.avatar.url: embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
        else: embed.set_author(name=ctx.author)
    else: 
        text = keys(multi, ctx)
        embed.set_author(name=text)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, players: dict):
        super().__init__(timeout=None)
        for c in range(len(results[index]['choices'])):
            self.add_item(ButtonChoice(results, index, ctx, multi, c, players, 0, "CHOICE"))
        self.add_item(ButtonChoice(results, index, ctx, multi, 69, players, 1, "PURGE"))
        self.add_item(ButtonChoice(results, index, ctx, multi, 420, players, 1, "END"))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, c: int, players: dict, row: int, id: str):
        super().__init__(emoji=i2c(c), label=results[index]['choices'][c] if id == "CHOICE" else id, row=row)
        self.results, self.index, self.ctx, self.multi, self.c, self.players, self.id = results, index, ctx, multi, c, players, id
    
    async def callback(self, interaction: discord.Interaction):
        if self.id == "END":
            if interaction.user != self.ctx.author: 
                return await interaction.response.send_message(f"Only {self.ctx.message.author.mention} can press this button.", ephemeral=True)
            text = parseText(self.multi, self.results, self.index, self.players, self.c, self.ctx)
            return await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)
        if self.id == "PURGE":
            if interaction.user != self.ctx.author: 
                return await interaction.response.send_message(f"Only {self.ctx.message.author.mention} can press this button.", ephemeral=True)
            keys_to_remove = []
            for k, v in self.players.items():
                if v['choice'] == -1 and v['name'] != self.ctx.author:
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del self.players[k]
            text = keysScore(self.players)
            return await interaction.response.edit_message(content=text,
                                                           embed=BuildQuestion(self.results, self.index, self.ctx, self.players if self.multi else None), 
                                                           view=QuizView(self.results, self.index, self.ctx, self.multi, self.players))
        
        # solo lock
        if not self.multi and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.message.author.mention} is playing this game.", ephemeral=True)
        
        # register player choice
        if not interaction.user.id in self.players: self.players[interaction.user.id] = {'score': 0, 'choice': self.c, 'name': interaction.user}
        else: self.players[interaction.user.id]['choice'] = self.c
        
        # listen for player input
        playing = False
        for key, value in self.players.items():
            if value['choice'] == -1: playing = True
        if playing:
            text = keysScore(self.players)
            await interaction.response.edit_message(content=text,
                                                    embed=BuildQuestion(self.results, self.index, self.ctx, self.players if self.multi else None), 
                                                    view=QuizView(self.results, self.index, self.ctx, self.multi, self.players))
        else:
            # multiplayer check
            for key, value in self.players.items():
                check = self.results[self.index]['correct_answer'] == self.results[self.index]['choices'][value['choice']]
                if check: value['score']+=1
                value['choice'] = -1
            # step
            text = parseText(self.multi, self.results, self.index, self.players, self.c, self.ctx)
            if self.index+1 < len(self.results): 
                await interaction.response.edit_message(content=text,
                                                        embed=BuildQuestion(self.results, self.index+1, self.ctx, self.players if self.multi else None), 
                                                        view=QuizView(self.results, self.index+1, self.ctx, self.multi, self.players))
            else: await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)

def parseText(multi: bool, results: list, index: int, players: dict, c: int, ctx: commands.Context) -> str:
    if multi:
        text = f"{results[index]['question']}\n{results[index]['correct_answer']}"
        text += keysScore(players)
    else:
        check = results[index]['correct_answer'] == results[index]['choices'][c]
        text = f"Correct!\nScore: {players[ctx.author.id]['score']}" if check else f"Incorrect!\n{results[index]['question']}\n{results[index]['correct_answer']}\nScore: {players[ctx.author.id]['score']}"
    return text