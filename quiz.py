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
        for item in categories:
            if str(item["id"]) == cat:
                req = f"https://opentdb.com/api.php?amount=50&category={cat}&encode=url3986"
                break
        if not cat: return await ctx.reply(embed=BuildCategory(categories))
    results = requests.get(req).json()['results']
    results = decodeResults(results)
    # for q in results:
    #     print(f"Category: {q['category']}, Type: {q['type']}, Difficulty: {q['difficulty']}")
    #     print(q['question'])
    #     print(q['choices'])
    #     print(f"Correct: {q['correct_answer']}, Incorrect: {q['incorrect_answers']}")
    await ctx.reply(embed=BuildQuestion(results, 0, ctx, [ctx.author] if multi else None), view=QuizView(results, 0, ctx, multi, 0))

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
    else: return "🇼"

def BuildCategory(categories: list) -> discord.Embed:
    embed = discord.Embed(title=f"Available categories", color=0x00ff00)
    for c in categories:
        embed.add_field(name=c["name"], value=c["id"], inline=True)
    return embed

def BuildQuestion(results: list, index: int, ctx: commands.Context, multi: list):
    embed = discord.Embed(title=f"{index+1}. {results[index]['question']}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(text=f"{index+1}/{len(results)}")
    if not multi: embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
    else: embed.set_author(name=multi)
    for c in range(len(results[index]['choices'])):
        embed.add_field(name=i2c(c), value=results[index]['choices'][c], inline=False)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, score: int):
        super().__init__(timeout=None)
        for c in range(len(results[index]['choices'])):
            self.add_item(ButtonChoice(results, index, ctx, multi, c, score))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, c: int, score: int):
        super().__init__(emoji=i2c(c))
        self.results, self.index, self.ctx, self.multi, self.c, self.score = results, index, ctx, multi, c, score
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.author} is playing this game.", ephemeral=True)
        check = self.results[self.index]['correct_answer'] == self.results[self.index]['choices'][self.c]
        if self.index+1 < 50: 
            await interaction.response.edit_message(content=f"Correct!\nScore: {self.score}"
                                                    if check
                                                    else f"Incorrect!\n{self.results[self.index]['question']}\n{self.results[self.index]['correct_answer']}\nScore: {self.score}",
                                                    embed=BuildQuestion(self.results, self.index+1, self.ctx, [self.ctx.author] if self.multi else None), 
                                                    view=QuizView(self.results, self.index+1, self.ctx, self.multi, self.score+1 if check else self.score))
        else: await interaction.response.edit_message(content=f"Correct!\nScore: {self.score}\nTest ended."
                                                      if check
                                                      else f"Incorrect!\n{self.results[self.index]['question']}\n{self.results[self.index]['correct_answer']}\nScore: {self.score}\nTest ended.",
                                                      embed=None, view=None)