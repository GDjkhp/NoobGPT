'''
NOTE: noobgpt dystopian arc
this is a social experiment disabled by default.
you need to ask for every user's consent to use this feature.
acquiring message contents without consent should be illegal.
i made this module as proof of concept for discord bots to adapt to this concept.
this is also proof that I DO NOT LOG ANY OF THESE MESSAGES and i only process them per request.
'''

from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from util_discord import check_if_master_or_admin, command_check, description_helper
from util_database import myclient, get_database2, set_log_channel, set_log_notify
mycol = myclient["utils"]["1989"]
bad_filter = ["fuck", "shit", "damn", "piss"]

# event calls
async def message_snitcher(before: discord.Message, after: discord.Message,
                           title: str, desc: str, col: int):
    if not before: return
    if before.author.bot: return
    if not before.guild: return

    db = await get_database2(before.guild.id)
    if not (db.get("log_channel") and db["log_channel"]): return
    chan = before.guild.get_channel(db["log_channel"])
    if not chan: return

    if after:
        content = f"{after.jump_url}\n<t:{round(after.edited_at.timestamp())}:F>"
    else: content = f"{before.channel.jump_url}\n<t:{round(datetime.now().timestamp())}:F>"
    await chan.send(content=content, embed=update_msg_embed(before, after, title, desc, col))

async def message_warden(bot: commands.Bot, msg: discord.Message): # automod ripoff
    if msg.author.bot: return
    if msg.content:
        ctx = await bot.get_context(msg)
        words = msg.content.split()
        for x in words:
            if x in bad_filter:
                db = await get_database2(msg.guild.id)
                if db.get("log_channel") and db["log_channel"]:
                    chan = msg.guild.get_channel(db["log_channel"])
                    if chan: await chan.send(f"{msg.author} said a very bad word!\n{msg.jump_url}")
                await ctx.reply("no no word detected, delete if possible", ephemeral=True)
                return

async def message_creditor(bot: commands.Bot, msg: discord.Message): # social credit system
    if msg.author.bot: return
    data = await get_player_db(msg.author.id)
    if not data["msg_content_ok"]: return
    if msg.content:
        ctx = await bot.get_context(msg)
        words = msg.content.split()
        for x in words:
            if x in bad_filter:
                await update_player(msg.author.id, data["social_credit_score"]-100)
                return await ctx.reply("-100 social credit points", ephemeral=True)
        await update_player(msg.author.id, data["social_credit_score"]+1)
        await ctx.reply("+1 social credit point", ephemeral=True)

# commands
async def exceute_log_channel(ctx: commands.Context, chan_id: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "log", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    chan = None
    if chan_id:
        if chan_id == "off":
            await set_log_channel(ctx.guild.id, 0)
            return await ctx.reply("message logging has been disabled!")
        if not chan_id.isdigit(): return await ctx.reply("not a digit :(")
        chan = ctx.guild.get_channel(int(chan_id))
    if not chan: chan = ctx.channel
    await set_log_channel(ctx.guild.id, chan.id)
    await ctx.reply(f"{chan.jump_url} has been set as **THE MESSAGE LOGGING CENTER!**")

# utils
def update_msg_embed(before: discord.Message, after: discord.Message, title: str, desc: str, color: int):
    e = discord.Embed(title=title, description=desc, color=color)
    if before:
        if before.author.avatar: e.set_author(name=before.author, icon_url=before.author.avatar.url)
        else: e.set_author(name=before.author)
        e.add_field(name="Before", value=before.content, inline=False)
        if before.attachments:
            y = [x.url for x in before.attachments]
            e.add_field(name="Attachments", value="\n".join(y), inline=False)
    if after:
        e.add_field(name="After", value=after.content, inline=False)
        if after.attachments:
            y = [x.url for x in after.attachments]
            e.add_field(name="Attachments", value="\n".join(y), inline=False)
    else: e.add_field(name="After", value="*Original message was deleted*", inline=False)
    return e

async def add_player_db(user_id: int):
    data = {
        "user_id": user_id,
        "silent_mode": False,
        "msg_content_ok": False,
        "social_credit_score": 0,
    }
    await mycol.insert_one(data)
    return data

async def fetch_player_db(user_id: int):
    return await mycol.find_one({"user_id":user_id})

async def get_player_db(user_id: int):
    db = await fetch_player_db(user_id)
    if db: return db
    return await add_player_db(user_id)

async def update_player(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"social_credit_score": data}})

async def set_player_silent(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"silent_mode": data}})

async def set_player_consent(user_id: int, data):
    await mycol.update_one({"user_id":user_id}, {"$set": {"msg_content_ok": data}})

class TiananmenSquare1989Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def get(self, ctx: commands.Context):
    #     print(await get_player_db(ctx.author.id))

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} {description_helper['utils']['log']}")
    @app_commands.describe(channel_id="Channel ID of the channel you wish to become THE MESSAGE LOGGING CENTER!")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def log(self, ctx: commands.Context, channel_id: str=None):
        await exceute_log_channel(ctx, channel_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(TiananmenSquare1989Cog(bot))