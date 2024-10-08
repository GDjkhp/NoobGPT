import discord
from discord import app_commands
from discord.ext import commands
import json
import time
import random
import re
from util_database import myclient
from util_discord import command_check, check_if_master_or_admin, description_helper, get_guild_prefix

mycol = myclient["utils"]["nodeports"]
mycol_players = myclient["utils"]["xp_players"]
path="./res/mandatory_settings_and_splashes.json"

# noobgpt sucks without insults they said
async def detect_mentions(message: discord.Message, bot: commands.Bot):
    if message.author.bot: return False
    if message.mentions:
        if bot.user in message.mentions: return True
    ref_msg = None
    msg_id = message.reference.message_id if message.reference and message.reference.message_id else None
    try:
        if msg_id: ref_msg = await message.channel.fetch_message(msg_id)
    except:
        print("Exception in detect_mentions")
    if ref_msg and ref_msg.author == bot.user: return True

async def insult_user(bot: commands.Bot, msg: discord.Message):
    db = await get_database(msg.guild.id if msg.guild else msg.channel.id)
    if not db["insult_module"]: return

    if await detect_mentions(msg, bot):
        # ctx = await bot.get_context(msg) # context hack
        # async with ctx.typing():
        the_list = db["roasts"] if db["roasts"] else read_json_file(path)["insults from thoughtcatalog.com"]
        text = random.choice(the_list)
        await msg.reply(text)

