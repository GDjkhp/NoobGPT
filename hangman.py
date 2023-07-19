import random
import discord
from discord.ext import commands
import json

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data
synsets_data = read_json_file('synsets.json')

def get_random_synset():
    return synsets_data[random.randint(0, len(synsets_data)-1)]

def check(word: str, c: str, dead: list):
    return c.lower() in word.lower() or c.lower() in dead

def convert_box(word: str, dead: list) -> str:
    box = ""
    for c in word:
        if c.lower() in dead: box += c
        else: box += "_"
    return box

def add_player(p) -> dict:
    return {"score": 0, "choice": -1, "name": p, "emoji": "❓", "host": False, "confirm": -1}

def c2e(box: str) -> str:
    e = ""
    for c in box:
        if c.lower() in "qwertyuiopasdfghjklzxcvbnm": e += f":regional_indicator_{c}:"
        elif c == "_": e += "🟥"
        elif c == " ": e += "🟦"
        else: e += c
    return e

class QuizView(discord.ui.View):
    def __init__(self, ctx: commands.Context, words: list, index: int, box: str, dead: list, settings: dict):
        super().__init__(timeout=None)
        self.add_item(ButtonChoice("INPUT", ctx, words, index, box, dead, settings))
        self.add_item(ButtonChoice("CLOSE", ctx, words, index, box, dead, settings))

class MyModal(discord.ui.Modal):
    def __init__(self, ctx: commands.Context, words: list, index: int, box: list, dead: list, settings: dict):
        super().__init__(title="Enter credit card details")
        self.add_item(discord.ui.InputText(label="Expiry Date"))
        self.ctx, self.words, self.index, self.box, self.dead, self.settings = ctx, words, index, box, dead, settings

    async def callback(self, interaction: discord.Interaction):
        i, word = self.children[0].value, self.words[self.index]["word"]
        if not check(word, i, self.dead): self.settings["step"] += 1
        elif i.lower() in word.lower():
            for c in i: 
                if not c in self.dead: self.dead.append(c)
        if not i.lower() in self.dead and len(i) < 2: self.dead.append(i.lower())
        self.box = convert_box(word.replace("_", " "), self.dead)
        text = c2e(self.box) if self.settings["step"] != 8 else c2e(word.replace("_", " "))
        if self.settings["step"] != 8: 
            e = QuizEmbed(self.words, self.index, self.settings)
            if self.box != word.replace("_", " "):
                view = QuizView(self.ctx, self.words, self.index, self.box, self.dead, self.settings)
            else: 
                text, view, self.settings["result"] = f"GG!\n{text}", None, 1
            await interaction.response.edit_message(embed=e, content=text, view=view)
        else:
            self.settings["result"] = 0
            await interaction.response.edit_message(embed=e, view=None, content=f"GAME OVER!\n{text}")

class ButtonChoice(discord.ui.Button):
    def __init__(self, id: str, ctx: commands.Context, words: list, index: int, box: list, dead: list, settings: dict):
        super().__init__(label=id)
        self.id, self.ctx, self.words, self.index, self.box, self.dead, self.settings = id, ctx, words, index, box, dead, settings
    
    async def callback(self, interaction: discord.Interaction):
        if self.settings["type"] != "all" and interaction.user != self.ctx.author:
            return await interaction.response.send_message(content=f"{self.ctx.author.mention} is playing this game. Multiplayer TBD",
                                                           ephemeral=True)
        if self.id == "CLOSE": 
            await interaction.response.edit_message(content=f"You left.\n{c2e(self.words[self.index]['word'].replace('_', ' '))}", 
                                                    embed=None, view=None)
        if self.id == "INPUT": 
            await interaction.response.send_modal(MyModal(self.ctx, self.words, self.index, self.box, self.dead, self.settings))

def c_state(r: int):
    if r == 1: return 0x00ff00
    elif r == 0: return 0xff0000
    return discord.Embed.Empty

def QuizEmbed(words: list, index: int, settings: dict) -> discord.Embed:
    c = c_state(settings["result"])
    e = discord.Embed(title=words[index]["pos"], description=words[index]["definition"], color=c)
    print(e.color)
    # e.set_footer(text=f"{index+1}/{len(words)}")
    e.set_image(url=f"https://gdjkhp.github.io/img/hangman_frames/{settings['step']}.png")
    return e
    
async def HANG(ctx: commands.Context, type: str, mode: str, count: int, cat: str, diff: str):
    msg = await ctx.reply("Writing dictionary…")
    params = "`-quiz [mode: <all/anon/me>, type: <any/word/quiz>, count: <1-50>, category: <any/9-32>, difficulty: <any/easy/medium/hard>`"
    words, index = [get_random_synset() for i in range(1)], 0
    dead = [" ", "-"]
    box = convert_box(words[index]["word"].replace("_", " "), dead)
    # if mode:
    #     modes = ["all", "anon"]
    #     a = False
    #     if mode in modes: 
    #         multi = True
    #         a = True
    #     if mode == "anon": anon = True
    #     if mode == "me": a = True
    #     if not a: 
    #         modes.append("me")
    #         return await msg.edit(content=f"Mode not found.\n"+params)
    settings = {"step": 0, "type": type, "mode": mode, "count": count, "result": -1}
    await msg.edit(content=c2e(box) if settings["step"] != 8 else c2e(words[index]["word"].replace("_", " ")), 
                   embed=QuizEmbed(words, index, settings), view=QuizView(ctx, words, index, box, dead, settings))
    
# while True:
#     if box == word:
#         index+=1
#         dead = [" ", "-"]
#         box = ""
#         word: str = words[index]["word"].replace("_", " ")
#         for c in word:
#             if c.lower() in dead: box += c
#             else: box += "_"