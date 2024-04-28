from discord.ext import commands
import aiohttp
import time
import os
import requests
import base64
import json

# bard (legacy)
from bard import Bard
cookie_dict = {
    "__Secure-1PSID": os.getenv("BARD"),
    "__Secure-1PSIDTS": os.getenv("BARD0"),
    # Any cookie values you want to pass session object.
}
async def BARD(ctx: commands.Context, arg: str):
    msg = await ctx.reply("Generating response…")
    old = round(time.time() * 1000)
    try: response = Bard(cookie_dict=cookie_dict, timeout=60).get_answer(arg)
    except Exception as e: return await msg.edit(content=f"**Error! :(**\n{e}")
    await ctx.reply(response['content'][:2000])
    if response['images']:
        img = list(response['images'])
        for i in range(len(img)):
            await ctx.reply(img[i])
    await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

# palm (alternative to bard)
import google.generativeai as PALM
PALM.configure(api_key=os.getenv("PALM"))
async def PALM_LEGACY(ctx: commands.Context, arg: str):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose."
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        try: 
            text = PALM.generate_text(prompt=arg).result
            if not text: return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            replyFirst = True
            for chunk in chunks:
                if replyFirst: 
                    replyFirst = False
                    await ctx.reply(chunk)
                else: await ctx.send(chunk)
        except Exception as e: return await msg.edit(content=f"**Error! :(**\n{e}")
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

# gemini
import google.generativeai as genai
genai.configure(api_key=os.getenv("PALM"))
text_model = genai.GenerativeModel(model_name="gemini-pro")
image_model = genai.GenerativeModel(model_name="gemini-pro-vision")
async def GEMINI(ctx: commands.Context, arg: str):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        text = None
        # image
        if len(ctx.message.attachments) > 0:
            attachment = ctx.message.attachments[0]
            if attachment.width is not None:  # Checking if the attachment is an image
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        image_data = await resp.read()
                        image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
                        prompt_parts = [image_parts[0], arg if arg else 'What is this a picture of?']
                        try: text = image_model.generate_content(prompt_parts).text
                        except Exception as e: text = f"**Error! :(**\n{e}"
        # text
        else:
            if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose." # if nothing was supplied
            try: text = text_model.generate_content(arg).text
            except Exception as e: text = f"**Error! :(**\n{e}"
        try: 
            if not text: return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            replyFirst = True
            for chunk in chunks:
                if replyFirst: 
                    replyFirst = False
                    await ctx.reply(chunk)
                else: await ctx.send(chunk)
        except Exception as e: return await msg.edit(content=f"**Error! :(**\n{e}")
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

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
    
def json_data(arg, base64_data=None, mime=None):
    if not arg:
        arg_text = "Explain who you are, your functions, capabilities, limitations, and purpose."
        arg_image_text = 'What is this?'
    else:
        arg_text = arg
        arg_image_text = arg
    return {
        "contents": [
            {
                "parts": [
                    {"text": arg_text if not base64_data else arg_image_text},
                    {
                        "inline_data": {
                            "mime_type": mime,
                            "data": base64_data
                        }
                    } if base64_data else None
                ]
            }
        ]
    }

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
            else:
                print(await response.content.read())
                return None

async def GEMINI_REST(ctx: commands.Context, arg: str, palm: bool):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        text = None
        # rewrite
        proxy = palm_proxy("gemini-1.5-pro-latest:generateContent")
        payload = json_data(arg)
        if not palm:
            if len(ctx.message.attachments) > 0:
                attachment = ctx.message.attachments[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        image_data = await resp.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        payload = json_data(arg, base64_data, attachment.content_type)
        else:
            proxy = palm_proxy("text-bison-001:generateText")
            payload = json_data_palm(arg, not ctx.channel.nsfw)
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