# noobgpt sucks without leveling system they said
async def earn_xp(bot: commands.Bot, msg: discord.Message):
    if not msg.guild: return
    if msg.author.bot: return
    ctx = await bot.get_context(msg)
    if msg.content and msg.content.startswith(await get_guild_prefix(ctx)): return
    db = await get_database(msg.guild.id)
    if not db["xp_module"]: return

    fake_chan = get_channel_data(msg.channel.id, db["channels"])
    fake_roles = get_member_roles(msg.author, db['xp_roles'])
    if check_member_if_xp_restricted(fake_roles, fake_chan): return
    multipliers = get_all_multipliers(fake_roles, fake_chan, db["xp_rate"])
    xp = int(random.randint(15, 25) * multipliers)
    now = time.time()
    player_db = await get_player_db(msg.guild.id)
    for data in player_db["players"]:
        if data["userID"] == msg.author.id:
            cooldown, t_id, t_type = get_lowest_cooldown(fake_roles, fake_chan, db['xp_cooldown'])
            if not now - data["lastUpdated"] >= cooldown: return
            await pull_player(msg.guild.id, data)
            data["xp"] += xp
            data["msgs"] += 1
            data["lastUpdated"] = now
            if loop_level(data):
                await assign_roles_logic(msg, data["level"], db['xp_roles'])
                json_data = read_json_file(path)
                if db["xp_troll"]: text: str = random.choice(json_data["level up loser"])
                else:
                    if db["xp_messages"]: text = random.choice(db["xp_messages"])
                    else: text = json_data["mee6 default"]
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
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}prefix <prefix>`")
    await set_prefix(ctx.guild.id, arg)
    await ctx.reply(f"prefix has been set to `{arg}`")

async def toggle_insult(ctx: commands.Context):
    if await command_check(ctx, "insult", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
    b = not db["insult_module"]
    await set_insult(ctx.guild.id, b)
    await ctx.reply(f"`insult_module` is set to `{b}`")

async def toggle_xp(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    db = await get_database(ctx.guild.id)
    b = not db["xp_module"]
    await set_xp(ctx.guild.id, b)
    await ctx.reply(f"`xp_module` is set to `{b}`")

async def user_rank(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return
    if db.get("bot_rank_channel") and not db["bot_rank_channel"] == ctx.channel.id: return
    if not arg: arg = ctx.author.id
    elif not arg.isdigit(): return await ctx.reply(f"not a digit :(\nusage: `{await get_guild_prefix(ctx)}rank <user_id>`")
    player_db = await get_player_db(ctx.guild.id)
    for player in player_db["players"]:
        if player['userID'] == int(arg):
            fake_roles = get_member_roles(ctx.author, db['xp_roles'])
            fake_chan = get_channel_data(ctx.channel.id, db["channels"])
            cooldown, t_id, t_type = get_lowest_cooldown(fake_roles, fake_chan, db['xp_cooldown'])
            return await ctx.reply(embed=embed_xp(ctx.author, player, fake_roles, cooldown, t_id, db['xp_rate'], t_type, fake_chan))
    await ctx.reply("null player")

async def guild_lead(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    db = await get_database(ctx.guild.id)
    if not db["xp_module"]: return
    if db.get("bot_rank_channel") and not db["bot_rank_channel"] == ctx.channel.id: return
    await ctx.reply("under construction") # TODO: query sorting first n players from highest to lowest xp, such bs (hint: wordle)

# unused command, created automagically
async def create_bot_master_role(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator: return await ctx.reply("not an admin :(")
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles permission is disabled :(**")
    db = await get_database(ctx.guild.id) # nonsense
    role = await ctx.guild.create_role(name="noobgpt bot master", mentionable=False)
    await set_master_role(ctx.guild.id, role.id)
    await ctx.reply(f"<@&{role.id}> role added")

async def add_master_user(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator: return await ctx.reply("not an admin :(")
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    if not arg: arg = str(ctx.author.id)
    if ctx.message.mentions: member = ctx.message.mentions[0]
    elif arg.isdigit(): member = ctx.guild.get_member(int(arg))
    else: return await ctx.reply("not a user id")
    if not member: return await ctx.reply("user not found")

    db = await get_database(ctx.guild.id)
    if not db.get("bot_master_role") or not ctx.guild.get_role(db["bot_master_role"]):
        await create_bot_master_role(ctx)
        db = await get_database(ctx.guild.id) # update

    role = ctx.guild.get_role(db["bot_master_role"])
    await member.add_roles(role)
    await ctx.reply(f"bot master role <@&{role.id}> added to <@{member.id}>")

async def add_xp_role(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")

    p = await get_guild_prefix(ctx)
    if not arg or not arg.lstrip('-').isdigit():
        return await ctx.reply(f"usage: `{p}xprole <level>`\nparameters:\n`-1` = restricted, `0` = none, `1, 2, ...` = levels")
    
    role = await ctx.guild.create_role(name="Level "+arg if int(arg) > 0 else "special role" if int(arg) == 0 else "xp restriction", 
                                       mentionable=False)
    await push_role(ctx.guild.id, role_data(role.id, int(arg)))
    await ctx.reply(f"<@&{role.id}> has been created. edit attributes using `{p}xproleedit <roleid>`, `name` and `color` in server settings.")

async def view_xp_roles(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    db = await get_database(ctx.guild.id)
    text_list = []
    for role in db["xp_roles"]:
        text_list.append(f'<@&{role["role_id"]}>')
        text_list.append(f'Level: {role["role_level"]}, Multiplier: {role["role_multiplier"]}, Cooldown: {role["role_cooldown"]}, Keep: {role["role_keep"]}')

    if not text_list: return await ctx.reply("`xp_roles` not found 😳")
    text = "\n".join(text_list)
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else: await ctx.send(chunk)

async def edit_xp_role(ctx: commands.Context, role_id: str, keep: str, multiplier: str, cooldown: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    if not role_id or not role_id.isdigit():
        return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}xproleedit <roleid>`")
    role_id = int(role_id)
    db = await get_database(ctx.guild.id)
    for role in db["xp_roles"]:
        if role["role_id"] == role_id:
            real_role = ctx.guild.get_role(role_id)
            if not real_role:
                await pull_role(ctx.guild.id, role)
                return await ctx.reply("`real_role` not found.\nremoved from database.")
            
            if keep and keep.isdigit():
                keep = True if int(keep) else False
            else: return await ctx.reply("`keep` not found.\nplease enter `0` for no or `1` for yes.")

            if not multiplier: multiplier = role['role_multiplier'] # maintain -1 for none
            else:
                mulx = extract_number(multiplier)
                if not mulx: 
                    m_str = "`multiplier` not found.\nplease enter in `1.75x` or `1` format. use `0` for xp restriction, `-1` for none."
                    return await ctx.reply(m_str)
                multiplier = float(mulx)

            if not cooldown: cooldown = role['role_cooldown'] # maintain -1 for none
            else:
                if not cooldown.lstrip('-').isdigit(): 
                    return await ctx.reply("`cooldown` not found.\nplease enter a valid integer. use `-1` for none.")
                cooldown = int(cooldown)

            role_update = role_data(role_id, role['role_level'])
            role_update['role_keep'] = keep
            role_update['role_multiplier'] = multiplier
            role_update['role_cooldown'] = cooldown
            await pull_role(ctx.guild.id, role)
            await push_role(ctx.guild.id, role_update)
            return await ctx.reply(f"role updated\n{role_update}")
    await ctx.reply(f"role not found")

