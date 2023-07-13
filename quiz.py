import requests
from urllib import parse as p
import random
import discord
from discord.ext import commands

async def QUIZ(ctx: commands.Context, mode: str, cat: str):
    categories = requests.get('https://opentdb.com/api_category.php').json()['trivia_categories']
    req, multi = "https://opentdb.com/api.php?amount=50&encode=url3986", False
    if mode == "all": multi = True
    if cat:
        a = False
        for item in categories:
            if str(item["id"]) == cat:
                req = f"https://opentdb.com/api.php?amount=50&category={cat}&encode=url3986"
                a = True
                break
        if not a: return await ctx.reply(embed=BuildCategory(categories))
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
        decoded_dict = {}
        for key, value in r.items():
            if isinstance(value, list):
                d = [p.unquote(answer) for answer in value]
                c = [p.unquote(answer) for answer in value]
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
    return embed

def BuildQuestion(results: list, index: int, ctx: commands.Context, multi: dict):
    embed = discord.Embed(title=f"{index+1}. {results[index]['question']}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(text=f"{index+1}/{len(results)}")
    if not multi: embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
    else: 
        text = keys(multi, ctx)
        embed.set_author(name=text)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, players: dict):
        super().__init__(timeout=None)
        for c in range(len(results[index]['choices'])):
            self.add_item(ButtonChoice(results, index, ctx, multi, c, players))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, c: int, players: dict):
        super().__init__(emoji=i2c(c), label=results[index]['choices'][c])
        self.results, self.index, self.ctx, self.multi, self.c, self.players = results, index, ctx, multi, c, players
    
    async def callback(self, interaction: discord.Interaction):
        if not self.multi and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.message.author.mention} is playing this game.", ephemeral=True)
        if not interaction.user.id in self.players: self.players[interaction.user.id] = {'score': 0, 'choice': self.c, 'name': interaction.user}
        else: self.players[interaction.user.id]['choice'] = self.c
        playing = False
        for key, value in self.players.items():
            if value['choice'] == -1: playing = True
        if playing:
            text = keysScore(self.players)
            await interaction.response.edit_message(content=text,
                                                    embed=BuildQuestion(self.results, self.index, self.ctx, self.players if self.multi else None), 
                                                    view=QuizView(self.results, self.index, self.ctx, self.multi, self.players))
        else:
            for key, value in self.players.items():
                check = self.results[self.index]['correct_answer'] == self.results[self.index]['choices'][value['choice']]
                if check: value['score']+=1
                value['choice'] = -1
            check = self.results[self.index]['correct_answer'] == self.results[self.index]['choices'][self.c]
            text = f"Correct!\nScore: {self.players[self.ctx.author.id]['score']}" if check else f"Incorrect!\n{self.results[self.index]['question']}\n{self.results[self.index]['correct_answer']}\nScore: {self.players[self.ctx.author.id]['score']}"
            if self.multi:
                text = f"{self.results[self.index]['question']}\n{self.results[self.index]['correct_answer']}"
                text += keysScore(self.players)
            if self.index+1 < 50: 
                await interaction.response.edit_message(content=text,
                                                        embed=BuildQuestion(self.results, self.index+1, self.ctx, self.players if self.multi else None), 
                                                        view=QuizView(self.results, self.index+1, self.ctx, self.multi, self.players))
            else: await interaction.response.edit_message(content=text+"\nTest ended.", embed=None, view=None)
