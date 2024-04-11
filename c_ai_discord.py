import discord
from discord.ext import commands
from  character_ai import PyAsyncCAI
import asyncio
import os
import pymongo
import aiohttp
import random

myclient = pymongo.MongoClient(os.getenv('MONGO'))
mycol = myclient["ai"]["character"]
client = PyAsyncCAI(os.getenv('CHARACTER'))
pagelimit=12

async def c_ai(bot: commands.Bot, msg: discord.Message, char: list = None):
    if msg.author.id == bot.user.id: return
    ctx = await bot.get_context(msg) # context hack

    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return

    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return

    # get character (roles, reply, lowercase mention)
    chars = [] if not char else char
    clean_text = clean_message(msg)
    for x in db["characters"]:
        if x["name"].lower() in clean_text.lower(): 
            chars.append(x)
    if msg.reference:
        ref_msg = await msg.channel.fetch_message(msg.reference.message_id)
        for x in db["characters"]:
            if x["name"] == ref_msg.author.name: chars.append(x)
    if not chars: return
    
    async with ctx.typing():
        for x in chars:
            if x["name"] == msg.author.name: continue
            data = await client.chat.send_message(
                x["history_id"], x["username"], clean_text
            )
            wh = await get_webhook(ctx.channel)
            wh = await update_webhook(wh, x["name"], x["avatar"])
            await wh.send(data['replies'][0]['text'])
            await reset_webhook(wh)

async def random_msg(bot: commands.Bot, msg: discord.Message):
    if msg.author.id == bot.user.id: return
    ctx = await bot.get_context(msg) # context hack

    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return

    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return
    
    trigger = generate_random_bool(db["message_rate"])
    if trigger and db["characters"]:
        # print("random get")
        random.shuffle(db["characters"])
        pick_one = [db["characters"][0]]
        await c_ai(bot, msg, pick_one)

async def add_char(ctx: commands.Context, text: str):
    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    if not text: return await ctx.reply("?")
    async with ctx.typing():
        res = await search_char(text)
        if not res["characters"]: return await ctx.reply("no results found")
        await ctx.reply(view=MyView4(ctx, text, res["characters"], 0), embed=search_embed(text, res["characters"], 0))

async def delete_char(ctx: commands.Context):
    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    async with ctx.typing():
        if not db["characters"]: return await ctx.reply("no entries found")
        await ctx.reply(view=DeleteView(ctx, db["characters"], 0), embed=delete_embed(ctx.guild, db["characters"], 0))

async def t_chan(ctx: commands.Context):
    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await asyncio.to_thread(get_database, ctx.guild.id)
    if db["admin_approval"] and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    ok = await asyncio.to_thread(toggle_chan, ctx.guild.id, ctx.channel.id)
    if ok: await ctx.reply("channel added to the list")
    else: await ctx.reply("channel removed from the list")

async def t_adm(ctx: commands.Context):
    # fucked up the perms again
    permissions = ctx.guild.me.guild_permissions
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

async def set_rate(ctx: commands.Context, num):
    if not num: return await ctx.reply("?")
    if not num.isdigit(): return await ctx.reply("not a digit")
    num = int(num)
    if num < 0:
        num = 0
    elif num > 100:
        num = 100
    await asyncio.to_thread(push_rate, ctx.guild.id, num)
    await ctx.reply(f"message_rate set to {num}")

async def c_help(ctx: commands.Context):
    text = "Character.ai is an American neural language model chatbot service that can generate human-like text responses and participate in contextual conversation."
    text += "\n\nAvailable commands:"
    text += "\n`-cadd <query>` add a character"
    text += "\n`-cdel` delete a character"
    text += "\n`-cchan` add channel"
    text += "\n`-cadm` toggle admin approval"
    text += "\n`-crate <int>` set random message rate (0-100)"
    await ctx.reply(text)

# utils
async def load_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return image_data
            else:
                raise OSError(f"Failed to load image from URL: {url}")
