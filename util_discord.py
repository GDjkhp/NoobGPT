from discord.ext import commands
from discord import app_commands
import discord
import json
import os
from util_database import *
mycol = myclient["utils"]["commands"]
legal_url="https://gdjkhp.github.io/NoobGPT/#legal"

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

async def copypasta(ctx: commands.Context):
    if await command_check(ctx, "legal", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=legal_url, 
                                    emoji="☑️", label="Terms and conditions"))
    await ctx.reply(read_json_file("./res/mandatory_settings_and_splashes.json")["legal"], view=view)

# shit deed
available_categories=["ai", "games", "media", "utils"]
ai_commands=["openai", "googleai", "petals", "perplex", "groq", "github", "mistral", "claude", "c.ai", "blackbox", "pawan", "horde"]
games_commands=["aki", "tic", "hang", "quiz", "word", "rps"]
media_commands=["anime", "manga", "tv", "ytdlp", "cob", "booru", "music", "deez"]
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
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}view` View disabled commands",
        f"`{p}botmaster [user id]` Adds bot master role to a user",
        f"`{p}prefix [prefix]` Change bot command prefix",
        f"`{p}channel` Toggle channel mode, where you can set specific commands per channel",
        f"`{p}toggle [command]` Toggle command. Requires channel mode",
        f"`{p}disable [command]` Disable command server-wide"
    ]
    await ctx.reply("\n".join(text))

async def set_prefix_cmd(ctx: commands.Context, arg: str):
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}prefix <prefix>`")
    db = await get_database2(ctx.guild.id) # nonsense
    await set_prefix(ctx.guild.id, arg)
    await ctx.reply(f"prefix has been set to `{arg}`")

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

    db = await get_database2(ctx.guild.id)
    if not db.get("bot_master_role") or not ctx.guild.get_role(db["bot_master_role"]):
        await create_bot_master_role(ctx)
        db = await get_database2(ctx.guild.id) # update

    role = ctx.guild.get_role(db["bot_master_role"])
    await member.add_roles(role)
    await ctx.reply(f"bot master role <@&{role.id}> added to <@{member.id}>")

# unused command, created automagically
async def create_bot_master_role(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if not ctx.author.guild_permissions.administrator: return await ctx.reply("not an admin :(")
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles permission is disabled :(**")
    db = await get_database2(ctx.guild.id) # nonsense
    role = await ctx.guild.create_role(name="noobgpt bot master", mentionable=False)
    await set_master_role(ctx.guild.id, role.id)
    await ctx.reply(f"<@&{role.id}> role added")

async def command_enable(ctx: commands.Context, com: str):
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    if not com: return await ctx.reply(f"execute `{await get_guild_prefix(ctx)}halp` to view commands")
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
    if not com: return await ctx.reply(f"execute `{await get_guild_prefix(ctx)}halp` to view commands")
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

# public code for everyone to share, free to use
description_helper = read_json_file("./res/mandatory_settings_and_splashes.json")["help_wanted_dictionaries_dead_or_alive"]

def check_if_not_owner(ctx: commands.Context): # does not support interactions, deal with it
    return ctx.author.id != int(os.getenv("OWNER"))

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
    if not ctx.guild: return True # dm support
    db = await get_database2(ctx.guild.id)
    check = db.get("bot_master_role") and ctx.guild.get_role(db["bot_master_role"]) in ctx.author.roles
    return check or ctx.author.guild_permissions.administrator

async def get_guild_prefix(ctx: commands.Context):
    db = await get_database2(ctx.guild.id if ctx.guild else ctx.channel.id)
    return db["prefix"]

class DiscordUtil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["config"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def config(self, ctx: commands.Context):
        await config_commands(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Toggle channel mode, where you can set specific commands per channel")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def channel(self, ctx: commands.Context):
        await command_channel_mode(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Toggle command. Requires channel mode")
    @app_commands.describe(command="Command you want to enable")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def toggle(self, ctx: commands.Context, command:str=None):
        await command_enable(ctx, command)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Disable command server-wide")
    @app_commands.describe(command="Command you want to disable")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def disable(self, ctx: commands.Context, command:str=None):
        await command_disable(ctx, command)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} View available commands")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def view(self, ctx: commands.Context):
        await command_view(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Change bot command prefix")
    @app_commands.describe(prefix="Set prefix")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def prefix(self, ctx: commands.Context, prefix:str=None):
        await set_prefix_cmd(ctx, prefix)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Adds bot master role to a user")
    @app_commands.describe(user_id="User ID of the member you want to be a bot master")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botmaster(self, ctx: commands.Context, user_id:str=None):
        await add_master_user(ctx, user_id)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} View terms of service and privacy policy")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def legal(self, ctx: commands.Context):
        await copypasta(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordUtil(bot))