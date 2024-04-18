import discord
from discord.ext import commands
from character_ai import PyAsyncCAI
import asyncio
import os
import pymongo
import aiohttp
import random
import re
from queue import Queue

myclient = pymongo.MongoClient(os.getenv('MONGO'))
mycol = myclient["ai"]["character"]
client = PyAsyncCAI(os.getenv('CHARACTER'))
pagelimit=12
typing_chans = []
supported = [discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread] # sussy

# queue system
tasks_queue = Queue()
async def run_tasks():
    while True:
        if not tasks_queue.empty():
            ctx, x, text = tasks_queue.get()

            db = await asyncio.to_thread(get_database, ctx.guild.id)
            if db["channel_mode"] and not ctx.channel.id in db["channels"]: continue
            if db["message_rate"] == 0: continue

            if generate_random_bool(get_rate(ctx, x)):
                try:
                    if ctx.channel.id in typing_chans:
                        await send_webhook_message(ctx, x, text)
                    else:
                        async with ctx.typing():
                            typing_chans.append(ctx.channel.id)
                            await send_webhook_message(ctx, x, text)
                            typing_chans.remove(ctx.channel.id)
                except Exception as e: print(e)      
        await asyncio.sleep(1) # DO NOT REMOVE

def add_task(ctx, x, text):
    tasks_queue.put((ctx, x, text))

async def c_ai_init():
    task = asyncio.create_task(run_tasks())
    await task

# the real
async def c_ai(bot: commands.Bot, msg: discord.Message):
    if not type(msg.channel) in supported: return
    if msg.author.id == bot.user.id: return
    if msg.content == "": return # you can send blank messages
    ctx = await bot.get_context(msg) # context hack

    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles: return

    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: return
    if db["message_rate"] == 0: return

    # get character (lowercase mention, roles, reply)
    chars = []
    clean_text = replace_mentions(msg, bot)
    for x in db["characters"]:
        if smart_str_compare(clean_text, x["name"]): chars.append(x)
    if msg.reference:
        ref_msg = await msg.channel.fetch_message(msg.reference.message_id)
        for x in db["characters"]:
            if x["name"] == ref_msg.author.name: chars.append(x)

    if not chars:
        trigger = generate_random_bool(db["message_rate"])
        if trigger and db["characters"]:
            # print("random get")
            random.shuffle(db["characters"])
            if not db["characters"][0] == msg.author.name:
                chars.append(db["characters"][0])
    if not chars: return

    for x in chars:
        if x["name"] == msg.author.name: continue
        if generate_random_bool(get_rate(ctx, x)):
            if ctx.channel.id in typing_chans:
                data = await client.chat.send_message(x["history_id"], x["username"], clean_text)
                if data: add_task(ctx, x, data['replies'][0]['text'])
            else:
                async with ctx.typing():
                    typing_chans.append(ctx.channel.id)
                    data = await client.chat.send_message(x["history_id"], x["username"], clean_text)
                    if data: add_task(ctx, x, data['replies'][0]['text'])
                    typing_chans.remove(ctx.channel.id)

async def add_char(ctx: commands.Context, text: str, list_type: str):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not list_type in ["trending", "recommended"]: 
        if not text: return await ctx.reply("?")
    else: text = list_type
    try:
        res = await search_char(text, list_type)
        if not res: return await ctx.reply("no results found")
        await ctx.reply(view=MyView4(ctx, text, res, 0), embed=search_embed(text, res, 0))
    except Exception as e:
        print(e)
        await ctx.reply("an error occured")

