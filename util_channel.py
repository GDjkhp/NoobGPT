import discord
from discord.ext import commands
from util_discord import check_if_master_or_admin, command_check
master_perm = discord.PermissionOverwrite(manage_permissions=True, view_channel=True)

async def create_sus_txtchannel(ctx: commands.Context, name: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "channel", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.administrator:
        return await ctx.reply("**THIS FEATURE REQUIRES ADMIN PERMS FOR NOOBGPT :(**")
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.guild.me: master_perm,
        ctx.author: master_perm
    }
    channel = await ctx.guild.create_text_channel(name, overwrites=overwrites, category=ctx.channel.category)
    await ctx.reply(f"{channel.jump_url} has been created privately")

async def create_sus_vchannel(ctx: commands.Context, name: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "channel", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.administrator:
        return await ctx.reply("**THIS FEATURE REQUIRES ADMIN PERMS FOR NOOBGPT :(**")
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.guild.me: master_perm,
        ctx.author: master_perm
    }
    channel = await ctx.guild.create_voice_channel(name, overwrites=overwrites, category=ctx.channel.category)
    await ctx.reply(f"{channel.jump_url} has been created privately")

async def add_member_to_sus(ctx: commands.Context, user_ids: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "channel", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.administrator:
        return await ctx.reply("**THIS FEATURE REQUIRES ADMIN PERMS FOR NOOBGPT :(**")
    success = False
    for user_id in user_ids.split():
        if not user_id or not user_id.isdigit(): continue
        mem = ctx.guild.get_member(int(user_id))
        if not mem: continue
        await ctx.channel.set_permissions(mem, view_channel=True)
        await ctx.reply(f"<@{user_id}> has been added to the group chat")
        success = True
    if not success: await ctx.reply(":(")

async def add_role_to_sus(ctx: commands.Context, role_ids: str):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "channel", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.administrator:
        return await ctx.reply("**THIS FEATURE REQUIRES ADMIN PERMS FOR NOOBGPT :(**")
    success = False
    for role_id in role_ids.split():
        if not role_id or not role_id.isdigit(): return await ctx.reply(":(")
        role = ctx.guild.get_role(int(role_id))
        if not role: return await ctx.reply(":(")
        await ctx.channel.set_permissions(role, view_channel=True)
        await ctx.reply(f"<@&{role_id}> has been added to the group chat")
        success = True
    if not success: await ctx.reply(":(")

class CogPChan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ptext(self, ctx: commands.Context, *, name: str=None):
        await create_sus_txtchannel(ctx, name)

    @commands.command()
    async def pvoice(self, ctx: commands.Context, *, name: str=None):
        await create_sus_vchannel(ctx, name)

    @commands.command()
    async def adduser(self, ctx: commands.Context, *, id: str=None):
        await add_member_to_sus(ctx, id)

    @commands.command()
    async def addrole(self, ctx: commands.Context, *, id: str=None):
        await add_role_to_sus(ctx, id)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogPChan(bot))