async def delete_xp_role(ctx: commands.Context, role_id: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles is disabled :(**")
    
    if not role_id or not role_id.isdigit():
        return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}xproledel <roleid>`")
    role_id = int(role_id)
    db = await get_database(ctx.guild.id)
    for role in db["xp_roles"]:
        if role["role_id"] == role_id:
            await pull_role(ctx.guild.id, role)
            real_role = ctx.guild.get_role(role_id)
            if not real_role:
                return await ctx.reply("`real_role` not found.\nremoved from database.")
            await real_role.delete()
            return await ctx.reply("role removed from server and database.")
    await ctx.reply(f"role not found")

async def toggle_special_channel(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

    db = await get_database(ctx.guild.id)
    for chan in db["channels"]:
        if chan["channel_id"] == ctx.channel.id:
            await pull_channel(ctx.guild.id, chan)
            return await ctx.reply("channel has been removed from the database")
    
    await push_channel(ctx.guild.id, channel_data(ctx.channel.id, 0, 0))
    await ctx.reply(f"channel has been added to the database with an xp rate and cooldown of `0`. edit entry using `{await get_guild_prefix(ctx)}xpchanedit`")

async def edit_special_channel(ctx: commands.Context, rate: str, cooldown: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

    db = await get_database(ctx.guild.id)
    for chan in db["channels"]:
        if chan["channel_id"] == ctx.channel.id:
            m_str = "`rate` not found.\nplease enter in `1.75x` or `1` format. use `0` for xp restriction, `-1` for none."
            if not rate: return await ctx.reply(m_str)
            else:
                mulx = extract_number(rate)
                if not mulx: return await ctx.reply(m_str)
                rate = float(mulx)

            if not cooldown: cooldown = chan['channel_xp_cooldown'] # maintain -1 for none
            else:
                if not cooldown.lstrip('-').isdigit(): 
                    return await ctx.reply("`cooldown` not found.\nplease enter a valid integer. use `-1` for none.")
                cooldown = int(cooldown)
            
            fake_chan = channel_data(ctx.channel.id, rate, cooldown)
            await pull_channel(ctx.guild.id, chan)
            await push_channel(ctx.guild.id, fake_chan)
            return await ctx.reply(f"channel updated\n{fake_chan}")
    await ctx.reply("channel not found")

async def toggle_troll(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    db = await get_database(ctx.guild.id)
    b = not db["xp_troll"]
    await set_troll_mode(ctx.guild.id, b)
    await ctx.reply(f"`xp_troll` is set to `{b}`")

async def view_insults(ctx: commands.Context):
    if await command_check(ctx, "insult", "utils"): return
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
    text = "\n".join(db["roasts"])
    if not text: 
        return await ctx.reply(content=f"**Error! :(**\nGood bot.\nDefault insults are being used. Add custom insults using `{await get_guild_prefix(ctx)}insultadd`")
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else: await ctx.send(chunk)

async def view_lvlmsgs(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    db = await get_database(ctx.guild.id)
    p = await get_guild_prefix(ctx)
    if db["xp_troll"]: return await ctx.reply(f"xp troll is enabled. disable this first using `{p}lvlmsgtroll`.")
    text = "\n".join(db["xp_messages"])
    if not text:
        stat = f"**Error! :(**\nDefault mee6 level up message is being used. Add custom messages using `{p}lvlmsgadd`"
        return await ctx.reply(content=stat)
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else: await ctx.send(chunk)

async def add_insult(ctx: commands.Context, arg: str):
    if await command_check(ctx, "insult", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    p = await get_guild_prefix(ctx)
    if not arg: return await ctx.reply(f"usage: `{p}insultadd <str>`")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id) # nonsense
    await push_insult(ctx.guild.id if ctx.guild else ctx.channel.id, arg)
    await ctx.reply(f"insult added. use `{p}insultview` to list all insults.")

async def add_lvl_msg(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    p = await get_guild_prefix(ctx)
    if not arg: return await ctx.reply(f"usage: `{p}lvlmsgadd <str>`\nformat: {read_json_file(path)['mee6 default']}")
    await push_xp_msg(ctx.guild.id, arg)
    await ctx.reply(f"levelup msg added. use `{p}lvlmsgview` to list all levelup msgs.")

async def del_insult(ctx: commands.Context, arg: str):
    if await command_check(ctx, "insult", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    p = await get_guild_prefix(ctx)
    if not arg: return await ctx.reply(f"usage: `{p}insultdel <str>`")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id) # nonsense
    await pull_insult(ctx.guild.id if ctx.guild else ctx.channel.id, arg)
    await ctx.reply(f"insult removed. use `{p}insultview` to list all insults.")

async def del_lvl_msg(ctx: commands.Context, arg: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    p = await get_guild_prefix(ctx)
    if not arg: return await ctx.reply(f"usage: `{p}lvlmsgdel <str>`")
    await pull_xp_msg(ctx.guild.id, arg)
    await ctx.reply(f"levelup msg removed. use `{p}lvlmsgview` to list all levelup msgs.")

# TODO: add xp
async def user_set_xp(ctx: commands.Context, user: str, number: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

# TODO: set level
async def user_set_level(ctx: commands.Context, user: str, number: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

async def rank_channel(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "level", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")

    db = await get_database(ctx.guild.id)
    p = await get_guild_prefix(ctx)
    if db.get("bot_rank_channel") and db["bot_rank_channel"] == ctx.channel.id:
        await set_rank_channel(ctx.guild.id, 0)
        await ctx.reply(f"rank channel has been removed. everyone can use `{p}rank` and `{p}levels` everywhere.")
    else:
        await set_rank_channel(ctx.guild.id, ctx.channel.id)
        await ctx.reply(f"rank channel has been added. everyone can use `{p}rank` and `{p}levels` only in this channel.")

async def help_insult(ctx: commands.Context):
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}insult` Toggles insults. Defaults to thoughtcatalog.com",
        f"`{p}insultview` View custom insults.",
        f"`{p}insultadd` Add custom insult.",
        f"`{p}insultdel` Delete custom insult.",
    ]
    await ctx.reply("\n".join(text))

