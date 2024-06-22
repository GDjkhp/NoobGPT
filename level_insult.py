import discord
from discord.ext import commands
import json
import time
import random
import re
import util_database
from util_discord import command_check

mycol = util_database.myclient["utils"]["nodeports"]
path="./res/mandatory_settings_and_splashes.json"

# noobgpt sucks without insults they said
async def detect_mentions(message: discord.Message, bot: commands.Bot):
    if message.mentions:
        if bot.user in message.mentions: return True
    ref_msg = await message.channel.fetch_message(message.reference.message_id) if message.reference else None
    if ref_msg and ref_msg.author == bot.user: return True

async def insult_user(bot: commands.Bot, msg: discord.Message):
    db = await get_database(msg.guild.id if msg.guild else msg.channel.id)
    if not db["insult_module"]: return

    if await detect_mentions(msg, bot):
        ctx = await bot.get_context(msg) # context hack
        async with ctx.typing():
            text = random.choice(read_json_file(path)["insults from thoughtcatalog.com"])
            await msg.reply(text)

# noobgpt sucks without leveling system they said
async def earn_xp(msg: discord.Message):
    if not msg.guild: return
    if msg.author.bot: return
    if msg.content and msg.content[0] == "-": return # ignore commands
    db = await get_database(msg.guild.id)
    if not db["xp_module"]: return
    if db["xp_channel_mode"] and not msg.channel.id in db["channels"]: return

    fake_roles = get_member_roles(msg.author, db['xp_roles'])
    if check_member_if_xp_restricted(fake_roles): return
    multipliers = get_all_multipliers(fake_roles, db["xp_rate"])
    xp = int(random.randint(15, 25) * multipliers)
    now = time.time()
    for data in db["players"]:
        if data["userID"] == msg.author.id:
            cooldown, role_id = get_lowest_cooldown(fake_roles, db['xp_cooldown'])
            if not now - data["lastUpdated"] >= cooldown: return
            await pull_player(msg.guild.id, data)
            data["xp"] += xp
            data["msgs"] += 1
            data["lastUpdated"] = now
            if loop_level(data):
                json_data = read_json_file(path)
                text: str = random.choice(json_data["level up loser"]) if db["xp_troll"] else json_data["mee6 default"]
                user_data = {"name": f"<@{msg.author.id}>", "level": data["level"]}
                await msg.channel.send(text.format_map(user_data))
            await push_player(msg.guild.id, data)
            return
    await push_player(msg.guild.id, player_data(xp, msg.author.id, now)) # not found

# noobgpt sucks without custom prefix they said
async def get_prefix(bot: commands.Bot, message: discord.Message):
    db = await get_database(message.guild.id if message.guild else message.channel.id)
    return commands.when_mentioned_or(db['prefix'])(bot, message)

# commands
async def set_prefix_cmd(ctx: commands.Context, arg: str):
    if await command_check(ctx, "prefix", "utils"): return
    if ctx.guild and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if not arg: return await ctx.reply("usage: `-prefix <prefix>`")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id) # nonsense
    await set_prefix(ctx.guild.id, arg)
    await ctx.reply(f"prefix has been set to `{arg}`")

async def toggle_insult(ctx: commands.Context):
    if await command_check(ctx, "insult", "utils"): return
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
    b = not db["insult_module"]
    await set_insult(ctx.guild.id, b)
    await ctx.reply(f"`insult_module` is set to `{b}`")

