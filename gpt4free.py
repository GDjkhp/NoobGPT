import io, base64
import time
import discord
from discord import app_commands
from discord.ext import commands
from util_discord import description_helper, command_check, get_guild_prefix, check_if_not_owner
from perplexity import loopMsgGH, loopMsgSlash, strip_dash
from g4f.client import AsyncClient
client = AsyncClient()
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]

async def get_models():
    cursor = mycol.find()
    data = await cursor.to_list(None)
    if data: return data[0]["ai_txt"], data[0]["ai_img"]

async def get_models_default():
    cursor = mycol.find()
    data = await cursor.to_list(None)
    if data: return data[0]["ai_txt_default"], data[0]["ai_img_default"]

async def set_models(ctx: commands.Context, mode: str, arg: str):
    model_list = arg.split()
    await mycol.update_one({}, {"$set": {mode: model_list}})
    text = f"{mode}: {model_list}"
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else: await ctx.send(chunk)

async def set_models_default(ctx: commands.Context, mode: str, arg: str):
    await mycol.update_one({}, {"$set": {mode: arg}})
    text = f"{mode}: {arg}"
    await ctx.reply(text)

async def the_free_req_img(prompt: str, model: str):
    response = await client.images.generate(
        prompt=prompt,
        model=model,
        response_format="b64_json"
    )
    return response.data[0].b64_json
    
async def the_free_req_text(msgs: list, model: str):
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Be precise and concise."
            }
        ] + msgs,
        web_search=True
    )
    return response.choices[0].message.content

async def free_image(ctx: commands.Context | discord.Interaction, model: str,
                     prompt: str=None, debug: bool=True):
    if await command_check(ctx, "g4f", "ai"):
        warn = "command disabled"
        if isinstance(ctx, commands.Context):
            return await ctx.reply(warn, ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(warn, ephemeral=True)
    # async with ctx.typing():
    if debug:
        nfo = f"{model}\nGenerating image…"
        if isinstance(ctx, commands.Context):
            msg = await ctx.reply(nfo)
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(nfo)
    old = round(time.time() * 1000)
    try:
        if not prompt: # not a slash
            message = ctx.message
            if message:
                prompt = message.content
                if prompt:
                    p = await get_guild_prefix(ctx)
                    prompt = strip_dash(prompt, p)
                else: prompt = ""
                if message.reference: # reply hack
                    hey = await message.channel.fetch_message(message.reference.message_id)
                    if hey.content: prompt = f"{prompt}: {strip_dash(hey.content, p)}" # depth 1, dont you dare overload tokens
        if not prompt: prompt = "Generate something" # force
        b64 = await the_free_req_img(prompt, model)
        file = discord.File(io.BytesIO(base64.b64decode(b64)), filename="image.jpeg")
        if isinstance(ctx, discord.Interaction): await ctx.followup.send(file=file)
        if isinstance(ctx, commands.Context): await ctx.reply(file=file)
    except Exception as e:
        print(e)
        if not debug: return
        err = f"**Error! :(**"
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=err)
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=err)
    if not debug: return
    done = f"{model}\n**Took {round(time.time() * 1000)-old}ms**"
    if isinstance(ctx, commands.Context):
        await msg.edit(content=done)
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=done)
    
async def free_text(ctx: commands.Context | discord.Interaction, model: str,
                    prompt: str=None, image: discord.Attachment=None, debug: bool=True):
    if await command_check(ctx, "g4f", "ai"):
        warn = "command disabled"
        if isinstance(ctx, commands.Context):
            return await ctx.reply(warn, ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(warn, ephemeral=True)
    # async with ctx.typing():
    if debug:
        nfo = f"{model}\nGenerating response…"
        if isinstance(ctx, commands.Context):
            msg = await ctx.reply(nfo)
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(nfo)
    old = round(time.time() * 1000)
    try:
        messages = await loopMsgGH(ctx.message, await get_guild_prefix(ctx)) if not prompt else await loopMsgSlash(prompt, image)
        text = await the_free_req_text(messages, model)
        if not text:
            if not debug: return
            err = f"**Error! :(**\nEmpty response."
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=err)
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=err)
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        replyFirst = True
        for chunk in chunks:
            if isinstance(ctx, discord.Interaction): await ctx.followup.send(chunk)
            if isinstance(ctx, commands.Context):
                if replyFirst:
                    replyFirst = False
                    await ctx.reply(chunk)
                else:
                    await ctx.send(chunk)
    except Exception as e:
        print(e)
        if not debug: return
        err = f"**Error! :(**"
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=err)
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=err)
    if not debug: return
    done = f"{model}\n**Took {round(time.time() * 1000)-old}ms**"
    if isinstance(ctx, commands.Context):
        await msg.edit(content=done)
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=done)
    
