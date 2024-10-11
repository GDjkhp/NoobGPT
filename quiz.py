import aiohttp
from urllib import parse as p
import random
import discord
from discord import app_commands
from discord.ext import commands
from util_discord import command_check, description_helper, get_guild_prefix
v2cat = ["science", "film_and_tv", "music", "history", "geography", "art_and_literature", "sport_and_leisure", "general_knowledge", "science", "food_and_drink"]

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: print(e)

async def QUIZ(ctx: commands.Context | discord.Interaction, mode: str, v: str, count: str, cat: str, diff: str, ty: str):
    if await command_check(ctx, "quiz", "games"): return await ctx.reply("command disabled", ephemeral=True)
    if isinstance(ctx, commands.Context): msg = await ctx.reply("Crunching data…")
    params = f"```{await get_guild_prefix(ctx)}quiz [version: <any/v1/v2> mode: <all/anon/me> count: <1-50> category: <any/9-32> difficulty: <any/easy/medium/hard> type: <any/multiple/boolean>```"
    if count:
        if count.isdigit():
            if int(count) > 51 or int(count) < 1: 
                if isinstance(ctx, commands.Context):
                    return await msg.edit(content="Items must be 1-50.") 
                if isinstance(ctx, discord.Interaction):
                    return await ctx.response.send_message(content="Items must be 1-50.") 
        else: 
            if isinstance(ctx, commands.Context):
                return await msg.edit(content="Must be integer :("+params)
            if isinstance(ctx, discord.Interaction):
                return await ctx.response.send_message(content="Must be integer :("+params)
    else: count = "50"
    multi, anon, ck, req = False, False, None, None
    if v == None or v == "v1" or v == "any": 
        req = f"https://opentdb.com/api.php?amount={int(count)}&encode=url3986"
        ck, v = "correct_answer", "v1"
    elif v == "v2": 
        req = f"https://the-trivia-api.com/v2/questions/?limit={int(count)}"
        ck = "correctAnswer"
    else: 
        if isinstance(ctx, commands.Context):
            return await msg.edit(content="Version not found.\n"+params)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(content="Version not found.\n"+params)
    if mode:
        modes = ["all", "anon"]
        a = False
        if mode in modes: 
            multi = True
            a = True
        if mode == "anon": anon = True
        if mode == "me": a = True
        if not a: 
            if isinstance(ctx, commands.Context):
                return await msg.edit(content="Mode not found."+params)
            if isinstance(ctx, discord.Interaction):
                return await ctx.response.send_message(content="Mode not found."+params)
    req_fake = await req_real("https://opentdb.com/api_category.php")
    categories = v2cat if v == "v2" else req_fake["trivia_categories"]
    if cat:
        a = False
        if v == "v1" and any([str(item["id"]) == cat for item in categories]):
            req += f"&category={cat}"
            a = True
        if v == "v2" and any([item == cat for item in categories]):
            req += f"&categories={cat}"
            a = True
        if cat == "any": a = True 
        if not a:
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=None, embed=BuildCategory(categories))
            if isinstance(ctx, discord.Interaction):
                return await ctx.response.send_message(content=None, embed=BuildCategory(categories))
    if diff:
        d = ["easy", "medium", "hard"]
        a = False
        if diff in d:
            req += f"&difficulties={diff}" if v == "v2" else f"&difficulty={diff}"
            a = True
        if diff == "any": a = True
        if not a:
            if isinstance(ctx, commands.Context):
                return await msg.edit(content="Difficulty not found!"+params)
            if isinstance(ctx, discord.Interaction):
                return await ctx.response.send_message(content="Difficulty not found!"+params)
    if ty and v == "v1":
        t = ["multiple", "boolean"]
        a = False
        if ty in t:
            req += f"&type={ty}"
            a = True
        if ty == "any": a = True
        if not a:
            if isinstance(ctx, commands.Context):
                return await msg.edit(content="Type not found!"+params)
            if isinstance(ctx, discord.Interaction):
                return await ctx.response.send_message(content="Type not found!"+params)
    settings = {"multiplayer": multi, "anon": anon, "difficulty": diff, "type": ty, "count": int(count), "correct_key": ck}
    req_fake0 = await req_real(req)
    results = req_fake0["results"] if v == "v1" else req_fake0
    if not results:
        if isinstance(ctx, commands.Context):
            return await msg.edit(content="Error crunching questions, try again.")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(content="Error crunching questions, try again.")
    results = decodeResults(results, settings["correct_key"])
    players = {}
    if isinstance(ctx, commands.Context): real_player = ctx.author
    if isinstance(ctx, discord.Interaction): real_player = ctx.user
    players[real_player.id] = add_player(real_player)
    players[real_player.id]["host"] = True
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"`{settings}`", embed=BuildQuestion(results, 0, ctx, players, settings), 
                       view=QuizView(results, 0, ctx, players, settings))
    if isinstance(ctx, discord.Interaction): 
        await ctx.response.send_message(content=f"`{settings}`", embed=BuildQuestion(results, 0, ctx, players, settings), 
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

def parseText(settings: dict, results: list, index: int, players: dict, c: int, ctx: commands.Context | discord.Interaction) -> str:
    if settings["multiplayer"]:
        text = f"{question_fix(results[index]['question'])}\n{results[index][settings['correct_key']]}"
        text += keysScore(players)
    else:
        z = [420, 69, -1, 1337, 666]
        if isinstance(ctx, commands.Context): real_player = ctx.author
        if isinstance(ctx, discord.Interaction): real_player = ctx.user
        if not c in z: 
            check = results[index][settings["correct_key"]] == results[index]["choices"][c]
            r = f"\n{question_fix(results[index]['question'])}\n{results[index][settings['correct_key']]}\nScore: {players[real_player.id]['score']} "
            text = r+"✅" if check else r+"❌"
        else: text = f"Score: {players[real_player.id]['score']}"
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

def BuildQuestion(results: list, index: int, ctx: commands.Context | discord.Interaction, players: dict, settings: dict):
    embed = discord.Embed(title=f"{index+1}. {question_fix(results[index]['question'])}", 
                          description=f"{results[index]['category']} ({results[index]['difficulty']})")
    embed.set_footer(text=f"{index+1}/{len(results)}")
    if not settings["multiplayer"]:
        if isinstance(ctx, commands.Context): real_player = ctx.author
        if isinstance(ctx, discord.Interaction): real_player = ctx.user
        if real_player.avatar: embed.set_author(name=real_player, icon_url=real_player.avatar.url) 
        else: embed.set_author(name=real_player)
    else: 
        text = keys(players, settings["anon"])
        embed.set_author(name=text)
    return embed

class QuizView(discord.ui.View):
    def __init__(self, results: list, index: int, ctx: commands.Context | discord.Interaction, players: dict, settings: dict):
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
    def __init__(self, results: list, index: int, ctx: commands.Context | discord.Interaction, c: int, players: dict, row: int, id: str, settings: dict):
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
            await interaction.response.edit_message(content="Message updated.", embed=None, view=None)
            return await interaction.followup.send(content=keysScore(self.players),
                                                   embed=BuildQuestion(self.results, self.index, self.ctx, self.players, self.settings),
                                                   view=QuizView(self.results, self.index, self.ctx, self.players, self.settings))
            
        # solo lock
        if isinstance(self.ctx, commands.Context): real_player = self.ctx.author
        if isinstance(self.ctx, discord.Interaction): real_player = self.ctx.user
        if not self.settings["multiplayer"] and interaction.user != real_player:
            return await interaction.response.send_message(f"{real_player.mention} is playing this game and set to singleplayer.", 
                                                           ephemeral=True)
        
        # register player choice
        await interaction.response.edit_message(view=None)
        if not interaction.user.id in self.players: self.players[interaction.user.id] = add_player(interaction.user)
        self.players[interaction.user.id]["choice"] = self.c
        
        # listen for player input
        playing = False
        for key, value in self.players.items():
            if value["choice"] == -1: playing = True
        if playing:
            text = keysScore(self.players)
            await interaction.edit_original_response(content=text,
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
                await interaction.edit_original_response(content=text,
                                                         embed=BuildQuestion(self.results, self.index+1, self.ctx, self.players, self.settings), 
                                                         view=QuizView(self.results, self.index+1, self.ctx, self.players, self.settings))
            else: await interaction.edit_original_response(content=text+"\nTest ended.", embed=None, view=None)

async def mode_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["all", "anon", "me"] if current.lower() in mode.lower()
    ]

async def cat_auto_v1(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    req_fake = await req_real("https://opentdb.com/api_category.php")
    return [
        app_commands.Choice(name=cat["name"], value=str(cat["id"])) for cat in req_fake["trivia_categories"] if current.lower() in cat["name"].lower()
    ]

async def cat_auto_v2(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=cat, value=cat) for cat in v2cat if current.lower() in cat.lower()
    ]

async def diff_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=diff, value=diff) for diff in ["any", "easy", "medium", "hard"] if current.lower() in diff.lower()
    ]

