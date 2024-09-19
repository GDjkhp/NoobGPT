import discord
from discord.ext import commands
from discord import app_commands
from character_ai import PyAsyncCAI
import asyncio
import aiohttp
import random
import re
from collections import defaultdict
from typing import Dict
import time
import util_database
import os
from util_discord import command_check, check_if_master_or_admin as check, description_helper

mycol = util_database.myclient["ai"]["character"]
client = PyAsyncCAI(os.getenv('CHARACTER'))
list_types = ["search", "trending", "recommended"]
real_modes = ["basic", "nospace", "split", "snake"]
pagelimit=12
typing_chans = []
provider="https://gdjkhp.github.io/img/Character.AI.png"

# queue system
channel_queues: Dict[int, asyncio.Queue] = defaultdict(asyncio.Queue)
last_webhook_times: Dict[int, float] = defaultdict(float)
channel_tasks: Dict[int, asyncio.Task] = {}
async def c_ai_init(ctx: commands.Context):
    while True:
        try:
            if channel_queues[ctx.channel.id].empty():
                await asyncio.sleep(0.1)
                continue
            ctx, x, text = await channel_queues[ctx.channel.id].get() # updated ctx is required for message author
            permissions: discord.Permissions = ctx.channel.permissions_for(ctx.me)
            if not permissions.send_messages or not permissions.send_messages_in_threads: continue
            db = await get_database(ctx.guild.id)
            if db["channel_mode"] and not ctx.channel.id in db["channels"]: continue
            if db["message_rate"] == 0: continue
            # still alive?
            exist = False
            for char in db["characters"]:
                if x["name"] == char["name"]:
                    if get_rate(ctx, char) == 0: continue
                    exist = True
            if not exist: continue
            # webhook rate limiting
            current_time = time.time()
            time_since_last_webhook = current_time - last_webhook_times[ctx.channel.id]
            if time_since_last_webhook < 0.5:
                await asyncio.sleep(0.5 - time_since_last_webhook)
            # send the fucking message
            if ctx.channel.id in typing_chans:
                await send_webhook_message(ctx, x, text)
            else:
                typing_chans.append(ctx.channel.id)
                async with ctx.typing():
                    await send_webhook_message(ctx, x, text)
            last_webhook_times[ctx.channel.id] = time.time()
        except Exception as e: print(f"Exception in c_ai_init: {e}")
        try: 
            if ctx.channel.id in typing_chans: typing_chans.remove(ctx.channel.id)
        except: print("escaped the matrix bug triggered")

async def add_task_to_queue(ctx: commands.Context, x, text):
    await channel_queues[ctx.channel.id].put((ctx, x, text))
    if ctx.channel.id not in channel_tasks or channel_queues[ctx.channel.id].task_done():
        channel_tasks[ctx.channel.id] = ctx.bot.loop.create_task(c_ai_init(ctx))

async def queue_msgs(ctx, chars, clean_text):
    for x in chars:
        data = None
        try:
            data = await client.chat.send_message(x["history_id"], x["username"], clean_text)
            if data and data.get('replies'): await add_task_to_queue(ctx, x, data['replies'][0]['text'])
            else: print(data)
        except Exception as e: print(f"Exception in queue_msgs: {e}, data: {data}")