async def search_char(text: str):
    return await client.character.search(text)
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
def delete_embed(arg: str, result: list, index: int):
    embed = discord.Embed(title=arg, description=f"{len(result)} found", color=0xff0000)
    i = index
    while i < len(result):
        if (i < index+pagelimit): 
            embed.add_field(name=f"[{i + 1}] {result[i]['name']}", value=result[i]['description'])
        i += 1
    return embed
def generate_random_bool(num):
    chance = num / 100 # convert number to probability
    result = random.random() 
    # print(result)
    return result < chance
def clean_gdjkhp(o: str, n: str):
    return o.replace("GDjkhp", n)
def replace_mentions(message: discord.Message):
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
    return content
def clean_message(message: discord.Message) -> str:
    text = replace_mentions(message)
    return clean_gdjkhp(text, message.author.name)

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): 
                self.add_option(label=f"[{i + 1}] {result[i]['participant__name']}", value=i, description=f"{result[i]['title']}")
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
            
        chat = await client.chat.new_chat(selected["external_id"])
        participants = chat['participants']
        if not participants[0]['is_human']:
            tgt = participants[0]['user']['username']
        else:
            tgt = participants[1]['user']['username']

        role = await create_role(self.ctx, selected["participant__name"])
        
        img = await load_image(f"https://characterai.io/i/80/static/avatars/{selected['avatar_file_name']}")
        data = {
            "name": selected["participant__name"],
            "description": selected['title'],
            "username": tgt,
            "history_id": chat["external_id"],
            "role_id": role.id,
            "avatar": img
        }

        await asyncio.to_thread(push_database, self.ctx.guild.id, data)

        await interaction.message.edit(content=f"{selected['participant__name']} has been added to the server", embed=None, view=None)

        wh = await get_webhook(self.ctx.channel)
        wh = await update_webhook(wh, data["name"], data["avatar"])
        await wh.send(chat["messages"][0]["text"])
        await reset_webhook(wh)

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

class DeleteChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): 
                self.add_option(label=f"[{i + 1}] {result[i]['name']}", value=i)
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
        await delete_role(role)

        await asyncio.to_thread(pull_database, self.ctx.guild.id, selected)
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

class nextPageDelete(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx = result, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = DeleteView(self.ctx, self.result, self.index), 
                                                embed= delete_embed(self.ctx.guild, self.result, self.index))

# database handling: slow?
def add_database(server_id: int):
    mycol.insert_one(
        {
            "guild": server_id,
            "admin_approval": False,
            "message_rate": 66,
            "channel_mode": True,
            "channels": [],
            "characters": []
        }
    )

def fetch_database(server_id: int) -> dict:
    return mycol.find_one({"guild":server_id})

def get_database(server_id: int):
    if not list(mycol.find({"guild":server_id})):
        add_database(server_id)
    return fetch_database(server_id)

def push_database(server_id: int, data):
    mycol.update_one({"guild":server_id}, {"$push": {"characters": dict(data)}})

def pull_database(server_id: int, data):
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

# role handling
async def create_role(ctx: commands.Context, name: str) -> discord.Role:
    return await ctx.guild.create_role(name=name, color=0x00ff00, mentionable=True)

async def delete_role(role: discord.Role):
    await role.delete()

def fetch_role(ctx: commands.Context, id: int) -> discord.Role:
    return ctx.guild.get_role(id)

# webhook handling
async def fetch_webhook(channel: discord.TextChannel) -> discord.Webhook:
    webhooks = await channel.webhooks()
    for x in webhooks:
        if x.name == 'NoobGPT':
            return x
    return None

async def create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    return await channel.create_webhook(name='NoobGPT')

async def update_webhook(webhook: discord.Webhook, name: str, av: str):
    return await webhook.edit(name=name, avatar=av)

async def reset_webhook(webhook: discord.Webhook):
    return await webhook.edit(name="NoobGPT", avatar=None)

async def get_webhook(channel: discord.TextChannel):
    wh = await fetch_webhook(channel)
    if not wh: wh = await create_webhook(channel)
    return wh