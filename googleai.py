from discord.ext import commands
import discord
from discord import app_commands
import aiohttp
import time
import os
import base64
import json
from util_discord import command_check, description_helper, get_guild_prefix

headers = {'Content-Type': 'application/json'}
def palm_proxy(model: str) -> str:
    return f"{os.getenv('PROXY')}/v1beta/models/{model}?key={os.getenv('PALM')}"

def check_response(response_data) -> bool:
    return response_data.get("candidates", []) and \
        response_data["candidates"][0].get("content", {}).get("parts", []) and \
            response_data["candidates"][0]["content"]["parts"][0].get("text", "")

def check_response_palm(response_data) -> bool:
    return response_data.get("candidates", []) and \
        response_data["candidates"][0].get("output", "")

def get_error(response_data) -> str:
    if response_data.get("promptFeedback", {}):
        result = "**Error! :(**\n"
        for entry in response_data.get("promptFeedback", {}).get("safetyRatings", []):
            if entry['probability'] != 'NEGLIGIBLE':
                result += f"{entry['category']}: {entry['probability']}\n"
        return result

    error_message = response_data.get('error', {}).get('message', 'Unknown error')
    error_type = response_data.get('errorType', '')
    return f"**Error! :(**\n{error_message}" if "error" in response_data else f"**Error! :(**\n{error_type}"

def get_error_palm(response_data) -> str:
    if response_data.get('safetyFeedback', []):
        result = "**Error! :(**\n"
        for entry in response_data.get('safetyFeedback', []):
            if entry['rating']['probability'] != 'NEGLIGIBLE':
                result += f"{entry['rating']['category']}: {entry['rating']['probability']}\n"
        return result

    error_message = response_data.get('error', {}).get('message', 'Unknown error')
    error_type = response_data.get('errorType', '')
    return f"**Error! :(**\n{error_message}" if "error" in response_data else f"**Error! :(**\n{error_type}"

def get_text(response_data) -> str:
    # with open('gemini_response.json', 'w') as json_file:
    #     json.dump(response_data, json_file, indent=4)
    # print(f"Response saved to 'gemini_response.json'")
    if check_response(response_data):
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return get_error(response_data)
    
def get_text_palm(response_data) -> str:
    # with open('gemini_response.json', 'w') as json_file:
    #     json.dump(response_data, json_file, indent=4)
    # print(f"Response saved to 'gemini_response.json'")
    if check_response_palm(response_data):
        return response_data["candidates"][0]["output"]
    else:
        return get_error_palm(response_data)

# ugly
def strip_dash(text: str, prefix: str):
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith(prefix) and i != len(words)-1:
            words = words[:i] + words[i+1:]
            break
    return " ".join(words)

# i really love this function, improved
async def loopMsg(message: discord.Message, prefix: str):
    role = "model" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content, prefix)
    if not content: content = "?" # maybe image only, i can't read this message :(
    content = "Hello!" if content and content.startswith(prefix) else content
    base64_data, mime = None, None
    if len(message.attachments) > 0:
        attachment = message.attachments[0]
        image_data = await attachment.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        mime = attachment.content_type
    base_data = [
        {
            "role": role, # check if only user supports images, see perplexity line 65 (update: it doesnt matter)
            "parts": [
                {"text": content},
                {
                    "inline_data": {
                        "mime_type": mime,
                        "data": base64_data
                    }
                } if base64_data else None
            ]
        }
    ]
    if not message.reference: return base_data
    try:
        repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    except:
        print("Exception in loopMsg:googleai")
        return base_data
    previousMessages = await loopMsg(repliedMessage, prefix)
    return previousMessages + base_data

async def json_data(msg: discord.Message, prefix: str):
    messagesArray = await loopMsg(msg, prefix)
    return {"contents": messagesArray}

async def json_data_slash(prompt: str, image: discord.Attachment):
    if image:
        image_data = await image.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        mime = image.content_type
    base_data = [
        {
            "role": "user", 
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime,
                        "data": base64_data
                    }
                } if image else None
            ]
        }
    ]
    return {"contents": base_data}

def json_data_palm(arg: str, safe: bool):
    return {
        "prompt": {
            "text": arg if arg else "Explain who you are, your functions, capabilities, limitations, and purpose."
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_UNSPECIFIED",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DEROGATORY",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_TOXICITY",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_VIOLENCE",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUAL",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_MEDICAL",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE"
            }
        ] if not safe else None,
    }

async def req_real(url, json, headers, palm):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json, headers=headers) as response:
            if response.status == 200:
                return get_text_palm(await response.json()) if palm else get_text(await response.json())
            else: print(await response.content.read())

models_google = [
    # "text-bison-001", # dead
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-2.0-pro-exp-02-05",
    "gemini-2.0-flash-thinking-exp-01-21",
]

async def GEMINI_REST(ctx: commands.Context | discord.Interaction, model: str, prompt: str=None, image: discord.Attachment=None,
                      debug: bool=True, palm: bool=False):
    if await command_check(ctx, "googleai", "ai"):
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
    text = None
    prefix = await get_guild_prefix(ctx)
    # rewrite
    if palm:
        proxy = palm_proxy(f"{model}:generateText")
        payload = json_data_palm(strip_dash(ctx.message.content, prefix), not ctx.channel.nsfw)
    else:
        proxy = palm_proxy(f"{model}:generateContent")
        payload = await json_data(ctx.message, prefix) if not prompt else await json_data_slash(prompt, image)
    text = await req_real(proxy, payload, headers, palm)
    # silly
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
    if not debug: return
    done = f"{model}\n**Took {round(time.time() * 1000)-old}ms**"
    if isinstance(ctx, commands.Context):
        await msg.edit(content=done)
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=done)

async def help_google(ctx: commands.Context):
    if await command_check(ctx, "googleai", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text  = [
        f"`{p}gemini` {models_google[2]}",
        f"`{p}flash` {models_google[3]}",
        f"`{p}think` {models_google[6]}",
        # f"`{p}palm` {models[0]}"
    ]
    await ctx.reply("\n".join(text))

class CogGoogle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def palm(self, ctx: commands.Context):
    #     await GEMINI_REST(ctx, 0, True)

    @commands.command(aliases=["ge"]) # alias
    async def gemini(self, ctx: commands.Context):
        await GEMINI_REST(ctx, models_google[2])

    # @app_commands.command(name="gemini", description=f"{description_helper['emojis']['ai']} {models_google[0]}")
    # @app_commands.describe(prompt="Text prompt", image="Image prompt")
    # @app_commands.allowed_installs(guilds=True, users=True)
    # @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # async def gemini_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None):
    #     await GEMINI_REST(ctx, models_google[0], prompt, image)

    @commands.command()
    async def flash(self, ctx: commands.Context):
        await GEMINI_REST(ctx, models_google[3])

    # @app_commands.command(name="flash", description=f"{description_helper['emojis']['ai']} {models_google[1]}")
    # @app_commands.describe(prompt="Text prompt", image="Image prompt")
    # @app_commands.allowed_installs(guilds=True, users=True)
    # @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # async def flash_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None):
    #     await GEMINI_REST(ctx, models_google[1], prompt, image)

    @commands.command()
    async def think(self, ctx: commands.Context):
        await GEMINI_REST(ctx, models_google[6])

    @commands.command()
    async def googleai(self, ctx: commands.Context):
        await help_google(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogGoogle(bot))