async def help_level(ctx: commands.Context):
    p = await get_guild_prefix(ctx)
    text = [
        "# User commands",
        f"`{p}xp` Toggle XP leveling system.",
        f"`{p}rank` View a member's rank.",
        f"`{p}levels` View server leaderboard.",
        "# Role commands",
        f"`{p}xproleadd` Add level role.",
        f"`{p}xproleedit` Edit level role.",
        f"`{p}xproledel` Delete level role.",
        f"`{p}xproleview` View level roles.",
        "# Message commands",
        f"`{p}lvlmsgadd` Add custom level up message.",
        f"`{p}lvlmsgdel` Delete custom level up message.",
        f"`{p}lvlmsgview` View custom level up messages.",
        f"`{p}lvlmsgtroll` Toggle default troll level up messages.",
        "# Channel commands",
        f"`{p}xpchan` Toggle XP channel.",
        f"`{p}xpchanedit` Edit XP channel.",
        f"`{p}xprankchan` Set rank/leaderboard command channel.",
    ]
    await ctx.reply("\n".join(text))

# utils
async def assign_roles_logic(message: discord.Message, level: int, db_fake_roles: list):
    highest_level_role = None
    for r in db_fake_roles:
        if r["role_level"] > 0 and r["role_level"] <= level: 
            highest_level_role = r
    if not highest_level_role: return
    for r in message.author.roles:
        if highest_level_role["role_id"] == r.id: return

    role_del_list = []
    for fake in db_fake_roles:
        for r in message.author.roles:
            if fake["role_id"] == r.id and fake["role_level"] > 0 and not fake["role_keep"]: 
                role_del_list.append(r)
    if role_del_list: await message.author.remove_roles(*role_del_list)
    new_role = message.guild.get_role(highest_level_role["role_id"])
    await message.author.add_roles(new_role)