def noobgpt_cleaner(ctx: commands.Context, text: str):
    mod_text = text.lower()
    name_table = ["noobgpt"]
    if ctx.guild:
        user: discord.Member = ctx.guild.me
        if user.nick: name_table.append(user.nick.lower())
    for name in name_table:
        if name in text: mod_text = mod_text.replace(name, "")
    return mod_text

# DONUT USE: AI is advancing at the sp[e]ed of light
async def build_help(current: str=None):
    models_text, models_image = await get_models()
    def format_model(model: str) -> str:
        if current and model.lower() == current.lower():
            return f"> {model}"
        return f"* {model}"
    model_collect_text = '\n'.join(format_model(model) for model in models_text)
    model_collect_image = '\n'.join(format_model(model) for model in models_image)
    help_thing = [
        "# Text models",
        f"```md\n{model_collect_text}\n```",
        "# Image models",
        f"```md\n{model_collect_image}\n```",
    ]
    return help_thing

async def g4f_help(ctx: commands.Context):
    if await command_check(ctx, "g4f", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    DEFAULT_TXT, DEFAULT_IMG = await get_models_default()
    final_text = [
        "# Get started",
        f"`-ask <prompt>` text generation (defaults to `{DEFAULT_TXT}`)",
        f"`-imagine <prompt>` image generation (defaults to `{DEFAULT_IMG}`)",
        "# Advanced",
        "* Use `/ask` and `/imagine` to switch models",
        "* Check out `-aimode` to set up AI responses on mentions",
    ]
    await ctx.reply("\n".join(final_text))

async def model_img_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    models_text, models_image = await get_models()
    return [
        app_commands.Choice(name=model, value=model) for model in models_image if current.lower() in model.lower()
    ][:25]

async def model_txt_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    models_text, models_image = await get_models()
    return [
        app_commands.Choice(name=model, value=model) for model in models_text if current.lower() in model.lower()
    ][:25]

class GPT4UCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description=f"{description_helper['emojis']['ai']} GPT4Free Text Completion")
    @app_commands.describe(model="Large language model", prompt="Text prompt", image="Image prompt")
    @app_commands.autocomplete(model=model_txt_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gpt_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None, model: str=None):
        if not model:
            DEFAULT_TXT, _ = await get_models_default()
            model = DEFAULT_TXT
        await free_text(ctx, model, prompt, image)

    @app_commands.command(name="imagine", description=f"{description_helper['emojis']['ai']} GPT4Free Image Generation")
    @app_commands.describe(model="Text-to-Image model", prompt="Text prompt")
    @app_commands.autocomplete(model=model_img_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def imagine_slash(self, ctx: discord.Interaction, prompt: str, model: str=None):
        if not model:
            _, DEFAULT_IMG = await get_models_default()
            model = DEFAULT_IMG
        await free_image(ctx, model, prompt)

    @commands.command(aliases=["gpt"])
    async def ask(self, ctx: commands.Context):
        DEFAULT_TXT, _ = await get_models_default()
        await free_text(ctx, DEFAULT_TXT)

    @commands.command()
    async def imagine(self, ctx: commands.Context):
        _, DEFAULT_IMG = await get_models_default()
        await free_image(ctx, DEFAULT_IMG)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["ai"]} {description_helper["ai"]["g4f"]}'[:100])
    async def g4f(self, ctx: commands.Context):
        await g4f_help(ctx)

    @commands.command()
    async def aiimg(self, ctx: commands.Context, *, models):
        if check_if_not_owner(ctx): return
        await set_models(ctx, "ai_img", models)

    @commands.command()
    async def aitxt(self, ctx: commands.Context, *, models):
        if check_if_not_owner(ctx): return
        await set_models(ctx, "ai_txt", models)

    @commands.command()
    async def aiimgdef(self, ctx: commands.Context, model: str):
        if check_if_not_owner(ctx): return
        await set_models_default(ctx, "ai_img_default", model)

    @commands.command()
    async def aitxtdef(self, ctx: commands.Context, model: str):
        if check_if_not_owner(ctx): return
        await set_models_default(ctx, "ai_txt_default", model)

async def setup(bot: commands.Bot):
    await bot.add_cog(GPT4UCog(bot))