# the real
async def c_ai(bot: commands.Bot, msg: discord.Message):
    if not msg.guild: return
    if msg.author.id == bot.user.id: return
    if msg.content and msg.content[0] == "-": return # ignore commands
    # if msg.content == "": return # you can send blank messages
    ctx = await bot.get_context(msg) # context hack
    if await command_check(ctx, "c.ai", "ai"): return

    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles: return

    db = await get_database(ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: return
    if db["message_rate"] == 0: return

    # get character (lowercase mention, roles, reply)
    chars = []
    clean_text = replace_mentions(msg, bot)
    ref_msg = await msg.channel.fetch_message(msg.reference.message_id) if msg.reference else None

    # feat: character mentions
    if not db.get("mention_modes"):
        await push_mention(ctx.guild.id, "basic")
        await push_mention(ctx.guild.id, "nospace")
        db = await get_database(ctx.guild.id)

    for x in db["characters"]:
        if x in chars: continue
        if msg.author.name in x["name"]: continue
        if not generate_random_bool(get_rate(ctx, x)): continue
        if smart_str_compare(clean_text, x["name"], db["mention_modes"]) or (ref_msg and ref_msg.author.name in x["name"]):
            chars.append(x)

    if not chars:
        trigger = generate_random_bool(db["message_rate"])
        if trigger and db["characters"]:
            woke = []
            for x in db["characters"]:
                if msg.author.name in x["name"]: continue
                if not generate_random_bool(get_rate(ctx, x)): continue
                woke.append(x)
            if woke: chars.append(random.choice(woke))
    if not chars: return

    if ctx.channel.id in typing_chans:
        await queue_msgs(ctx, chars, clean_text)
    else:
        typing_chans.append(ctx.channel.id)
        async with ctx.typing(): await queue_msgs(ctx, chars, clean_text)

async def add_char(ctx: commands.Context, text: str, search_type: int):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    list_type = list_types[search_type]
    if search_type == 0: 
        if not text: return await ctx.reply("usage: `-cadd <query>`")
    else: text = list_type
    try:
        if len(text) >= 43: # char_id test
            res = await search_char_id(text)
        else: res = await search_char(text, list_type)
        if not res: return await ctx.reply("no results found")
        await ctx.reply(view=MyView4(ctx, text, res, 0), embed=search_embed(text, res, 0))
    except Exception as e:
        print(e)
        await ctx.reply("an error occured")

async def delete_char(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not db["characters"]: return await ctx.reply("no entries found")
    await ctx.reply(view=DeleteView(ctx, db["characters"], 0), embed=view_embed(ctx, db["characters"], 0, 0xff0000))

async def t_chan(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    ok = await toggle_chan(ctx.guild.id, ctx.channel.id)
    if ok: await ctx.reply("channel added to the list")
    else: await ctx.reply("channel removed from the list")

async def t_adm(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    await set_admin(ctx.guild.id, not db["admin_approval"])
    await ctx.reply(f'`admin approval` is now set to `{not db["admin_approval"]}`')

async def t_mode(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    await set_mode(ctx.guild.id, not db["channel_mode"])
    await ctx.reply(f'`channel mode` is now set to `{not db["channel_mode"]}`')

async def set_rate(ctx: commands.Context, num: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not num: return await ctx.reply("usage: `-crate <0-100>`")
    if not num.isdigit(): return await ctx.reply("not a digit")
    num = fix_num(num)
    await set_rate_db(ctx.guild.id, num)
    await ctx.reply(f"`message_rate` is now set to `{num}`")

async def view_char(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not db["characters"]: return await ctx.reply("no entries found")
    text = [
        f"message_rate: `{db['message_rate']}%`",
        f"channel_mode: `{db['channel_mode']}`",
        f"admin_approval: `{db['admin_approval']}`",
        f"mention_modes: `{db['mention_modes']}`" if db.get("mention_modes") else ""
    ]
    await ctx.reply(view=AvailView(ctx, db["characters"], 0), embed=view_embed(ctx, db["characters"], 0, 0x00ff00), content="\n".join(text))

async def edit_char(ctx: commands.Context, rate: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not rate: return await ctx.reply("usage: `-cedit <0-100>`")
    if not rate.isdigit(): return await ctx.reply("not a digit :(")
    rate = fix_num(rate)

    if not db["characters"]: return await ctx.reply("no entries found")
    await ctx.reply(view=EditView(ctx, db["characters"], 0, rate), 
                    embed=view_embed(ctx, db["characters"], 0, 0x00ffff))

async def reset_char(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")

    if not db["characters"]: return await ctx.reply("no entries found")
    await ctx.reply(view=ResetView(ctx, db["characters"], 0), 
                    embed=view_embed(ctx, db["characters"], 0, 0xff00ff))

async def set_mention_mode(ctx: commands.Context, modes: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "c.ai", "ai"): return
    # fucked up the perms again
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_webhooks or not permissions.manage_roles:
        return await ctx.reply("**manage webhooks and/or manage roles are disabled :(**")
    
    db = await get_database(ctx.guild.id)
    if db["admin_approval"] and not await check(ctx): return await ctx.reply("not a bot master or an admin")
    if db["channel_mode"] and not ctx.channel.id in db["channels"]: 
        return await ctx.reply("channel not found")
    
    if not modes:
        text = [
            "usage: `-cping <basic/nospace/split/snake>`",
            "basic: `yoko littner` -> `yoko littner`",
            "nospace: `hu tao` -> `hutao`",
            "split: `hatsune miku` -> `hatsune`, `miku`",
            "snake: `EricVanWilderman` -> `eric`, `van`, `wilderman`"
        ]
        return await ctx.reply("\n".join(text))

    modes = modes.split()
    for mode in list(modes):
        if mode in real_modes:
            if not mode in db["mention_modes"]: 
                await push_mention(ctx.guild.id, mode)
            else: await pull_mention(ctx.guild.id, mode)
    db = await get_database(ctx.guild.id)
    await ctx.reply(f"`mention_modes` is now set to `{db['mention_modes']}`")

async def c_help(ctx: commands.Context):
    if await command_check(ctx, "c.ai", "ai"): return
    text = [
        "# Character commands",
        "`-cchar` available characters",
        "`-cadd <query>` add character",
        "`-cdel` delete character",
        "`-cres` reset character",
        "`-ctren` trending characters",
        "`-crec` recommended characters",
        "# Server commands",
        "`-cchan` add/remove channel",
        "`-cadm` toggle admin approval",
        "`-cmode` toggle channel mode",
        "`-cping <basic/nospace/split/snake>` set mention mode",
        "`-crate <rate>` set global message_rate (0-100)",
        "`-cedit <rate>` set char_message_rate per channel (0-100)",
        "# Get started",
        "setup: `-cchan` -> `-cadd <query>`",
        "stop: `-crate 0`",
        "delete all chars: `-cdel` -> `💀`",
        "reset all chars: `-cres` -> `💀`",
        "set all char_message_rate: `-cedit <rate>` -> `💀`",
        "channel mode: `True` = read specific channels, `False` = read all channels",
        "admin approval: `True` = disables most commands, `False` = enables all commands",
        "you can also setup forums and threads per character with `-cchan` -> `-cedit 100`"
    ]
    await ctx.reply("\n".join(text))

# utils
async def mode_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in real_modes if current.lower() in mode.lower()
    ]

async def search_char(text: str, list_type: str):
    if list_type == "trending": 
        res = await client.character.trending()
        return res["trending_characters"]
    if list_type == "recommended":
        res = await client.character.recommended()
        return res["recommended_characters"]
    res = await client.character.search(text)
    return res["characters"]
async def search_char_id(text: str):
    chat = await client.chat.new_chat(text)
    return [
        {
            "external_id": text,
            "title": "⁉️",
            "avatar_file_name": chat["messages"][0]["src__character__avatar_file_name"],
            "participant__name": chat["messages"][0]["src__name"],
            "participant__num_interactions": -1,
            "user__username": chat["messages"][0]["src__user__username"],
        }
    ]
async def load_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return image_data
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def search_embed(arg: str, result: list, index: int):
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        char_name = f"[{i + 1}] `{result[i]['participant__name']}`"
        char_value = ""
        if result[i].get('title'): char_value += f"{result[i]['title']}\n"
        char_value += f"by `{result[i]['user__username']}`\n{format_number(int(result[i]['participant__num_interactions']))} chats"
        if (i < index+pagelimit): embed.add_field(name = char_name, value = char_value)
        i += 1
    return embed
def view_embed(ctx: commands.Context, result: list, index: int, col: int):
    embed = discord.Embed(title=ctx.guild, description=f"{len(result)} found", color=col)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        if (i < index+pagelimit): 
            char_title = f"[{i + 1}] `{result[i]['name']}`"
            char_desc = f"**{get_rate(ctx, result[i])}%**"
            if result[i].get('description'): char_desc += f"\n{result[i]['description']}"
            if result[i].get('author') and result[i].get('chats'): # another fuck up
                char_desc += f"\nby `{result[i]['author']}`\n{format_number(result[i]['chats'])} chats"
            embed.add_field(name = char_title, value = char_desc)
        i += 1
    return embed
def generate_random_bool(num):
    chance = num / 100 # convert number to probability
    result = random.random()
    return result < chance
def clean_gdjkhp(o: str, n: str):
    o = o.replace("gdjkhp", n)
    o = o.replace("GDJKHP", n.upper())
    return o
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
    async with aiohttp.ClientSession() as session:
        async with session.head(webhook_url) as response:
            return response.status == 200
async def send_webhook_message(ctx: commands.Context, x, text):
    wh = await get_webhook(ctx, x)
    if wh:
        if type(ctx.channel) == discord.Thread:
            await wh.send(clean_gdjkhp(text, ctx.author.name), thread=ctx.channel)
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
def smart_str_compare(text: str, char: str, modes: list):
    text_lower, char_lower = text.lower(), char.lower()
    if "basic" in modes:
        if char_lower in text_lower: return True # yoko littner -> yoko littner
    if "nospace" in modes:
        no_space_char = re.sub(r'[^a-zA-Z0-9]', '', char_lower)
        if no_space_char in text_lower: return True # hu tao -> hutao
    if "split" in modes:
        remove_symbols_text = re.sub(r'[^a-zA-Z0-9\s]', '', text_lower)
        char_splits = char_lower.split()
        for x in char_splits:
            for y in remove_symbols_text.split():
                if x == y: return True # hatsune miku -> hatsune, miku
    if "snake" in modes:
        snake_splits = snake(char)
        for x in snake_splits:
            for y in remove_symbols_text.split():
                if x == y: return True # [EricVanWilderman -> eric, van, wilderman] [Kizuna AI -> kizuna, a, i]
def fix_num(num):
    num = int(num)
    if num < 0: num = 0
    elif num > 100: num = 100
    return num
def get_rate(ctx: commands.Context, x):
    if not x.get("webhooks"): return 0 # malform fix
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
def format_number(num):
    if 1000 <= num < 1000000:
        return f"{num / 1000:.1f}k"
    elif 1000000 <= num < 1000000000:
        return f"{num / 1000000:.1f}m"
    elif 1000000000 <= num < 1000000000000:
        return f"{num / 1000000000:.1f}b"
    else:
        return str(num)

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

        await interaction.message.edit(content=f'adding `{selected["participant__name"]}`', embed=None, view=None)
        await interaction.response.defer()
        
        chat = None
        try:
            chat = await client.chat.new_chat(selected["external_id"])
        except Exception as e: print(e)
        if not chat or not chat.get('participants'): 
            print(chat)
            return await interaction.message.edit(content="an error occured")
        
        tgt = None
        for participant in chat['participants']:
            if not participant['is_human']:
                tgt = participant['user']['username']
                break
        if not tgt:
            print(chat['participants'])
            return await interaction.message.edit(content="tgt not found")

        # proper checking
        db = await get_database(self.ctx.guild.id)
        if db.get("characters"):
            found = False
            for x in db["characters"]:
                if x["username"] == tgt: found = True
            if found:
                return await interaction.message.edit(content=f"`{selected['participant__name']}` was already in chat")

        # thread support
        parent = self.ctx.channel
        threads = []
        if type(parent) == discord.Thread:
            parent = parent.parent
            threads = [{"id": self.ctx.channel.id, "rate": 100}]

        whs = await parent.webhooks()
        if len(whs) == 15: return await interaction.message.edit(content="webhook limit reached, please delete at least one")
        url = "https://cdn.discordapp.com/embed/avatars/4.png"
        if selected['avatar_file_name']:
            url = f"https://characterai.io/i/400/static/avatars/{selected['avatar_file_name']}"
        img = await load_image(url)
        wh = await parent.create_webhook(name=selected["participant__name"], avatar=img)
        role = await self.ctx.guild.create_role(name=selected["participant__name"], color=0x00ff00, mentionable=True)
        data = character_data(selected, tgt, chat, role, img, parent, wh, threads)
        await push_character(self.ctx.guild.id, data)
        await interaction.message.edit(content=f"`{selected['participant__name']}` has been added to the server")
        await add_task_to_queue(self.ctx, data, chat["messages"][0]["text"]) # wake up

class MyView4(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(ctx, arg, result, 0, "⏪"))
            self.add_item(nextPage(ctx, arg, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪"))
            self.add_item(DisabledButton("◀️"))
        if not last_index == len(result):
            self.add_item(nextPage(ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(ctx, arg, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️"))
            self.add_item(DisabledButton("⏩"))
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

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True)
        
class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, row: int=None):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success, row=row)
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.delete()

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

        await interaction.message.edit(content=f'deleting `{selected["name"]}`', embed=None, view=None)
        await interaction.response.defer()
        await delete_method(self.ctx, selected)
        await interaction.message.edit(content=f"`{selected['name']}` has been deleted from the server")

class DeleteAllButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, row: int=None):
        super().__init__(emoji="💀", style=discord.ButtonStyle.success, row=row)
        self.ctx, self.result = ctx, result
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(content='deleting', view=None, embed=None)
        await interaction.response.defer()
        count = 0
        for selected in self.result:
            count+=1
            await interaction.message.edit(content=f'deleting `{selected["name"]}`\n{count}/{len(self.result)}')
            await delete_method(self.ctx, selected)
        await interaction.message.edit(content=f"`{count}` characters have been deleted from the server")

class ResetAllButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, row: int=None):
        super().__init__(emoji="💀", style=discord.ButtonStyle.success, row=row)
        self.ctx, self.result = ctx, result
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(content='resetting', view=None, embed=None)
        await interaction.response.defer()
        errors = []
        count = 0
        for selected in self.result:
            count+=1
            e_strs = "\n".join(errors)
            await interaction.message.edit(content=f'resetting `{selected["name"]}`\n{count}/{len(self.result)}\n{e_strs}')
            if not selected.get("char_id"):
                count -= 1
                errors.append(f"`char_id` not found. please re-add `{selected['name']}` with `-cdel` and `-cadd`")
                continue
            
            chat = None
            try:
                chat = await client.chat.new_chat(selected["char_id"])
            except Exception as e: print(e)
            if not chat or not chat.get('participants'):
                count -= 1
                print(chat)
                errors.append(f"an error occured resetting `{selected['name']}`")
                continue

            await reset_method(self.ctx, selected, chat)
        e_strs = "\n".join(errors)
        await interaction.message.edit(content=f'`{count}/{len(self.result)}` characters have been reset from the server\n{e_strs}')

class EditAllButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, rate: int, row: int=None):
        super().__init__(emoji="💀", style=discord.ButtonStyle.success, row=row)
        self.ctx, self.result, self.rate = ctx, result, rate
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.message.edit(content='setting', view=None, embed=None)
        await interaction.response.defer()
        errors = []
        count = 0
        for selected in self.result:
            count+=1
            e_strs = "\n".join(errors)
            await interaction.message.edit(content=f'setting `{selected["name"]}` char_message_rate to `{self.rate}`\n{count}/{len(self.result)}\n{e_strs}')

            if not selected.get("webhooks"): # old
                await pull_character(self.ctx.guild.id, selected)
                selected["webhooks"] = []
                await push_character(self.ctx.guild.id, selected)

            found = False
            for w in selected["webhooks"]:
                parent = self.ctx.channel
                if type(parent) == discord.Thread:
                    parent = parent.parent
                if w["channel"] == parent.id:
                    if await webhook_exists(w["url"]):
                        found = True
                        await edit_method(self.ctx, selected, w, self.rate)
                        break
            if not found:
                count -= 1
                errors.append(f"`{selected['name']}` webhook not found")
        e_strs = "\n".join(errors)
        await interaction.message.edit(content=f'`{count}/{len(self.result)}` characters have been edited from the server\n{e_strs}')

async def delete_method(ctx: commands.Context, selected):
    role = ctx.guild.get_role(selected["role_id"])
    if role: await role.delete()
    await delete_webhooks(ctx, selected)
    await pull_character(ctx.guild.id, selected)

async def reset_method(ctx: commands.Context, selected, chat):
    await pull_character(ctx.guild.id, selected)
    selected["history_id"] = chat["external_id"]
    await push_character(ctx.guild.id, selected)

async def edit_method(ctx: commands.Context, selected, w, rate):
    await pull_character(ctx.guild.id, selected)
    if type(ctx.channel) == discord.Thread:
        if not w.get("threads"): w["threads"] = []
        w["threads"].append({"id": ctx.channel.id, "rate": rate})
    else:
        w["char_message_rate"] = rate
    await push_character(ctx.guild.id, selected)

class DeleteView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(DeleteChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPageDelete(ctx, result, 0, "⏪"))
            self.add_item(nextPageDelete(ctx, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪"))
            self.add_item(DisabledButton("◀️"))
        if not last_index == len(result):
            self.add_item(nextPageDelete(ctx, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPageDelete(ctx, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️"))
            self.add_item(DisabledButton("⏩"))
        self.add_item(DeleteAllButton(ctx, result, 2))
        self.add_item(CancelButton(ctx, 2))

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
        else:
            self.add_item(DisabledButton("⏪"))
            self.add_item(DisabledButton("◀️"))
        if not last_index == len(result):
            self.add_item(nextPageAvail(ctx, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPageAvail(ctx, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️"))
            self.add_item(DisabledButton("⏩"))
        self.add_item(CancelButton(ctx))

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

        await interaction.message.edit(content=f'setting `{selected["name"]}` char_message_rate to `{self.rate}`', embed=None, view=None)
        await interaction.response.defer()

        if not selected.get("webhooks"): # old
            await pull_character(self.ctx.guild.id, selected)
            selected["webhooks"] = []
            await push_character(self.ctx.guild.id, selected)

        found = False
        mod_webhooks = list(selected["webhooks"])
        for w in selected["webhooks"]:
            parent = self.ctx.channel
            if type(parent) == discord.Thread:
                parent = parent.parent
            if w["channel"] == parent.id:
                if await webhook_exists(w["url"]):
                    found = True
                    await edit_method(self.ctx, selected, w, self.rate)
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
                return await interaction.message.edit(content="webhook limit reached, please delete at least one")
            wh = await parent.create_webhook(name=selected["name"], avatar=selected["avatar"])
            await pull_character(self.ctx.guild.id, selected)
            selected["webhooks"] = mod_webhooks # malform fix
            await push_webhook(self.ctx.guild.id, selected, {
                "channel": parent.id, "url": wh.url, "char_message_rate": self.rate, "threads": threads})

        await interaction.message.edit(content=f"`{selected['name']}` char_message_rate is now set to `{self.rate}` on this channel")

class EditView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int, rate: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(EditChoice(ctx, index, result, rate))
        if index - pagelimit > -1:
            self.add_item(nextPageEdit(ctx, result, 0, "⏪", rate))
            self.add_item(nextPageEdit(ctx, result, index - pagelimit, "◀️", rate))
        else:
            self.add_item(DisabledButton("⏪"))
            self.add_item(DisabledButton("◀️"))
        if not last_index == len(result):
            self.add_item(nextPageEdit(ctx, result, last_index, "▶️", rate))
            max_page = get_max_page(len(result))
            self.add_item(nextPageEdit(ctx, result, max_page, "⏩", rate))
        else:
            self.add_item(DisabledButton("▶️"))
            self.add_item(DisabledButton("⏩"))
        self.add_item(EditAllButton(ctx, result, rate, 2))
        self.add_item(CancelButton(ctx, 2))

class nextPageEdit(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str, rate: int):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx, self.rate = result, index, ctx, rate
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = EditView(self.ctx, self.result, self.index, self.rate), 
                                                embed= view_embed(self.ctx, self.result, self.index, 0x00ffff))

class ResetView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(ResetChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPageReset(ctx, result, 0, "⏪"))
            self.add_item(nextPageReset(ctx, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪"))
            self.add_item(DisabledButton("◀️"))
        if not last_index == len(result):
            self.add_item(nextPageReset(ctx, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPageReset(ctx, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️"))
            self.add_item(DisabledButton("⏩"))
        self.add_item(ResetAllButton(ctx, result, 2))
        self.add_item(CancelButton(ctx, 2))

class nextPageReset(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.ctx = result, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = ResetView(self.ctx, self.result, self.index), 
                                                embed= view_embed(self.ctx, self.result, self.index, 0xff00ff))
        
class ResetChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
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

        await interaction.message.edit(content=f'resetting `{selected["name"]}`', embed=None, view=None)
        await interaction.response.defer()

        if not selected.get("char_id"):
            return await interaction.message.edit(content=f"`char_id` not found. please re-add `{selected['name']}` with `-cdel` and `-cadd`")
        chat = None
        try:
            chat = await client.chat.new_chat(selected["char_id"])
        except Exception as e: print(e)
        if not chat or not chat.get('participants'):
            print(chat)
            return await interaction.message.edit(content="an error occured")

        await reset_method(self.ctx, selected, chat)
        await interaction.message.edit(content=f"`{selected['name']}` has been reset")
        await add_task_to_queue(self.ctx, selected, chat["messages"][0]["text"]) # wake up

# database handling
async def add_database(server_id: int):
    data = {
        "guild": server_id,
        "admin_approval": False,
        "message_rate": 66,
        "channel_mode": True,
        "mention_modes": [],
        "channels": [],
        "characters": [],
    }
    await mycol.insert_one(data)
    return data

async def fetch_database(server_id: int):
    return await mycol.find_one({"guild":server_id})

async def get_database(server_id: int):
    db = await fetch_database(server_id)
    if db: return db
    return await add_database(server_id)

def character_data(selected, tgt, chat, role: discord.Role, img, parent: discord.TextChannel, wh: discord.Webhook, threads):
    return {
        "name": selected["participant__name"],
        "description": selected['title'],
        "author": selected['user__username'],
        "chats": int(selected['participant__num_interactions']),
        "username": tgt,
        "char_id": selected['external_id'], # mistake again
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

async def push_character(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"characters": dict(data)}})

async def pull_character(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"characters": dict(data)}})

async def push_chan(server_id: int, chan_id):
    await mycol.update_one({"guild":server_id}, {"$push": {"channels": chan_id}})
    return True

async def pull_chan(server_id: int, chan_id):
    await mycol.update_one({"guild":server_id}, {"$pull": {"channels": chan_id}})
    return False

async def toggle_chan(server_id: int, chan_id):
    if await mycol.find_one({"guild":server_id, "channels": chan_id}):
        return await pull_chan(server_id, chan_id)
    return await push_chan(server_id, chan_id)
    
async def set_admin(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"admin_approval": b}})

async def set_mode(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"channel_mode": b}})

async def set_rate_db(server_id: int, value: int):
    await mycol.update_one({"guild":server_id}, {"$set": {"message_rate": value}})

async def push_mention(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"mention_modes": data}})

async def pull_mention(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"mention_modes": data}})

# webhook handling (ugly but safe)
async def push_webhook(server_id: int, c_data, w_data):
    if not c_data.get("webhooks"): 
        c_data["webhooks"] = []
    c_data["webhooks"].append(w_data)
    await push_character(server_id, c_data)

async def get_webhook(ctx: commands.Context, c_data):
    wh, mod_webhooks, silent_delete = None, None, False
    if c_data.get("webhooks"): # malform fix
        mod_webhooks = list(c_data["webhooks"])
        for w in c_data["webhooks"]:
            parent = ctx.channel
            if type(parent) == discord.Thread:
                parent = parent.parent
            if w["channel"] == parent.id:
                if await webhook_exists(w["url"]):
                    wh = discord.Webhook.from_url(w["url"], client=ctx.bot)
                    break
                else: 
                    silent_delete = True
                    mod_webhooks.remove(w)

    if silent_delete:
        await pull_character(ctx.guild.id, c_data)
        c_data["webhooks"] = mod_webhooks
        await push_character(ctx.guild.id, c_data)
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
    await pull_character(ctx.guild.id, c_data)
    await push_webhook(ctx.guild.id, c_data, {
        "channel": parent.id, "url": wh.url, "char_message_rate": 100, "threads": threads})
    return wh

async def delete_webhooks(ctx: commands.Context, c_data):
    if not c_data.get("webhooks"): return # malform fix
    for w in c_data["webhooks"]:
        if await webhook_exists(w["url"]):
            wh = discord.Webhook.from_url(w["url"], client=ctx.bot)
            await wh.delete()

class CogCAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} add character")
    @app_commands.describe(query="Search query")
    async def cadd(self, ctx: commands.Context, *, query:str=None):
        await add_char(ctx, query, 0)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} recommended characters")
    async def crec(self, ctx: commands.Context):
        await add_char(ctx, None, 2)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} trending characters")
    async def ctren(self, ctx: commands.Context):
        await add_char(ctx, None, 1)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} delete character")
    async def cdel(self, ctx: commands.Context):
        await delete_char(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} toggle admin approval")
    async def cadm(self, ctx: commands.Context):
        await t_adm(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} add/remove channel")
    async def cchan(self, ctx: commands.Context):
        await t_chan(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} set global message_rate")
    @app_commands.describe(rate="Set global message rate (Must be a valid integer: 0-100)")
    async def crate(self, ctx: commands.Context, *, rate:str=None):
        await set_rate(ctx, rate)

    @commands.command(aliases=["c.ai"])
    async def chelp(self, ctx: commands.Context):
        await c_help(ctx)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["ai"]} {description_helper["ai"]["cai"]}'[:100])
    async def cai(self, ctx: commands.Context):
        await c_help(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} toggle channel mode")
    async def cmode(self, ctx: commands.Context):
        await t_mode(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} available characters")
    async def cchar(self, ctx: commands.Context):
        await view_char(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} set char_message_rate per channel")
    @app_commands.describe(rate="Set character message rate per channel (Must be a valid integer: 0-100)")
    async def cedit(self, ctx: commands.Context, rate:str=None):
        await edit_char(ctx, rate)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} reset character")
    async def cres(self, ctx: commands.Context):
        await reset_char(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['cai']} set mention mode")
    @app_commands.autocomplete(mode=mode_auto)
    @app_commands.describe(mode="Set mention mode")
    async def cping(self, ctx: commands.Context, *, mode:str=None):
        await set_mention_mode(ctx, mode)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogCAI(bot))