def extract_number(input_str):
    pattern = r'^(-?\d+(\.\d+)?)(x.*)?$'
    match = re.match(pattern, input_str)
    if match:
        if match.group(1):
            number = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
            return str(-1) if number < 0 else str(number)

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

def embed_xp(member: discord.Member, data, fake_roles: list, cooldown, t_id, global_rate, t_type, fake_chan):
    embed = discord.Embed(color=0x00ff00)
    if member.avatar: embed.set_author(name=member, icon_url=member.avatar.url)
    else: embed.set_author(name=member)

    if t_type:
        if t_type == "role": cd_role = f"<@&{t_id}>\n"
        if t_type == "channel": cd_role = f"<#{t_id}>\n"
    else: cd_role = ""

    xp_restricted = False
    multiplier_strs = []
    for role in fake_roles:
        if not role['role_multiplier'] == -1:
            multiplier_strs.append(f"<@&{role['role_id']}>: {role['role_multiplier']}x")
        if role['role_multiplier'] == 0:
            xp_restricted = True
            multiplier_strs = [f"<@&{role['role_id']}>: {role['role_multiplier']}x"]
            break

    if not xp_restricted and fake_chan: 
        multiplier_strs.append(f"<#{fake_chan['channel_id']}>: {fake_chan['channel_xp_rate']}x")
    
    msgs = data['msgs']
    level = data['level']
    total_xp = data['xp']
    current_xp = total_xp - getTotalXP(level)
    current_xp_limit = getTotalXP(level+1)
    current_xp_remain = current_xp_limit - current_xp
    cooldown_left = max(0, int(data['lastUpdated']+cooldown-time.time()))
    xp_percent = round((current_xp / current_xp_limit) * 100, 2)

    embed.add_field(name="✨ XP", value=f"{current_xp} (lv. {level})")
    embed.add_field(name="⏩ Next level", value=f"{current_xp_limit} ({current_xp_remain} more)")
    embed.add_field(name="🕓 Cooldown", value=f"{cd_role}{cooldown}s ({cooldown_left}s left)")
    if multiplier_strs:
        value = "\n".join(multiplier_strs)
        value+= f"\n**Total multiplier: {get_all_multipliers(fake_roles, fake_chan, global_rate)}x**"
        embed.add_field(name="🌟 Multiplier", value=value)
    embed.set_footer(text=f"{draw_bar(data)}\nRate: {global_rate}x, {current_xp} / {current_xp_limit} XP ({xp_percent}%)\nTotal XP: {total_xp}, Message count: {msgs}") # \n? messages to go!
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

def channel_data(id, rate, cd):
    return {
        "channel_id": id,
        "channel_xp_rate": rate,
        "channel_xp_cooldown": cd
    }

