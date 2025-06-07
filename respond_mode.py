import discord
from discord import app_commands
from discord.ext import commands
from c_ai_discord import fix_num
from util_discord import command_check, check_if_master_or_admin, description_helper
from util_database import get_database2, set_ai_mode, set_ai_rate, set_ai_mention
from googleai import models_google, GEMINI_REST
from perplexity import models_mistral, models_groq, models_github, main_mistral, main_groq, main_github
from gpt4free import get_models, free_image, free_text, build_help

async def ai_respond_mode(ctx: commands.Context, model: str):
    if await command_check(ctx, "aimode", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    id = ctx.guild.id if ctx.guild else ctx.channel.id
    db = await get_database2(id)
    models_text, models_image = await get_models()
    models_master = models_text + models_image + ["off"]
    if not model in models_master:
        final_text = [
            "# Configuration",
            f'Current model: `{db["ai_mode"] if db.get("ai_mode") and db["ai_mode"] else None}`',
            f'Mention mode: `{db["ai_mention"] if db.get("ai_mention") else False}`',
            f'Response rate: `{db["ai_rate"] if db.get("ai_rate") else 0}%`',
            "# Get started",
            "* `-aimode <model>` setup ai",
            "  * Use `-aimode off` to disable AI response (reverts to `-insult`)\n",
            "* `-airate <0-100>` set response rate",
            "  * `0` = mute",
            "  * `100` = always respond\n",
            "* `-aimention` set response mention",
            "  * `True` = always active: read message, if name/nickname mentioned in text, respond",
            "  * `False` = respond only on pings",
        ]
        return await ctx.reply("\n".join(final_text))
    if model != "off":
        await set_ai_mode(id, model)
        await ctx.reply(f"`{model}` has been set as my default response mode. talk to me and see what happens.")
    else:
        await set_ai_mode(id, "") # tsundere mode
        await ctx.reply(f"ai response mode has been disabled. talk to me and i'll roast you instead.")

async def ted_talk_response(ctx: commands.Context, model):
    if await command_check(ctx, "g4f", "ai"):  return
    async with ctx.typing(): # users and discord itself will hate me for this
        models_text, models_image = await get_models()
        if model in models_text:
            return await free_text(ctx, model, debug=False)
        if model in models_image:
            return await free_image(ctx, model, debug=False)
        if model in models_google:
            return await GEMINI_REST(ctx, model, debug=False)
        if model in models_mistral:
            return await main_mistral(ctx, model, debug=False)
        if model in models_groq:
            return await main_groq(ctx, model, debug=False)
        if model in models_github:
            return await main_github(ctx, model, debug=False)

async def ai_respond_rate(ctx: commands.Context, rate: str):
    if await command_check(ctx, "aimode", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    id = ctx.guild.id if ctx.guild else ctx.channel.id
    db = await get_database2(id) # please be good
    
    if not rate.isdigit(): return await ctx.reply("not a digit :(")
    rate = fix_num(rate)
    await set_ai_rate(id, rate)
    adv_info = f"ai response mode rate is now set to `{rate}%`"
    if rate == 0: adv_info += "\ni will only respond to mentions"
    await ctx.reply(adv_info)

async def ai_respond_mention(ctx: commands.Context):
    if await command_check(ctx, "aimode", "utils"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin", ephemeral=True)
    id = ctx.guild.id if ctx.guild else ctx.channel.id
    db = await get_database2(id) # i need this

    b = db["ai_mention"] if db.get("ai_mention") else False
    await set_ai_mention(id, not b)
    await ctx.reply(f"ai mode mention is now `{not b}`")

async def model_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    models_text, models_image = await get_models()
    models_master = models_text + models_image + ["off"]
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
        
    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} Set AI mode mention setting")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def aimention(self, ctx: commands.Context):
        await ai_respond_mention(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIModeCog(bot))