from discord.ext import commands
import json
from util_database import myclient
mycol = myclient["utils"]["commands"]

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
available_categories=["ai", "games", "media", "utils"]
ai_commands=["openai", "googleai", "petals", "perplex", "groq", "github", "mistral", "claude", "c.ai"]
games_commands=["aki", "tic", "hang", "quiz", "word", "rps"]
media_commands=["anime", "manga", "tv", "ytdlp", "cob", "booru", "music"]
utils_commands=["quote", "weather", "av", "ban", "halp", "legal", "xp", "insult"]
available_commands = ai_commands + games_commands + media_commands + utils_commands

def category_to_commands(cat: str, commands: list):
    y = []
    if cat == "ai":    y = ai_commands
    if cat == "games": y = games_commands
    if cat == "media": y = media_commands
    if cat == "utils": y = utils_commands
    for x in y:
        if not x in commands: commands.append(x)

async def config_commands(ctx: commands.Context):
    text = [
        "`-view` View available commands.",
        "`-botmaster [user/userid]` Adds bot master role to a user.",
        "`-prefix [prefix]` Change bot command prefix.",
        "`-channel` Toggle channel mode, where you can set specific commands per channel.",
        "`-toggle [command]` Toggle command. Requires channel mode.",
        "`-disable [command]` Disable command server-wide."
    ]
    await ctx.reply("\n".join(text))

async def command_enable(ctx: commands.Context, com: str):
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    if not com: return await ctx.reply("execute `-halp` to view commands")
    if not com in available_commands and not com in available_categories:
        return await ctx.reply("😩")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
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
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    if not com: return await ctx.reply("execute `-halp` to view commands")
    if not com in available_commands and not com in available_categories:
        return await ctx.reply("😩")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id) # nonsense
    if com in available_commands:
        res = await toggle_global_command(ctx.guild.id, com)
    if com in available_categories: 
        res = await toggle_global_cat(ctx.guild.id, com)
    await ctx.reply(f"`{com}` has been {res} server-wide")

async def command_channel_mode(ctx: commands.Context):
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
    await set_mode(ctx.guild.id, not db["channel_mode"])
    await ctx.reply(f'channel mode is now set to {not db["channel_mode"]}')

async def command_view(ctx: commands.Context):
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
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

# database handling sequel
mycol2 = myclient["utils"]["nodeports"]
async def add_database2(server_id: int):
    data = {
        "guild": server_id,
        "prefix": "-",
        "bot_master_role": 0,
        "bot_dj_role": 0,
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
    await mycol2.insert_one(data)
    return data

async def fetch_database2(server_id: int):
    return await mycol2.find_one({"guild":server_id})

async def get_database2(server_id: int):
    db = await fetch_database2(server_id)
    if db: return db
    return await add_database2(server_id)

async def set_dj_role_db(server_id: int, role_id):
    await mycol2.update_one({"guild":server_id}, {"$set": {"bot_dj_role": role_id}})

# public code for everyone to share, free to use
async def command_check(ctx: commands.Context, com: str, cat: str):
    db = await get_database(ctx.guild.id if ctx.guild else ctx.channel.id)
    if com in db["disabled_commands"]: return True
    if cat in db["disabled_categories"]: return True
    if db["channel_mode"]:
        for chan in db["channels"]:
            if chan["id"] == ctx.channel.id:
                if com in chan["commands"]: return False
        return True

async def check_if_master_or_admin(ctx: commands.Context):
    if not ctx.guild: return True # dm support, fuck you guys <3
    db = await get_database2(ctx.guild.id)
    check = db.get("bot_master_role") and ctx.guild.get_role(db["bot_master_role"]) in ctx.author.roles
    if check or ctx.author.guild_permissions.administrator: return True

# unused (for prefix help commands)
async def get_guild_prefix(ctx: commands.Context):
    db = await get_database2(ctx.guild.id if ctx.guild else ctx.channel.id)
    return db["prefix"]

class DiscordUtil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def config(ctx: commands.Context):
        await config_commands(ctx)

    @commands.command()
    async def channel(ctx: commands.Context):
        await command_channel_mode(ctx)

    @commands.command()
    async def enable(ctx: commands.Context, arg=None):
        await command_enable(ctx, arg)

    @commands.command()
    async def disable(ctx: commands.Context, arg=None):
        await command_disable(ctx, arg)

    @commands.command()
    async def view(ctx: commands.Context):
        await command_view(ctx)

    @commands.command()
    async def ban(ctx: commands.Context, *, arg=None):
        await banner(ctx, ctx.bot, arg)

    @commands.command()
    async def av(ctx: commands.Context, *, arg=None):
        await avatar(ctx, ctx.bot, arg)

    @commands.command()
    async def legal(ctx: commands.Context):
        await copypasta(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordUtil(bot))