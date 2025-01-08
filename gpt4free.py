import io, base64
import time
import discord
from discord import app_commands
from discord.ext import commands
from util_discord import model_helper, description_helper, command_check, get_guild_prefix
from perplexity import loopMsgGH, loopMsgSlash, strip_dash
from g4f.client import AsyncClient
client = AsyncClient()

models_image = model_helper["models_image"]
models_text = model_helper["models_text"]

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
        nfo = f"{model}\nGenerating response…"
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
    
async def model_img_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=model, value=model) for model in models_image if current.lower() in model.lower()
    ][:25]

async def model_txt_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=model, value=model) for model in models_text if current.lower() in model.lower()
    ][:25]

class GPT4UCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gpt", description=f"{description_helper['emojis']['ai']} GPT4Free Text Completion")
    @app_commands.describe(model="Large language model")
    @app_commands.autocomplete(model=model_txt_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gpt_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None, model: str="gpt-4o"):
        await free_text(ctx, model, prompt, image)

    @app_commands.command(name="imagine", description=f"{description_helper['emojis']['ai']} GPT4Free Image Generation")
    @app_commands.describe(model="Image model")
    @app_commands.autocomplete(model=model_img_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def imagine_slash(self, ctx: discord.Interaction, prompt: str, model: str="flux"):
        await free_image(ctx, model, prompt)

    @commands.command()
    async def gpt(self, ctx: commands.Context):
        await free_text(ctx, "gpt-4o")

    @commands.command()
    async def imagine(self, ctx: commands.Context):
        await free_image(ctx, "flux")

async def setup(bot: commands.Bot):
    await bot.add_cog(GPT4UCog(bot))