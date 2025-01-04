import discord
from discord import app_commands
from discord.ext import commands
from util_discord import command_check, check_if_master_or_admin, description_helper
from util_database import set_ai_mode, get_database2, set_ai_rate
from googleai import models_google, GEMINI_REST
from perplexity import models_mistral, models_groq, models_github, main_mistral, main_groq, main_github
models_master = models_google + models_mistral + models_groq + models_github + ["off"]

async def ai_respond_mode(ctx: commands.Context, model: str):
    if await command_check(ctx, "aimode", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    id = ctx.guild.id if ctx.guild else ctx.channel.id
    db = await get_database2(id) # please be good

    if not model in models_master: return await ctx.reply(f"Model not found.\n\nAvailable models:\n```{'\n'.join(models_master)}```")
    if model != "off":
        await set_ai_mode(id, model)
        await ctx.reply(f"{model} has been set as my default response mode. talk to me and see what happens.")
    else:
        await set_ai_mode(id, "") # tsundere mode
        await ctx.reply(f"ai response mode has been disabled. talk to me and i'll roast you instead.")

async def ted_talk_response(ctx: commands.Context, model):
    async with ctx.typing(): # users and discord itself will hate me for this
        if model in models_google:
            await GEMINI_REST(ctx, model, debug=False)
        if model in models_mistral:
            await main_mistral(ctx, model, debug=False)
        if model in models_groq:
            await main_groq(ctx, model, debug=False)
        if model in models_github:
            await main_github(ctx, model, debug=False)
            
async def ai_respond_rate(ctx: commands.Context, rate: str):
    if await command_check(ctx, "aimode", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    id = ctx.guild.id if ctx.guild else ctx.channel.id
    db = await get_database2(id) # please be good
    
    if not rate.isdigit(): return await ctx.reply("not a digit :(")
    rate = fix_num(rate)
    await set_ai_rate(id, rate)
    await ctx.reply(f"ai response mode rate is now set to `{rate}%`")
    
def fix_num(num):
    num = int(num)
    if num < 0: num = 0
    elif num > 100: num = 100
    return num

async def model_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=model, value=model) for model in models_master if current.lower() in model.lower()
    ][:25]

class AIModeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} {description_helper['utils']['aimode']}")
    @app_commands.describe(model="Large language model")
    @app_commands.autocomplete(model=model_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def aimode(self, ctx: commands.Context, model: str=None):
        await ai_respond_mode(ctx, model)
        
    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Set AI mode message rate")
    @app_commands.describe(rate="Random message rate")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def airate(self, ctx: commands.Context, rate: str="1"):
        await ai_respond_rate(ctx, rate)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIModeCog(bot))