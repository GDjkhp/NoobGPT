import discord
from discord.ext import commands
import json
import random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import pymongo
import os

myclient = pymongo.MongoClient(os.getenv('MONGO'))
mycol = myclient["games"]["wordle"]

font = ImageFont.truetype("./res/font/LibreFranklin-Bold.ttf", size=75)
colors = ["#787c7e", "#e9c342", "#77a76a"] # gray yellow green

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def add_player(p) -> dict:
    return {"score": 0, "name": p, "host": False, "confirm": -1}

def id2e(id: str) -> str:
    if id == "INPUT": return "📔"
    if id == "LEAVE": return "💩"
    if id == "NEXT": return "🩲"
    if id == "UPDATE": return "💽"

def game_reset(dead: dict, settings: dict, history: list):
    settings["step"] = 0
    settings["result"] = -1
    history.clear()
    dead["yellow"].clear()
    dead["green"].clear()
    dead["gray"].clear()

def keys(d: dict) -> str:
    text = ""
    for key, value in d.items(): 
        text += f"\n{value['name']}: {value['score']}"
    return text

def c_state(r: int):
    if r == 1: return 0x00ff00
    elif r == 0: return 0xff0000
    return None

def QuizEmbed(settings: dict, index: int, words: list, players: dict) -> discord.Embed:
    c = c_state(settings["result"])
    e = discord.Embed(color=c)
    e.set_footer(text=f"{index+1}/{len(words)}")
    e.set_author(name=keys(players))
    return e

def check_and_push(arg: str, dead: dict, real: str):
    index = 0
    real_temp = str(real)
    for c in arg:
        if c == real[index]: 
            if not c in dead["green"]: 
                dead["green"].append(c)
            if c in dead["yellow"]: 
                dead["yellow"].remove(c)
            real_temp = real_temp.replace(c, "", 1)

        elif c in real_temp and c not in dead["green"]: # blunder?
            if not c in dead["yellow"]: 
                dead["yellow"].append(c)
            real_temp = real_temp.replace(c, "", 1)

        elif not c in dead["gray"] and c not in dead["green"]: 
            dead["gray"].append(c)
        index+=1

def button_confirm(d, k) -> bool:
    d[k]["confirm"]+=1
    if d[k]["confirm"] < 1: 
        return True
    return False

def format_hearts(dead: dict) -> str:
    return f":green_heart: {dead['green']}\n:yellow_heart: {dead['yellow']}\n:grey_heart: {dead['gray']}"

def draw_rounded_rectangle(draw: ImageDraw.ImageDraw, position: tuple, size: tuple, radius: int, color: str):
    x, y = position
    width, height = size

    # Adjust dimensions to avoid 1 pixel excess
    width -= 1
    height -= 1

    draw.rectangle(
        [(x, y + radius), (x + width, y + height - radius)],
        fill=color,
    )
    draw.rectangle(
        [(x + radius, y), (x + width - radius, y + height)],
        fill=color,
    )
    draw.pieslice(
        [(x, y), (x + radius * 2, y + radius * 2)],
        start=180,
        end=270,
        fill=color,
    )
    draw.pieslice(
        [(x + width - radius * 2, y), (x + width, y + radius * 2)],
        start=270,
        end=360,
        fill=color,
    )
    draw.pieslice(
        [(x, y + height - radius * 2), (x + radius * 2, y + height)],
        start=90,
        end=180,
        fill=color,
    )
    draw.pieslice(
        [(x + width - radius * 2, y + height - radius * 2), (x + width, y + height)],
        start=0,
        end=90,
        fill=color,
    )

def wordle_image(history: list, real: str) -> discord.File:
    img = Image.new('RGBA', (500, 600))
    draw = ImageDraw.Draw(img)
    x, y, size = 0, 0, 100

    for i in range(5):
        for j in range(6):
            draw_rounded_rectangle(draw, (i*100, j*100), (size, size), 25, colors[0])
    
    if history:
        for word in history:
            # consumables
            real_temp = str(real)
            fake_temp = str(word)

            # first pass
            x, index = 0, 0
            for c in word:
                if c == real[index]:
                    draw_rounded_rectangle(draw, (x, y), (size, size), 25, colors[2])
                    real_temp = real_temp.replace(c, "", 1)
                    fake_temp = fake_temp.replace(c, "_", 1)
                # elif not c in real_temp: 
                #     draw_rounded_rectangle(draw, (x, y), (size, size), 25, colors[0])
                x+=size
                index+=1

            # second pass
            x, index = 0, 0
            for c in fake_temp:
                if c != "_" and c in real_temp:
                    draw_rounded_rectangle(draw, (x, y), (size, size), 25, colors[1])
                    real_temp = real_temp.replace(c, "", 1)
                x+=size
                index+=1

            x = 0
            for c in word:
                draw.text((x+50, y+50), c, fill="white", anchor="mm", font=font)
                x+=size

            y+=size

    # return everything all at once
    img_byte_array = BytesIO()
    img.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    return discord.File(img_byte_array, 'wordle.png')

