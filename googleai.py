from discord.ext import commands
import discord
import aiohttp
import time
import os
import base64
import json
from util_discord import command_check

headers = {'Content-Type': 'application/json'}
def palm_proxy(model: str) -> str:
    return f"{os.getenv('PROXY')}v1beta/models/{model}?key={os.getenv('PALM')}"

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
def strip_dash(text: str):
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith("-") and i != len(words)-1:
            words = words[:i] + words[i+1:]
            break
    return " ".join(words)

# i really love this function, improved
async def loopMsg(message: discord.Message):
    role = "model" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content)
    content = "Hello!" if content and content[0] == "-" else content
    base64_data, mime = None, None
    if len(message.attachments) > 0:
        attachment = message.attachments[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                image_data = await resp.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                base64_data, mime = base64_data, attachment.content_type
    base_data = [
        {
            "role": role, 
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
    repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    previousMessages = await loopMsg(repliedMessage)
    return previousMessages + base_data
    
async def json_data(msg: discord.Message):
    messagesArray = await loopMsg(msg)
    return {"contents": messagesArray}

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

models = [
    "text-bison-001",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

async def GEMINI_REST(ctx: commands.Context, model: int, palm: bool):
    if await command_check(ctx, "googleai", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        text = None
        # rewrite
        if palm:
            proxy = palm_proxy(f"{models[model]}:generateText")
            payload = json_data_palm(strip_dash(ctx.message.content), not ctx.channel.nsfw)
        else:
            proxy = palm_proxy(f"{models[model]}:generateContent")
            payload = await json_data(ctx.message)
        text = await req_real(proxy, payload, headers, palm)
        # silly
        if not text: return await msg.edit(content=f"**Error! :(**")
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        replyFirst = True
        for chunk in chunks:
            if replyFirst: 
                replyFirst = False
                await ctx.reply(chunk)
            else: await ctx.send(chunk)
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

async def help_google(ctx: commands.Context):
    if await command_check(ctx, "googleai", "ai"): return
    text  = [
        f"`-ge` {models[1]}",
        f"`-flash` {models[2]}",
        f"`-palm` {models[0]}"
    ]
    await ctx.reply("\n".join(text))