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
    print(results)
    results = decodeResults(results)
    # for q in results:
    #     print(f"Category: {q['category']}, Type: {q['type']}, Difficulty: {q['difficulty']}")
    #     print(q['question'])
    #     print(f"Correct: {q['correct_answer']}, Incorrect: {q['incorrect_answers']}")
    await ctx.reply(embed=BuildQuestion(results, 0, ctx, [ctx.author] if multi else None), view=QuizView(results, 0, ctx, multi))

def BuildCategory(categories: list) -> discord.Embed:
    embed = discord.Embed(title=f"Available categories", color=0x00ff00)
    for c in categories:
        embed.add_field(name=c["name"], value=c["id"], inline=True)
    return embed

def decodeResults(results: list) -> list:
    fResults = []
    for r in results:
        decoded_dict = {}
        for key, value in r.items():
            if isinstance(value, list):
                d = [p.unquote(answer) for answer in value]
            else:
                d = p.unquote(value)
            decoded_dict[key] = d
        fResults.append(decoded_dict)
    return fResults

def BuildQuestion(results: list, index: int, ctx: commands.Context, multi: list):
    embed = discord.Embed(title=f"{index+1}. {results[index]['question']}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(f"{index+1}/{len(results)}")
    if not multi: embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
    else: embed.set_author(name=multi)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool):
        super().__init__(timeout=None)
        choices: list = results[index]['incorrect_answers']
        choices.append(results[index]['correct_answer'])
        random.shuffle(choices)
        for c in range(len(choices)):
            self.add_item(ButtonChoice(results, index, ctx, multi, c, choices, results[index]['correct_answer']))

class ButtonChoice(discord.ui.Button):
    def __init__(self, results: list, index: int, ctx: commands.Context, multi: bool, c: int, choices: list, correct: str):
        l: str = "🇼"
        if c == 0:
            l = "🇦"
        elif c == 1:
            l = "🇧"
        elif c == 2:
            l = "🇨"
        elif c == 3:
            l = "🇩"
        super().__init__(emoji=l)
        self.results, self.index, self.ctx, self.multi, self.c, self.choices, self.correct = results, index, ctx, multi, c, choices, correct
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            await interaction.response.send_message(f"{self.ctx.author} is playing this game.", ephemeral=True)
        elif self.index+1 < 50: 
            await interaction.response.edit_message(content="Correct" if self.correct == self.choices[self.c] else f"Incorrect. {self.correct}",
                                                    embed=BuildQuestion(self.results, self.index+1, self.ctx, None), 
                                                    view=QuizView(self.results, self.index+1, self.ctx, self.multi))
        else: await interaction.response.edit_message(content="Correct" if self.correct == self.choices[self.c] else f"Incorrect. {self.correct}\nTest ended.")