class QuizView(discord.ui.View):
    def __init__(self, ctx: commands.Context, words: list, index: int, dead: dict, settings: dict, players: dict, history: list):
        super().__init__(timeout=None)
        possible_games = True
        if history and history[len(history)-1] == words[index]["word"].upper():
            if index+1 < len(words): 
                self.add_item(ButtonChoice("NEXT", ctx, words, index, dead, settings, players, history))
            else: possible_games = False
        else: 
            self.add_item(ButtonChoice("INPUT", ctx, words, index, dead, settings, players, history))
        if possible_games:
            self.add_item(ButtonChoice("LEAVE", ctx, words, index, dead, settings, players, history))
            # self.add_item(ButtonChoice("UPDATE", ctx, words, index, dead, settings, players, history))

class ButtonChoice(discord.ui.Button):
    def __init__(self, id: str, ctx: commands.Context, words: list, index: int, dead: dict, settings: dict, players: dict, history: list):
        super().__init__(label=id, emoji=id2e(id))
        self.id, self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history = id, ctx, words, index, dead, settings, players, history
    
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
            return await interaction.response.send_message(content=f"<@{host_id}> is playing this game. Use `-word` to create your own game.",
                                                           ephemeral=True)
        # register player choice
        if not interaction.user.id in self.players: self.players[interaction.user.id] = add_player(interaction.user)

        # buttons
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
                await interaction.response.edit_message(content=f"Someone left.\n{format_hearts(self.dead)}",
                                                        embed=QuizEmbed(self.settings, self.index, self.words, self.players),
                                                        view=QuizView(self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history))
            else: 
                return await interaction.response.edit_message(content=f"You left.\n{self.words[self.index]['word'].upper()}", embed=None, view=None)
        if self.id == "INPUT": # removing return was hot
            return await interaction.response.send_modal(MyModal(self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history))
        if self.id == "NEXT":
            game_reset(self.dead, self.settings, self.history)
            await interaction.channel.send(content=f"New game.",
                                           embed=QuizEmbed(self.settings, self.index+1, self.words, self.players),
                                           file=wordle_image(self.history, self.words[self.index+1]["word"].upper()),
                                           view=QuizView(self.ctx, self.words, self.index+1, self.dead, self.settings, self.players, self.history))
        if self.id == "UPDATE":
            if interaction.user.id != host_id: 
                return await interaction.response.send_message(f"Only <@{host_id}> can press this button.", ephemeral=True)
            await interaction.channel.send(content=f"Message updated.\n{format_hearts(self.dead)}",
                                           embed=QuizEmbed(self.settings, self.index, self.words, self.players),
                                           file=wordle_image(self.history, self.words[self.index]["word"].upper()),
                                           view=QuizView(self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history))
        await interaction.message.delete()
        await interaction.response.defer()