async def type_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=type_, value=type_) for type_ in ["any", "multiple", "boolean"] if current.lower() in type_.lower()
    ]

class CogQuiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quiz(self, ctx: commands.Context, version: str=None, mode: str=None, count: str=None, category: str=None, difficulty: str=None, type_: str=None):
        await QUIZ(ctx, mode, version, count, category, difficulty, type_)

    @app_commands.command(name="quiz-v1", description=f"{description_helper['emojis']['games']} opentdb")
    @app_commands.autocomplete(mode=mode_auto, category=cat_auto_v1, difficulty=diff_auto, type=type_auto)
    @app_commands.describe(count="Set count (Must be a valid integer: 1-50)",
                           mode="Set game mode", category="Set category", difficulty="Set difficulty", type="Set question type")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def quizv1(self, ctx: discord.Interaction, mode: str=None, count: str=None, category: str=None, difficulty: str=None, type: str=None):
        await QUIZ(ctx, mode, "v1", count, category, difficulty, type)

    @app_commands.command(name="quiz-v2", description=f"{description_helper['emojis']['games']} the-trivia-api")
    @app_commands.autocomplete(mode=mode_auto, category=cat_auto_v2, difficulty=diff_auto, type=type_auto)
    @app_commands.describe(count="Set count (Must be a valid integer: 1-50)",
                           mode="Set game mode", category="Set category", difficulty="Set difficulty", type="Set question type")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def quizv2(self, ctx: discord.Interaction, mode: str=None, count: str=None, category: str=None, difficulty: str=None, type: str=None):
        await QUIZ(ctx, mode, "v2", count, category, difficulty, type)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogQuiz(bot))