def get_member_roles(member: discord.Member, roles: list):
    fake_roles = []
    for role in member.roles:
        for db_role in roles:
            if role.id == db_role['role_id']:
                fake_roles.append(db_role)
    return fake_roles

def get_lowest_cooldown(fake_roles: list, fake_chan, global_cooldown):
    lowest_cd, t_id, t_type = global_cooldown, None, None
    if fake_chan and fake_chan["channel_xp_cooldown"] >= 0 and fake_chan["channel_xp_cooldown"] < lowest_cd:
            lowest_cd, t_id, t_type = fake_chan["channel_xp_cooldown"], fake_chan["channel_id"], "channel"
    for role in fake_roles:
        if role['role_cooldown'] >= 0 and role['role_cooldown'] < lowest_cd:
            lowest_cd, t_id, t_type = role['role_cooldown'], role['role_id'], "role"
    return lowest_cd, t_id, t_type

def check_member_if_xp_restricted(fake_roles: list, fake_chan):
    for role in fake_roles:
        if role['role_multiplier'] == 0: return True
    if fake_chan and fake_chan["channel_xp_rate"] == 0: return True

def get_all_multipliers(fake_roles: list, fake_chan, global_rate):
    total_multipliers = global_rate
    for role in fake_roles:
        if role['role_multiplier'] == 0: return 0
        if not role['role_multiplier'] < 0:
            total_multipliers += role['role_multiplier']
    if fake_chan:
        if fake_chan["channel_xp_rate"] == 0: return 0
        if not fake_chan["channel_xp_rate"] < 0:
            total_multipliers += fake_chan["channel_xp_rate"]
    return total_multipliers

def get_channel_data(chan_id: int, fake_chans: list):
    for chan in fake_chans:
        if chan["channel_id"] == chan_id: return chan

# database handling
async def add_database(server_id: int):
    data = {
        "guild": server_id,
        "prefix": "-",
        "bot_master_role": 0,
        "bot_rank_channel": 0,
        "insult_module": True,
        "roasts": [],
        "xp_module": False,
        "xp_troll": False,
        "xp_rate": 1,
        "xp_cooldown": 60,
        "xp_roles": [],
        "xp_messages": [],
        "channels": [],
    }
    await mycol.insert_one(data)
    return data

async def fetch_database(server_id: int):
    return await mycol.find_one({"guild":server_id})

async def get_database(server_id: int):
    db = await fetch_database(server_id)
    if db: return db
    return await add_database(server_id)

async def add_player_db(server_id: int):
    data = {
        "guild": server_id,
        "players": [],
    }
    await mycol_players.insert_one(data)
    return data

async def fetch_player_db(server_id: int):
    return await mycol_players.find_one({"guild":server_id})

async def get_player_db(server_id: int):
    db = await fetch_player_db(server_id)
    if db: return db
    return await add_player_db(server_id)

async def set_prefix(server_id: int, p):
    await mycol.update_one({"guild":server_id}, {"$set": {"prefix": p}})

async def push_player(server_id: int, data):
    await mycol_players.update_one({"guild":server_id}, {"$push": {"players": dict(data)}})

async def pull_player(server_id: int, data):
    await mycol_players.update_one({"guild":server_id}, {"$pull": {"players": dict(data)}})

async def set_insult(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"insult_module": b}})

async def set_xp(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_module": b}})

async def set_cooldown(server_id: int, b):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_cooldown": b}})

async def set_rate(server_id: int, b):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_rate": b}})

async def set_troll_mode(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"xp_troll": b}})

async def push_insult(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"roasts": data}})

async def pull_insult(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"roasts": data}})

async def push_xp_msg(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"xp_messages": data}})

async def pull_xp_msg(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"xp_messages": data}})

async def push_role(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"xp_roles": dict(data)}})

async def pull_role(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"xp_roles": dict(data)}})

async def set_master_role(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$set": {"bot_master_role": data}})

async def push_channel(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"channels": dict(data)}})

async def pull_channel(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"channels": dict(data)}})

