from discord.ext import commands
import json
import util_database
mycol = util_database.myclient["utils"]["commands"]

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

async def copypasta(ctx: commands.Context):
    if await command_check(ctx, "legal", "utils"): return
    await ctx.reply(read_json_file("./res/mandatory_settings_and_splashes.json")["legal"])

async def avatar(ctx: commands.Context, bot: commands.Bot, arg: str):
    if await command_check(ctx, "av", "utils"): return
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.avatar: return await ctx.reply(user.avatar.url)
    except: pass
    await ctx.reply("There is no such thing.")

async def banner(ctx: commands.Context, bot: commands.Bot, arg: str):
    if await command_check(ctx, "ban", "utils"): return
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.banner: return await ctx.reply(user.banner.url)
    except: pass
    await ctx.reply("There is no such thing.")

# shit deed
import discord
supported = [discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel, discord.Thread] # sussy
available_categories=["ai", "games", "media", "utils"]
ai_commands=["openai", "googleai", "petals", "perplex", "mistral", "claude", "chelp"]
games_commands=["aki", "tic", "hang", "quiz", "word", "rps"]
media_commands=["anime", "manga", "tv", "ytdlp", "cob", "booru"]
utils_commands=["quote", "weather", "av", "ban", "halp", "legal"]
available_commands = ai_commands + games_commands + media_commands + utils_commands

async def command_check(ctx: commands.Context, com: str, cat: str):
    if not type(ctx.channel) in supported: return False
    db = await get_database(ctx.guild.id)
    if com in db["disabled_commands"]: return True
    if cat in db["disabled_categories"]: return True
    if db["channel_mode"]:
        for chan in db["channels"]:
            if chan["id"] == ctx.channel.id:
                if com in chan["commands"]: return False
        return True
    
def category_to_commands(cat: str, commands: list):
    y = []
    if cat == "ai":    y = ai_commands
    if cat == "games": y = games_commands
    if cat == "media": y = media_commands
    if cat == "utils": y = utils_commands
    for x in y:
        if not x in commands: commands.append(x)

async def config_commands(ctx: commands.Context):
    text = "`-view` View available commands.\n"
    text+= "`-channel` Toggle channel mode, where you can set specific commands per channel. (admin-only)\n"
    text+= "`-toggle [command]` Toggle command. Requires channel mode. (admin-only)\n"
    text+= "`-disable [command]` Disable command server-wide. (admin-only)"
    await ctx.reply(text)

async def command_enable(ctx: commands.Context, com: str):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    if not com: return await ctx.reply("execute `-halp` to view commands")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if not com in available_commands and not com in available_categories:
        return await ctx.reply("😩")
    db = await get_database(ctx.guild.id)
    if not db["channel_mode"]: return await ctx.reply("channel_mode is disabled")
    if com in db["disabled_commands"] or com in db["disabled_categories"]:
        return await ctx.reply(f"`{com}` was disabled server-wide (enable `{com}` first)")
    
    chan_deets = None
    for chan in db["channels"]:
        if chan["id"] == ctx.channel.id:
            chan_deets = chan
            break
    if not chan_deets:
        chan_deets = {
            "id": ctx.channel.id,
            "commands": []
        }
    else: await pull_channel(ctx.guild.id, chan_deets)

    if com in available_commands:
        if com in chan_deets["commands"]:
            chan_deets["commands"].remove(com)
            res = "disabled"
        else: 
            chan_deets["commands"].append(com)
            res = "enabled"
    if com in available_categories:
        category_to_commands(com, chan_deets["commands"]) # enable all
        res = "enabled"

    await push_channel(ctx.guild.id, chan_deets)
    await ctx.reply(f"`{com}` has been {res}")

async def command_disable(ctx: commands.Context, com: str):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    if not com: return await ctx.reply("execute `-halp` to view commands")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    if not com in available_commands and not com in available_categories:
        return await ctx.reply("😩")
    db = await get_database(ctx.guild.id) # nonsense
    if com in available_commands:
        res = await toggle_global_command(ctx.guild.id, com)
    if com in available_categories: 
        res = await toggle_global_cat(ctx.guild.id, com)
    await ctx.reply(f"`{com}` has been {res} server-wide")

async def command_channel_mode(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("not an admin")
    db = await get_database(ctx.guild.id)
    await set_mode(ctx.guild.id, not db["channel_mode"])
    await ctx.reply(f'channel mode is now set to {not db["channel_mode"]}')

async def command_view(ctx: commands.Context):
    if not type(ctx.channel) in supported: return await ctx.reply("not supported")
    db = await get_database(ctx.guild.id)
    text  = f"disabled_commands: `{db['disabled_commands']}`\n"
    text += f"disabled_categories: `{db['disabled_categories']}`\n"
    text += f"channel_mode: `{db['channel_mode']}`"
    if db['channel_mode']:
        for chan in db["channels"]:
            if chan["id"] == ctx.channel.id:
                text += f"\ncommands: `{chan['commands']}`"
    await ctx.reply(text)

# database handling
async def add_database(server_id: int):
    data = {
        "guild": server_id,
        "channel_mode": False,
        "channels": [],
        "disabled_commands": [],
        "disabled_categories": [],
    }
    await mycol.insert_one(data)
    return data

async def fetch_database(server_id: int):
    return await mycol.find_one({"guild":server_id})

async def get_database(server_id: int):
    db = await fetch_database(server_id)
    if db: return db
    return await add_database(server_id)

async def push_channel(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$push": {"channels": dict(data)}})

async def pull_channel(server_id: int, data):
    await mycol.update_one({"guild":server_id}, {"$pull": {"channels": dict(data)}})

async def set_mode(server_id: int, b: bool):
    await mycol.update_one({"guild":server_id}, {"$set": {"channel_mode": b}})

async def push_com(server_id: int, com: str):
    await mycol.update_one({"guild":server_id}, {"$push": {"disabled_commands": com}})
    return "disabled"

async def pull_com(server_id: int, com: str):
    await mycol.update_one({"guild":server_id}, {"$pull": {"disabled_commands": com}})
    return "enabled"

async def toggle_global_command(server_id: int, com):
    if await mycol.find_one({"guild":server_id, "disabled_commands": com}):
        return await pull_com(server_id, com)
    return await push_com(server_id, com)

async def push_cat(server_id: int, cat: str):
    await mycol.update_one({"guild":server_id}, {"$push": {"disabled_categories": cat}})
    return "disabled"

async def pull_cat(server_id: int, cat: str):
    await mycol.update_one({"guild":server_id}, {"$pull": {"disabled_categories": cat}})
    return "enabled"

async def toggle_global_cat(server_id: int, cat: str):
    if await mycol.find_one({"guild":server_id, "disabled_categories": cat}):
        return await pull_cat(server_id, cat)
    return await push_cat(server_id, cat)