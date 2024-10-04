from discord.ext import commands
from discord import app_commands
from util_discord import command_check, description_helper

async def avatar_function(ctx: commands.Context, bot: commands.Bot, arg: str):
    if await command_check(ctx, "av", "utils"): return
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.avatar: return await ctx.reply(user.avatar.url)
    except: pass
    await ctx.reply("There is no such thing.")

async def banner_function(ctx: commands.Context, bot: commands.Bot, arg: str):
    if await command_check(ctx, "ban", "utils"): return
    if arg and not arg.isdigit(): return await ctx.reply("Must be a valid user ID.")
    try:
        user = await bot.fetch_user(int(arg) if arg else ctx.author.id)
        if user and user.banner: return await ctx.reply(user.banner.url)
    except: pass
    await ctx.reply("There is no such thing.")

class DiscordUtilMember(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["banner"]}')
    @app_commands.describe(user_id="User ID of the user you want to see the banner of")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def banner(self, ctx: commands.Context, *, user_id:str=None):
        await banner_function(ctx, self.bot, user_id)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["utils"]} {description_helper["utils"]["avatar"]}')
    @app_commands.describe(user_id="User ID of the user you want to see the avatar of")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, ctx: commands.Context, *, user_id:str=None):
        await avatar_function(ctx, self.bot, user_id)

    @commands.command()
    async def av(self, ctx: commands.Context, *, user_id:str=None):
        await avatar_function(ctx, self.bot, user_id)

    @commands.command()
    async def ban(self, ctx: commands.Context, *, user_id:str=None):
        await banner_function(ctx, self.bot, user_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordUtilMember(bot))