async def set_rank_channel(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$set": {"bot_rank_channel": data}})

class LevelInsult(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # insults
    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["insult"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insult(self, ctx: commands.Context):
        await toggle_insult(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['insult']} View custom insults")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insultview(self, ctx: commands.Context):
        await view_insults(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['insult']} Add custom insult")
    @app_commands.describe(insult="Add insult")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insultadd(self, ctx: commands.Context, *, insult:str=None):
        await add_insult(ctx, insult)

    @commands.hybrid_command(description=f"{description_helper['emojis']['insult']} Delete custom insult")
    @app_commands.describe(insult="Delete insult")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insultdel(self, ctx: commands.Context, *, insult:str=None):
        await del_insult(ctx, insult)

    @commands.hybrid_command(description=f"{description_helper['emojis']['insult']} How to use custom insults")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insulthelp(self, ctx: commands.Context):
        await help_insult(ctx)

    # xp level system
    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["xp"]}')
    async def xp(self, ctx: commands.Context):
        await toggle_xp(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} View a member's rank")
    @app_commands.describe(user_id="User ID of the member you want to see the rank of")
    async def rank(self, ctx: commands.Context, user_id:str=None):
        await user_rank(ctx, user_id)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} View server leaderboard")
    async def levels(self, ctx: commands.Context):
        await guild_lead(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} View level roles")
    async def xproleview(self, ctx: commands.Context):
        await view_xp_roles(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Add level role")
    @app_commands.describe(level="Level role (`-1` = restricted, `0` = none, `1, 2, ...` = levels)")
    async def xproleadd(self, ctx: commands.Context, level:str=None):
        await add_xp_role(ctx, level)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Edit level role")
    @app_commands.describe(keep="Keep level role (please enter `0` for no or `1` for yes)", 
                           multiplier="Set level role multiplier (please enter in `1.75x` or `1` format. use `0` for xp restriction, `-1` for none)", 
                           cooldown="Set level role cooldown (please enter a valid integer. use `-1` for none)",
                           role_id="Role ID of the level role you want to edit")
    async def xproleedit(self, ctx: commands.Context, role_id:str=None, keep:str=None, multiplier:str=None, cooldown:str=None):
        await edit_xp_role(ctx, role_id, keep, multiplier, cooldown)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Delete level role")
    @app_commands.describe(role_id="Role ID of the role you want to delete")
    async def xproledel(self, ctx: commands.Context, role_id:str=None):
        await delete_xp_role(ctx, role_id)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} View custom level up messages")
    async def lvlmsgview(self, ctx: commands.Context):
        await view_lvlmsgs(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Add custom level up message")
    @app_commands.describe(message="Add level up message")
    async def lvlmsgadd(self, ctx: commands.Context, *, message:str=None):
        await add_lvl_msg(ctx, message)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Delete custom level up message")
    @app_commands.describe(message="Delete level up message")
    async def lvlmsgdel(self, ctx: commands.Context, *, message:str=None):
        await del_lvl_msg(ctx, message)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Toggle troll level up messages")
    async def lvlmsgtroll(self, ctx: commands.Context):
        await toggle_troll(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} How to use XP system")
    async def xphelp(self, ctx: commands.Context):
        await help_level(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Toggle XP channel")
    async def xpchan(self, ctx: commands.Context):
        await toggle_special_channel(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Edit XP channel")
    @app_commands.describe(rate="Set channel xp rate (please enter in `1.75x` or `1` format. use `0` for xp restriction, `-1` for none)",
                           cooldown="Set channel xp cooldown (please enter a valid integer. use `-1` for none)")
    async def xpchanedit(self, ctx: commands.Context, rate:str=None, cooldown:str=None):
        await edit_special_channel(ctx, rate, cooldown)

    @commands.hybrid_command(description=f"{description_helper['emojis']['xp']} Set rank/leaderboard command channel")
    async def xprankchan(self, ctx: commands.Context):
        await rank_channel(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelInsult(bot))