async def delete_char(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not db["characters"]: return await ctx.reply("no entries found")
    await ctx.reply(view=DeleteView(ctx, db["characters"], 0), embed=view_embed(ctx, db["characters"], 0, 0xff0000))

async def t_chan(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    ok = await asyncio.to_thread(toggle_chan, ctx.guild.id, ctx.channel.id)
    if ok: await ctx.reply("channel added to the list")
    else: await ctx.reply("channel removed from the list")

async def t_adm(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"]: 
        await asyncio.to_thread(pull_ad, ctx.guild.id)
        await ctx.reply("admin approval off")
    else: 
        await asyncio.to_thread(push_ad, ctx.guild.id)
        await ctx.reply("admin approval on")

async def t_mode(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    if db["channel_mode"]: 
        await asyncio.to_thread(pull_mode, ctx.guild.id)
        await ctx.reply("channel mode off")
    else: 
        await asyncio.to_thread(push_mode, ctx.guild.id)
        await ctx.reply("channel mode on")

async def set_rate(ctx: commands.Context, num):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not num: return await ctx.reply("?")
    if not num.isdigit(): return await ctx.reply("not a digit")
    num = fix_num(num)
    await asyncio.to_thread(push_rate, ctx.guild.id, num)
    await ctx.reply(f"message_rate set to {num}")

async def view_char(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not db["characters"]: return await ctx.reply("no entries found")
    text = f"message_rate: {db['message_rate']}%\nchannel_mode: {db['channel_mode']}\nadmin_approval: {db['admin_approval']}"
    await ctx.reply(view=AvailView(ctx, db["characters"], 0), embed=view_embed(ctx, db["characters"], 0, 0x00ff00), content=text)

async def edit_char(ctx: commands.Context, rate: str):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not rate: return await ctx.reply("?")
    if not rate.isdigit(): return await ctx.reply("not a digit :(")
    rate = fix_num(rate)

    if not db["characters"]: return await ctx.reply("no entries found")
    await ctx.reply(view=EditView(ctx, db["characters"], 0, rate), 
                    embed=edit_embed(ctx, db["characters"], 0, 0x00ffff))

async def c_help(ctx: commands.Context):
    text = "Character.ai is an American neural language model chatbot service that can generate human-like text responses and participate in contextual conversation."
    text += "\n\nAvailable commands:"
    text += "\n`-cadd <query>` add a character"
    text += "\n`-cdel` delete a character"
    text += "\n`-cchan` add channel"
    text += "\n`-crate <int>` set global message_rate (0-100)"
    text += "\n`-cedit <int>` set char_message_rate per channel (0-100)"
    text += "\n`-cmode` toggle channel mode"
    text += "\n`-cadm` toggle admin approval"
    text += "\n`-cchar` available characters"
    text += "\n`-ctren` trending characters"
    text += "\n`-crec` recommended characters"
    await ctx.reply(text)

# utils
async def search_char(text: str, list_type: str):
    if list_type == "trending": 
        res = await client.character.trending()
        return res["trending_characters"]
    if list_type == "recommended":
        res = await client.character.recommended()
        return res["recommended_characters"]
    res = await client.character.search(text)
    return res["characters"]
async def load_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return image_data
            else:
                print(f"Failed to load image from URL: {url}")
                return await load_image("https://gdjkhp.github.io/img/dc.png")
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def search_embed(arg: str, result: list, index: int):
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] {result[i]['participant__name']}", value=f"{result[i]['title']}")
        i += 1
    return embed
def view_embed(ctx: commands.Context, result: list, index: int, col: int):
    embed = discord.Embed(title=ctx.guild, description=f"{len(result)} found", color=col)
    i = index
    while i < len(result):
        if (i < index+pagelimit): 
            embed.add_field(name=f"[{i + 1}] {result[i]['name']}", value=f"{get_rate(ctx, result[i])}%")
        i += 1
    return embed
def edit_embed(ctx: commands.Context, result: list, index: int, col: int):
    embed = discord.Embed(title="char_message_rate", description=f"{len(result)} found", color=col)
    i = index
    while i < len(result):
        if (i < index+pagelimit):
            embed.add_field(name=f"[{i + 1}] {result[i]['name']}", value=f"{get_rate(ctx, result[i])}%")
        i += 1
    return embed
def generate_random_bool(num):
    chance = num / 100 # convert number to probability
    result = random.random() 
    # print(result)
    return result < chance
def clean_gdjkhp(o: str, n: str):
    return o.replace("GDjkhp", n)
def replace_mentions(message: discord.Message, bot: commands.Bot):
    content = message.content
    if message.mentions:
        for mention in message.mentions:
            content = content.replace(
                f'<@{mention.id}>',
                mention.name
            )
    if message.role_mentions:
        for role_mention in message.role_mentions:
            content = content.replace(
                f'<@&{role_mention.id}>',
                role_mention.name
            )
    for emoji in bot.emojis: # global cache
        content = content.replace(str(emoji), f':{emoji.name}:')
    content = re.sub(r'<a?:[^\s]+:([0-9]+)>', '', content) # nitro_emoji_pattern
    return content
async def webhook_exists(webhook_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(webhook_url) as response:
                return response.status != 404
    except Exception as e:
        print("Error:", e)
        return False
async def send_webhook_message(ctx: commands.Context, x, text):
    wh = await get_webhook(ctx, x)
    if wh:
        if type(ctx.channel) == discord.Thread:
            await wh.send(clean_gdjkhp(text, ctx.author.name), thread=ctx.channel.id)
        else:
            await wh.send(clean_gdjkhp(text, ctx.author.name))
def snake(text: str):
    words = []
    current_word = ""
    for char in text:
        if char.isupper():
            if current_word:
                words.append(current_word)
            current_word = char.lower()
        else:
            current_word += char
    if current_word:
        words.append(current_word)
    return words
def smart_str_compare(text: str, char: str):
    snake_splits = snake(char)
    text, char = text.lower(), char.lower()
    char_splits = char.split()
    no_space_char = re.sub(r'[^a-zA-Z0-9]', '', char)
    remove_symbols_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    if char in text: return True # old
    if no_space_char in text: return True
    for x in char_splits:
        for y in remove_symbols_text.split():
            if x == y: return True
    for x in snake_splits: # weird
        for y in remove_symbols_text.split():
            if x == y: return True
    return False
def fix_num(num):
    num = int(num)
    if num < 0: num = 0
    elif num > 100: num = 100
    return num
def get_rate(ctx: commands.Context, x):
    for wh in x["webhooks"]:
        parent = ctx.channel
        if type(parent) == discord.Thread:
            parent = parent.parent
        if wh["channel"] == parent.id:
            if type(ctx.channel) == discord.Thread:
                if wh.get("threads"):
                    for thread in wh["threads"]:
                        if thread["id"] == ctx.channel.id:
                            return thread["rate"]
            else:
                if wh.get("char_message_rate"): return wh["char_message_rate"]
    return 0

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): 
                self.add_option(label=f"[{i + 1}] {result[i]['participant__name']}", value=i, description=f"{result[i]['title']}"[:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        selected = self.result[int(self.values[0])]

        await interaction.message.edit(view=None, content=f'adding {selected["participant__name"]}', embed=None)
        await interaction.response.defer()
        
        db = await asyncio.to_thread(get_database, self.ctx.guild.id)

        if db.get("characters"):
            found = False
            for x in db["characters"]:
                if x["name"] == selected["participant__name"]: found = True
            if found:
                return await interaction.followup.send(f"{selected['participant__name']} is already in chat", ephemeral=True)
        
        try:
            chat = await client.chat.new_chat(selected["external_id"])
        except Exception as e:
            print(e)
            return await interaction.message.edit(content="an error occured", embed=None, view=None)
        
        if chat:
            participants = chat['participants']
            if not participants[0]['is_human']:
                tgt = participants[0]['user']['username']
            else:
                tgt = participants[1]['user']['username']

            # thread support
            parent = self.ctx.channel
            threads = []
            if type(parent) == discord.Thread:
                parent = parent.parent
                threads = [{"id": self.ctx.channel.id, "rate": 100}]

            whs = await parent.webhooks()
            if len(whs) == 15: return await interaction.message.edit(content="webhook limit reached, please delete at least one", 
                                                                     embed=None, view=None)
            img = await load_image(f"https://characterai.io/i/400/static/avatars/{selected['avatar_file_name']}")
            wh = await parent.create_webhook(name=selected["participant__name"], avatar=img)
            role = await create_role(self.ctx, selected["participant__name"])
            data = {
                "name": selected["participant__name"],
                "description": selected['title'],
                "username": tgt,
                "history_id": chat["external_id"],
                "role_id": role.id,
                "avatar": img,
                "webhooks": [
                    {
                        "channel": parent.id,
                        "url": wh.url,
                        "char_message_rate": 100,
                        "threads": threads,
                    }
                ]
            }
            await asyncio.to_thread(push_character, self.ctx.guild.id, data)
            await interaction.message.edit(content=f"{selected['participant__name']} has been added to the server", embed=None, view=None)
            if type(parent) == discord.Thread:
                await wh.send(clean_gdjkhp(chat["messages"][0]["text"], self.ctx.author.name), thread=self.ctx.channel.id)
            else:
                await wh.send(clean_gdjkhp(chat["messages"][0]["text"], self.ctx.author.name))

class MyView4(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(ctx, arg, result, 0, "⏪"))
            self.add_item(nextPage(ctx, arg, result, index - pagelimit, "◀️"))
        if not last_index == len(result):
            self.add_item(nextPage(ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(ctx, arg, result, max_page, "⏩"))
        self.add_item(CancelButton(ctx))

class nextPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = MyView4(self.ctx, self.arg, self.result, self.index), 
                                                embed=search_embed(self.arg, self.result, self.index))
        
class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success)
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None, embed=None, content="the operation was cancelled")

class DeleteChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): 
                self.add_option(label=f"[{i + 1}] {result[i]['name']}", value=i, description=result[i]["description"][:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        selected = self.result[int(self.values[0])]

        await interaction.message.edit(view=None, content=f'deleting {selected["name"]}', embed=None)
        await interaction.response.defer()

        role = fetch_role(self.ctx, selected["role_id"])
        if role: await delete_role(role)
        await delete_webhooks(self.ctx, selected)

        await asyncio.to_thread(pull_character, self.ctx.guild.id, selected)
        await interaction.message.edit(content=f"{selected['name']} has been deleted to the server", embed=None, view=None)

class DeleteView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(DeleteChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPageDelete(ctx, result, 0, "⏪"))
            self.add_item(nextPageDelete(ctx, result, index - pagelimit, "◀️"))
        if not last_index == len(result):
            self.add_item(nextPageDelete(ctx, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPageDelete(ctx, result, max_page, "⏩"))
        self.add_item(CancelButton(ctx))

class nextPageDelete(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx = result, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = DeleteView(self.ctx, self.result, self.index), 
                                                embed= view_embed(self.ctx, self.result, self.index, 0xff0000))

class AvailView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        if index - pagelimit > -1:
            self.add_item(nextPageAvail(ctx, result, 0, "⏪"))
            self.add_item(nextPageAvail(ctx, result, index - pagelimit, "◀️"))
        if not last_index == len(result):
            self.add_item(nextPageAvail(ctx, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPageAvail(ctx, result, max_page, "⏩"))

class nextPageAvail(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx = result, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = AvailView(self.ctx, self.result, self.index), 
                                                embed= view_embed(self.ctx, self.result, self.index, 0x00ff00))

class EditChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list, rate: int):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx, self.rate = index, result, ctx, rate
        while i < len(result): 
            if (i < index+pagelimit):
                self.add_option(label=f"[{i + 1}] {result[i]['name']}", value=i, description=f"{get_rate(ctx, result[i])}%")
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        selected = self.result[int(self.values[0])]

        await interaction.message.edit(view=None, content=f'setting {selected["name"]} char_message_rate to {self.rate}', embed=None)
        await interaction.response.defer()

        if not selected.get("webhooks"): # old
            await asyncio.to_thread(pull_character, self.ctx.guild.id, selected)
            selected["webhooks"] = []
            await asyncio.to_thread(push_character, self.ctx.guild.id, selected)

        found = False
        mod_webhooks = list(selected["webhooks"])
        for w in selected["webhooks"]:
            parent = self.ctx.channel
            if type(parent) == discord.Thread:
                parent = parent.parent
            if w["channel"] == parent.id:
                url = w["url"]
                if await webhook_exists(url):
                    found = True
                    await asyncio.to_thread(pull_character, self.ctx.guild.id, selected)
                    if type(self.ctx.channel) == discord.Thread:
                        if not w.get("threads"): w["threads"] = []
                        w["threads"].append({"id": self.ctx.channel.id, "rate": self.rate})
                    else:
                        w["char_message_rate"] = self.rate
                    await asyncio.to_thread(push_character, self.ctx.guild.id, selected)
                    break
                else: mod_webhooks.remove(w)
        
        if not found: # create webhook
            parent = self.ctx.channel
            threads = []
            if type(parent) == discord.Thread:
                parent = parent.parent
                threads = [{"id": self.ctx.channel.id, "rate": self.rate}]
            whs = await parent.webhooks()
            if len(whs) == 15:
                return await interaction.message.edit(content="webhook limit reached, please delete at least one", embed=None, view=None)
            wh = await parent.create_webhook(name=selected["name"], avatar=selected["avatar"])
            await asyncio.to_thread(pull_character, self.ctx.guild.id, selected)
            selected["webhooks"] = mod_webhooks # malform fix
            await asyncio.to_thread(push_webhook, self.ctx.guild.id, selected, {
                "channel": parent.id, "url": wh.url, "char_message_rate": self.rate, "threads": threads})

        await interaction.message.edit(content=f"{selected['name']} char_message_rate is now set to {self.rate} on this channel", 
                                       embed=None, view=None)

class EditView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int, rate: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(EditChoice(ctx, index, result, rate))
        if index - pagelimit > -1:
            self.add_item(nextPageEdit(ctx, result, 0, "⏪", rate))
            self.add_item(nextPageEdit(ctx, result, index - pagelimit, "◀️", rate))
        if not last_index == len(result):
            self.add_item(nextPageEdit(ctx, result, last_index, "▶️", rate))
            max_page = get_max_page(len(result))
            self.add_item(nextPageEdit(ctx, result, max_page, "⏩", rate))
        self.add_item(CancelButton(ctx))

class nextPageEdit(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str, rate: int):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx, self.rate = result, index, ctx, rate
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = EditView(self.ctx, self.result, self.index, self.rate), 
                                                embed= edit_embed(self.ctx, self.result, self.index, 0x00ffff))

# database handling: slow?
def add_database(server_id: int):
    mycol.insert_one(
        {
            "guild": server_id,
            "admin_approval": False,
            "message_rate": 66,
            "channel_mode": True,
            "channels": [],
            "characters": [],
        }
    )
    return fetch_database(server_id)

def fetch_database(server_id: int) -> dict:
    return mycol.find_one({"guild":server_id})

def get_database(server_id: int):
    entry_exists = mycol.count_documents({"guild": server_id})
    if entry_exists > 0: return fetch_database(server_id)
    else: return add_database(server_id)

def push_character(server_id: int, data):
    mycol.update_one({"guild":server_id}, {"$push": {"characters": dict(data)}})

def pull_character(server_id: int, data):
    mycol.update_one({"guild":server_id}, {"$pull": {"characters": dict(data)}})

def push_chan(server_id: int, data):
    mycol.update_one({"guild":server_id}, {"$push": {"channels": data}})
    return True

def pull_chan(server_id: int, data):
    mycol.update_one({"guild":server_id}, {"$pull": {"channels": data}})
    return False

def toggle_chan(server_id: int, data):
    if not list(mycol.find({"guild":server_id, "channels": data})):
        return push_chan(server_id, data)
    else: 
        return pull_chan(server_id, data)
    
def push_ad(server_id: int):
    mycol.update_one({"guild":server_id}, {"$set": {"admin_approval": True}})

def pull_ad(server_id: int):
    mycol.update_one({"guild":server_id}, {"$set": {"admin_approval": False}})

def push_mode(server_id: int):
    mycol.update_one({"guild":server_id}, {"$set": {"channel_mode": True}})

def pull_mode(server_id: int):
    mycol.update_one({"guild":server_id}, {"$set": {"channel_mode": False}})

def push_rate(server_id: int, value: int):
    mycol.update_one({"guild":server_id}, {"$set": {"message_rate": value}})

# webhook handling (ugly but safe)
def push_webhook(server_id: int, c_data, w_data):
    if not c_data.get("webhooks"): 
        c_data["webhooks"] = []
    c_data["webhooks"].append(w_data)
    push_character(server_id, c_data)

async def get_webhook(ctx: commands.Context, c_data):
    test = await asyncio.to_thread(mycol.find_one, {"guild":ctx.guild.id})
    chars = test["characters"]
    wh, ch = None, None
    for x in chars:
        if x["name"] == c_data["name"]:
            if not x.get("webhooks"): break # malform fix
            for w in list(x["webhooks"]):
                parent = ctx.channel
                if type(parent) == discord.Thread:
                    parent = parent.parent
                if w["channel"] == parent.id:
                    url = w["url"]
                    if await webhook_exists(url):
                        wh = discord.Webhook.from_url(url, client=ctx.bot)
                        break
                    else: 
                        ch = x
                        x["webhooks"].remove(w)

    # silent delete
    if ch:
        await asyncio.to_thread(pull_character, ctx.guild.id, c_data)
        await asyncio.to_thread(push_character, ctx.guild.id, ch)
    if wh: return wh

    # create webhook?
    parent = ctx.channel
    threads = []
    if type(parent) == discord.Thread:
        parent = parent.parent
        threads = [{"id": ctx.channel.id, "rate": 100}]
    whs = await parent.webhooks()
    if len(whs) == 15: return None
    wh = await parent.create_webhook(name=c_data["name"], avatar=c_data["avatar"])
    await asyncio.to_thread(pull_character, ctx.guild.id, c_data)
    await asyncio.to_thread(push_webhook, ctx.guild.id, c_data, {
        "channel": ctx.channel.id, "url": wh.url, "char_message_rate": 100, "threads": threads})
    return wh

async def delete_webhooks(ctx: commands.Context, c_data):
    test = await asyncio.to_thread(mycol.find_one, {"guild":ctx.guild.id})
    chars = test["characters"]
    for x in chars:
        if x["name"] == c_data["name"]:
            channels = ctx.guild.channels
            for chan in channels:
                if not type(chan) in supported: continue
                perms = chan.permissions_for(ctx.guild.me)
                if perms.manage_webhooks:
                    whs = await chan.webhooks()
                    for w in whs:
                        if w.name == c_data["name"]:
                            await w.delete()

# role handling
async def create_role(ctx: commands.Context, name: str) -> discord.Role:
    return await ctx.guild.create_role(name=name, color=0x00ff00, mentionable=True)

async def delete_role(role: discord.Role):
    await role.delete()

def fetch_role(ctx: commands.Context, id: int) -> discord.Role:
    return ctx.guild.get_role(id)

# thread webhook hack, unused
class WebhookSender:
    def __init__(self, url):
        self.url = url

    async def send(self, text):
        async with aiohttp.ClientSession() as session:
            payload = {
                "content": text
            }
            headers = {
                "Content-Type": "application/json"
            }
            async with session.post(self.url, json=payload, headers=headers) as response:
                if not response.status == 204:
                    print("webhook thread hack error")