class MyModal(discord.ui.Modal):
    def __init__(self, ctx: commands.Context, words: list, index: int, dead: dict, settings: dict, players: dict, history: list):
        super().__init__(title="Enter credit card details")
        self.i = discord.ui.TextInput(label="Expiry Date")
        self.add_item(self.i)
        self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history = ctx, words, index, dead, settings, players, history

    async def on_submit(self, interaction: discord.Interaction):
        i, word = self.i.value.upper(), self.words[self.index]["word"].upper()

        # you don't belong here
        if len(i) != 5:
            return await interaction.response.send_message(content="hey, 5 letter words only pls.", ephemeral=True)
        
        await interaction.response.defer()
        self.history.append(i)
        check_and_push(i, self.dead, word)

        if i == word: # you win
            # leaderboard test
            user_data = mycol.find_one({"user": interaction.user.id})
            if not user_data:
                # If the user does not exist in the collection, insert a new document
                mycol.insert_one({
                    "user": interaction.user.id,
                    "servers": [interaction.guild_id],
                    "score": 6-self.settings["step"]  # Set an initial score, modify as needed
                })
            else:
                # If the user exists, update the existing document
                mycol.update_one(
                    {"user": interaction.user.id},
                    {"$addToSet": {"servers": interaction.guild_id}, "$inc": {"score": 6-self.settings["step"]}}
                )
            
            self.settings["result"] = 1
            self.players[interaction.user.id]["score"] += 1
            await interaction.channel.send(embed=QuizEmbed(self.settings, self.index, self.words, self.players),
                                           view=QuizView(self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history),
                                           file=wordle_image(self.history, word))
        else:
            self.settings["step"] += 1
            if self.settings["step"] != 6: # in-game
                await interaction.channel.send(embed=QuizEmbed(self.settings, self.index, self.words, self.players), content=format_hearts(self.dead),
                                               view=QuizView(self.ctx, self.words, self.index, self.dead, self.settings, self.players, self.history),
                                               file=wordle_image(self.history, word))
            else: # you lose
                self.settings["result"] = 0
                await interaction.channel.send(embed=QuizEmbed(self.settings, self.index, self.words, self.players),
                                               content=f"GAME OVER!\n{word}", view=None,
                                               file=wordle_image(self.history, word))
        await interaction.message.delete()

async def brag_embed(server_scores, ctx: commands.Context, global_lead: bool) -> discord.Embed:
    e = discord.Embed(color=0x00ff00, title=ctx.guild if not global_lead else "GLOBAL", description="wordle prototype")
    index, limit = 0, 10
    for user_data in server_scores:
        index+=1
        try: member = await ctx.guild.fetch_member(user_data['user'])
        except discord.NotFound: member = None
        member_name = member.name if member else "???"
        e.add_field(name=f"{index}. {member_name}", value=f"Score: {user_data['score']}", inline=False)
        if index == limit: break
    return e

async def brag_function(ctx: commands.Context, mode: str, optional: str):
    try: 
        if not optional or int(optional): pass
    except: return await ctx.reply("⁉️")
    user_id = ctx.author.id if not optional else int(optional)
    if not ctx.guild.id: return await ctx.reply(content="this is a server-only command.")
    server_scores = mycol.find({"servers": ctx.guild.id}).sort("score", pymongo.DESCENDING)
    user_data = mycol.find_one({"user": user_id, "servers": ctx.guild.id})

    if not user_data or not server_scores:
        return await ctx.reply(content="🤨")
    
    if mode == "rank":
        count = 0
        for user_data in server_scores:
            count+=1
            if user_data['user'] == user_id:
                try: 
                    if optional: member = await ctx.guild.fetch_member(user_id)
                except discord.NotFound: return await ctx.reply(content="🤨")
                return await ctx.reply(f"{ctx.author if not optional else member}\nRANK: #{count}, SCORE: {user_data['score']}")
            
    if mode == "lead":
        return await ctx.reply(embed=await brag_embed(server_scores, ctx, False))
    
    if mode == "global":
        global_scores = mycol.find({}).sort("score", pymongo.DESCENDING)
        return await ctx.reply(embed=await brag_embed(global_scores, ctx, True))

async def wordle(ctx: commands.Context, mode: str, count: str):
    params = "```-hang [mode: <all/hardcore/me> OR stats: <rank/lead/global>, count: <1-50>]```"

    if mode in ["lead", "rank", "global"]:
        return await brag_function(ctx, mode, count)

    if mode:
        modes = ["all", "me", "hardcore"]
        if mode in modes: pass
        else: return await ctx.reply(content="Mode not found."+params)
    else: mode = "me"

    synsets_data = read_json_file("./res/dict/synsets_wordle.json")
    if count:
        try:
            if int(count) > 0 and int(count) <= len(synsets_data): pass
            else: return await ctx.reply(content=f"Must be greater than 0 and less than or equal to {len(synsets_data)}."+params)
        except: return await ctx.reply(content="Not a valid integer.\n"+params)
    else: count = 1

    random.shuffle(synsets_data)
    words = synsets_data if mode == "hardcore" else synsets_data[:int(count)]
    players = {}
    players[ctx.author.id] = add_player(ctx.author)
    players[ctx.author.id]["host"] = True
    dead = {"yellow": [], "green": [], "gray": []}
    settings = {"step": 0, "mode": mode, "result": -1}
    history = []
    await ctx.reply(file=wordle_image(history, words[0]["word"].upper()),
                    embed=QuizEmbed(settings, 0, words, players), view=QuizView(ctx, words, 0, dead, settings, players, history))