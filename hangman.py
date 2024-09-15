import random
import discord
from discord import app_commands
from discord.ext import commands
import json
from util_discord import command_check, description_helper
modes = ["all", "me", "hardcore"]

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def check(word: str, c: str, dead: list):
    return c in word or c in dead

def convert_box(word: str, dead: list) -> str:
    box = ""
    for c in word:
        if c in dead: box += c
        else: box += "_"
    return box

def add_player(p) -> dict:
    return {"score": 0, "choice": -1, "name": p, "emoji": "❓", "host": False, "confirm": -1}

def c2e(box: str) -> str:
    e = ""
    for c in box:
        if c in "qwertyuiopasdfghjklzxcvbnm": e += f":regional_indicator_{c}:"
        elif c == "_": e += "🟥"
        elif c == " ": e += "🟦"
        else: e += c
    return e

def id2e(id: str) -> str:
    if id == "INPUT": return "📔"
    if id == "LEAVE": return "💩"
    if id == "NEXT": return "🩲"
    if id == "UPDATE": return "💽"

def c_state(r: int):
    if r == 1: return 0x00ff00
    elif r == 0: return 0xff0000
    return None

def keysScore(d: dict) -> str:
    text = ""
    for key, value in d.items(): text += f"\n{value['name']}: {value['score']}"
    return text

def button_confirm(d, k) -> bool:
    d[k]["confirm"]+=1
    if d[k]["confirm"] < 1: 
        return True
    return False

class QuizView(discord.ui.View):
    def __init__(self, ctx: commands.Context, words: list, index: int, box: str, dead: list, settings: dict, players: dict):
        super().__init__(timeout=None)
        possible_games = True
        if words[index]["word"].replace("_", " ").lower() != box: 
            self.add_item(ButtonChoice("INPUT", ctx, words, index, box, dead, settings, players))
        elif index+1 < len(words):
            self.add_item(ButtonChoice("NEXT", ctx, words, index, box, dead, settings, players))
            possible_games = False
        if possible_games:
            self.add_item(ButtonChoice("LEAVE", ctx, words, index, box, dead, settings, players))
            self.add_item(ButtonChoice("UPDATE", ctx, words, index, box, dead, settings, players))

class MyModal(discord.ui.Modal):
    def __init__(self, ctx: commands.Context, words: list, index: int, box: list, dead: list, settings: dict, players: dict):
        super().__init__(title="Enter credit card details")
        self.i = discord.ui.TextInput(label="Expiry Date")
        self.add_item(self.i)
        self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players = ctx, words, index, box, dead, settings, players

    async def on_submit(self, interaction: discord.Interaction):
        i, word = self.i.value.lower(), self.words[self.index]["word"].replace("_", " ").lower()
        if not check(word, i, self.dead): self.settings["step"] += 1
        elif i in word:
            for c in i: 
                if not c in self.dead: 
                    self.dead.append(c)
                    self.players[interaction.user.id]["score"] += 1
        if not i in self.dead and len(i) < 2: self.dead.append(i)
        self.box = convert_box(word, self.dead)
        text = c2e(self.box) if self.settings["step"] != 8 else c2e(word)
        view = QuizView(self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players)
        if self.settings["step"] != 8: 
            if self.box == word:
                text, self.settings["result"] = f"GG!\n{text}", 1
            e = QuizEmbed(self.words, self.index, self.settings, self.players, self.ctx)
            await interaction.response.edit_message(embed=e, content=text, view=view)
        else:
            self.settings["result"] = 0
            e = QuizEmbed(self.words, self.index, self.settings, self.players, self.ctx)
            await interaction.response.edit_message(embed=e, view=None, content=f"GAME OVER!\n{text}")