async def toggle_xp(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    db = await get_database(ctx.guild.id)
    b = not db["xp_module"]
    await set_xp(ctx.guild.id, b)
    await ctx.reply(f"`xp_module` is set to `{b}`")

async def user_rank(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return
    if not arg: arg = ctx.author.id
    elif not arg.isdigit(): return await ctx.reply("not a digit :(\nusage: `-rank <userid>`")
    for player in db['players']:
        if player['userID'] == int(arg):
            fake_roles = get_member_roles(ctx.author, db['xp_roles'])
            cooldown, role_id = get_lowest_cooldown(fake_roles, db['xp_cooldown'])
            return await ctx.reply(embed=embed_xp(ctx.author, player, fake_roles, cooldown, role_id, db['xp_rate']))
    await ctx.reply("null player")

async def guild_lead(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return
    await ctx.reply("under construction") # TODO: query sorting first n players from highest to lowest xp, such bs

# TODO: view and delete lvlmsgs, insults (use UpdateResult)
async def add_insult(ctx: commands.Context, arg: str):
    if not arg: return await ctx.reply("usage: `-insultadd <str>`")
    await push_insult(ctx.guild.id, arg)
    await ctx.reply("insult added. use `-insultview` to list all insults.")

async def add_lvl_msg(ctx: commands.Context, arg: str):
    if not arg: return await ctx.reply(f"usage: `-lvlmsgadd <str>`\nformat: {read_json_file(path)['mee6 default']}")
    await push_xp_msg(ctx.guild.id, arg)
    await ctx.reply("levelup msg added. use `-lvlmsgview` to list all levelup msgs.")

async def add_xp_role(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")

    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")

    if not arg or not arg.isdigit():
        return await ctx.reply("usage: -xprole <level>\nparameters:\n`-1` = restricted, `0` = none, `1, 2, ...` = levels")
    
    role = await ctx.guild.create_role(name="Level "+arg if int(arg) > 0 else "special role", mentionable=False)
    await push_role(ctx.guild.id, role_data(role.id, int(arg)))
    await ctx.reply(f"<@&{role.id}> has been created. edit attributes using `-xproleedit <roleid>`, `name` and `color` in server settings.")

async def edit_xp_role(ctx: commands.Context, role_id: str, keep: str, multiplier: str, cooldown: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    if not role_id or not role_id.isdigit():
        return await ctx.reply("usage: -xproleedit <roleid>")
    
    db = await get_database(ctx.guild.id)
    for role in db["xp_roles"]:
        if role["role_id"] == role_id:
            real_role = ctx.guild.get_role(role_id)
            if not real_role:
                await pull_role(ctx.guild.id, role)
                return await ctx.reply("`real_role` not found. removed from database.")
            if keep and keep.isdigit():
                keep = True if int(keep) else False
            else: return await ctx.reply("`keep` not found. please enter `0` for no or `1` for yes")

            if not multiplier: multiplier = role['role_multiplier'] # maintain -1 for none
            else:
                mulx = extract_number(multiplier) # TODO: does this support negatives?
                if not mulx: return await ctx.reply("`multiplier` not found. please enter in `1.75x` or `1` format.")
                multiplier = mulx

            if not cooldown: cooldown = role['role_cooldown'] # maintain -1 for none
            else:
                if not cooldown.isdigit(): return await ctx.reply("`cooldown` not found. please enter a valid integer.")
                cooldown = int(cooldown)

            role_update = role_data(role_id, role['level'])
            role_update['role_keep'] = keep
            role_update['role_multiplier'] = multiplier
            role_update['role_cooldown'] = cooldown
            await pull_role(ctx.guild.id, role)
            await push_role(ctx.guild.id, role_update)
            return await ctx.reply(f"role updated\n{role_update}")
    await ctx.reply(f"role not found")

async def delete_xp_role(ctx: commands.Context, role_id: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    if not role_id or not role_id.isdigit():
        return await ctx.reply("usage: -xproledel <roleid>")

    db = await get_database(ctx.guild.id)
    for role in db["xp_roles"]:
        if role["role_id"] == role_id:
            await pull_role(ctx.guild.id, role)
            real_role = ctx.guild.get_role(role_id)
            if not real_role:
                return await ctx.reply("`real_role` not found. removed from database.")
            await real_role.delete()
            return await ctx.reply("role removed from server and database.")
    await ctx.reply(f"role not found")

# utils
def extract_number(input_str):
    pattern = r'^(-?\d+(\.\d+)?)(x.*)?$'
    match = re.match(pattern, input_str)
    if match:
        if match.group(1):
            number = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
            return 1 if number <= 0 else number

def getTotalXP(n): return int((5 * (91 * n + 27 * n ** 2 + 2 * n ** 3)) / 6)

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def loop_level(data):
    total_xp = getTotalXP(data["level"]+1)
    status = False
    while data["xp"] >= total_xp:
        status = True
        data["level"] += 1
        total_xp = getTotalXP(data["level"]+1)
    return status

def draw_bar(data):
    bars = 28 # why 28? because mobile embed footer
    total_xp = data['xp']
    current_xp = total_xp - getTotalXP(data['level'])
    current_xp_limit = getTotalXP(data['level']+1)
    filled_chars = int((current_xp / current_xp_limit) * bars) 
    bar = "▓" * filled_chars + "░" * (bars - filled_chars)
    return bar[:bars] # hard limit

def embed_xp(member: discord.Member, data, fake_roles: list, cooldown, role_id, global_rate):
    embed = discord.Embed(color=0x00ff00)
    if member.avatar: embed.set_author(name=member, icon_url=member.avatar.url)
    else: embed.set_author(name=member)

    cd_role = f"<@&{role_id}>: " if role_id else ""
    multiplier_strs = []
    for role in fake_roles:
        if not role['role_multiplier'] == -1:
            multiplier_strs.append(f"<@&{role['role_id']}>: {role['role_multiplier']}x")
        if role['role_multiplier'] == 0:
            multiplier_strs = [f"<@&{role['role_id']}>: {role['role_multiplier']}x"]
            break
    
    msgs = data['msgs']
    level = data['level']
    total_xp = data['xp']
    current_xp = total_xp - getTotalXP(data['level'])
    current_xp_limit = getTotalXP(data['level']+1)
    current_xp_remain = current_xp_limit - current_xp
    cooldown_left = max(0, int(data['lastUpdated']+cooldown-time.time()))
    xp_percent = round((current_xp / current_xp_limit) * 100, 2)

    embed.add_field(name="✨ XP", value=f"{current_xp} (lv. {level})")
    embed.add_field(name="⏩ Next level", value=f"{current_xp_limit} ({current_xp_remain} more)")
    embed.add_field(name="🕓 Cooldown", value=f"{cooldown}s ({cd_role}{cooldown_left}s left)")
    if multiplier_strs:
        value = "\n".join(multiplier_strs)
        value+= f"\n**Total multiplier: {get_all_multipliers(fake_roles, global_rate)}x**"
        embed.add_field(name="🌟 Multiplier", value=value)
    embed.set_footer(text=f"{draw_bar(data)}\nRate: {global_rate}x, {current_xp} / {current_xp_limit} XP ({xp_percent}%)\nMessage count: {msgs}") # \n? messages to go!
    return embed

def player_data(xp, id, time):
    return {
        "xp": xp,
        "level": 0,
        "lastUpdated": time,
        "userID": id,
        "msgs": 1
    }

def role_data(id: int, level: int):
    return {
        "role_id": id,
        "role_level": level,
        "role_keep": False,
        "role_multiplier": 0 if level < 0 else -1, # 0: restricted, -1: none
        "role_cooldown": -1 # suppresses global cooldown, -1: none
    }

def channel_data(id, cd, rate): # TODO: fuck you colon. you're making this difficult. stop raising the bar. my dad hates me now.
    return {
        "channel_id": id,
        "channel_xp_cooldown": cd,
        "channel_xp_rate": rate
    }

def get_member_roles(member: discord.Member, roles: list):
    fake_roles = []
    for role in member.roles:
        for db_role in roles:
            if role.id == db_role['role_id']:
                fake_roles.append(db_role)
    return fake_roles

def get_lowest_cooldown(fake_roles: list, global_cooldown):
    lowest_cd, role_id = global_cooldown, None
    for role in fake_roles:
        if role['role_cooldown'] < lowest_cd: 
            lowest_cd, role_id = role['role_cooldown'], role['role_id']
    return lowest_cd, role_id

def check_member_if_xp_restricted(fake_roles: list):
    for role in fake_roles:
        if role['role_multiplier'] == 0: return True

def get_all_multipliers(fake_roles: list, global_rate):
    total_multipliers = global_rate
    for role in fake_roles:
        if not role['role_multiplier'] == -1: total_multipliers += role['role_multiplier']
    return total_multipliers

# database handling
async def add_database(server_id: int):
    data = {
        "guild": server_id,
        "prefix": "-",
        "insult_module": True,
        "insult_default": True,
        "xp_module": False,
        "xp_troll": True,
        "xp_channel_mode": False,
        "xp_rate": 1,
        "xp_cooldown": 60,
        "channels": [],
        "xp_roles": [],
        "xp_messages": [],
        "roasts": [],
        "players": []
    }
    await mycol.insert_one(data)
    return data

async def fetch_database(server_id: int):
    return await mycol.find_one({"guild":server_id})

async def get_database(server_id: int):
    db = await fetch_database(server_id)
    if db: return db
    return await add_database(server_id)

async def set_prefix(server_id: int, p):
    await mycol.update_one({"guild":server_id}, {"$set": {"prefix": p}})

async def push_player(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"players": dict(data)}})

async def pull_player(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"players": dict(data)}})

async def set_insult(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"insult_module": b}})

async def set_xp(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_module": b}})

async def set_cooldown(server_id: int, b):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_cooldown": b}})

async def set_rate(server_id: int, b):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_rate": b}})

async def set_mode(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_channel_mode": b}})

async def push_insult(server_id: int, data):
    return await mycol.update_one({"guild":server_id}, {"$push": {"roasts": data}})

async def pull_insult(server_id: int, data):
    return await mycol.update_one({"guild":server_id}, {"$pull": {"roasts": data}})

async def push_xp_msg(server_id: int, data):
    return await mycol.update_one({"guild":server_id}, {"$push": {"xp_messages": data}})

async def pull_xp_msg(server_id: int, data):
    return await mycol.update_one({"guild":server_id}, {"$pull": {"xp_messages": data}})

async def push_role(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"xp_roles": dict(data)}})

async def pull_role(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"xp_roles": dict(data)}})