class ButtonChoice(discord.ui.Button):
    def __init__(self, id: str, ctx: commands.Context, words: list, index: int, box: list, dead: list, settings: dict, players: dict):
        super().__init__(label=id, emoji=id2e(id))
        self.id, self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players = id, ctx, words, index, box, dead, settings, players
    
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
        # solo lock
        if self.settings["mode"] != "all" and interaction.user.id != host_id:
            return await interaction.response.send_message(content=f"<@{host_id}> is playing this game. Use `-hang` to create your own game.",
                                                           ephemeral=True)
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
            for k in keys_to_remove: del self.players[k]
            if self.players:
                await interaction.response.edit_message(content=c2e(self.box), 
                                                        embed=QuizEmbed(self.words, self.index, self.settings, self.players, self.ctx), 
                                                        view=QuizView(self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players))
            else: await interaction.response.edit_message(content=f"You left.\n{c2e(self.words[self.index]['word'].replace('_', ' ').lower())}", 
                                                          embed=None, view=None)
                
        # register player choice
        await interaction.message.edit(view=None)
        if not interaction.user.id in self.players: self.players[interaction.user.id] = add_player(interaction.user)

        if self.id == "INPUT": 
            await interaction.response.send_modal(MyModal(self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players))
        if self.id == "NEXT":
            if self.settings["mode"] != "hardcore": self.settings["step"] = 0
            word = self.words[self.index+1]["word"].replace("_", " ").lower()
            self.dead = [" ", "-"]
            self.box = convert_box(word, self.dead)
            self.settings["result"] = -1
            await interaction.response.edit_message(content=c2e(self.box), 
                                                    embed=QuizEmbed(self.words, self.index+1, self.settings, self.players, self.ctx), 
                                                    view=QuizView(self.ctx, self.words, self.index+1, self.box, self.dead, self.settings, self.players))
        if self.id == "UPDATE":
            if interaction.user.id != host_id: 
                return await interaction.response.send_message(f"Only <@{host_id}> can press this button.", ephemeral=True)
            await interaction.message.edit(content="Message updated.", embed=None, view=None)
            await interaction.response.send_message(content=c2e(self.box), 
                                                    embed=QuizEmbed(self.words, self.index, self.settings, self.players, self.ctx), 
                                                    view=QuizView(self.ctx, self.words, self.index, self.box, self.dead, self.settings, self.players))

def QuizEmbed(words: list, index: int, settings: dict, players: dict, ctx: commands.Context) -> discord.Embed:
    c = c_state(settings["result"])
    e = discord.Embed(title=words[index]["pos"], description=words[index]["definition"], color=c)
    e.set_footer(text=f"{index+1}/{len(words)}")
    e.set_image(url=f"https://gdjkhp.github.io/img/hangman_frames/{settings['step']}.png")
    e.set_author(name=keysScore(players))
    return e
    
async def HANG(ctx: commands.Context, mode: str, count: str, gtype: str, cat: str, diff: str):
    if await command_check(ctx, "hang", "games"): return
    msg = await ctx.reply("Writing dictionary…")
    params = "```-hang [mode: <all/hardcore/me> count: <1-50>, type: <any/word/quiz> category: <any/9-32> difficulty: <any/easy/medium/hard>```"
    if mode:
        if mode in modes: pass
        else: return await msg.edit(content="Mode not found.\n"+params)
    else: mode = "me"
    synsets_data = read_json_file('./res/dict/synsets.json')
    if count:
        if count.isdigit():
            if int(count) > 0 and int(count) <= len(synsets_data): pass
            else: return await msg.edit(content=f"Must be greater than 0 and less than or equal to {len(synsets_data)}."+params)
        else: return await msg.edit(content="Not a valid integer.\n"+params)
    else: count = 1
    random.shuffle(synsets_data)
    words, index = synsets_data if mode == "hardcore" else synsets_data[:int(count)], 0
    dead = [" ", "-"]
    box = convert_box(words[index]["word"].replace("_", " ").replace("_", " ").lower(), dead)
    settings = {"step": 0, "type": gtype, "mode": mode, "result": -1}
    players = {}
    players[ctx.author.id] = add_player(ctx.author)
    players[ctx.author.id]["host"] = True
    await msg.edit(content=c2e(box), embed=QuizEmbed(words, index, settings, players, ctx), 
                   view=QuizView(ctx, words, index, box, dead, settings, players))

async def mode_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in modes if current.lower() in mode.lower()
    ]

class CogHang(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["games"]} {description_helper["games"]["hang"]}')
    @app_commands.autocomplete(mode=mode_auto)
    @app_commands.describe(count="Must be a valid integer.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def hang(self, ctx: commands.Context, mode: str=None, count: str=None):
        await HANG(ctx, mode, count, None, None, None)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHang(bot))