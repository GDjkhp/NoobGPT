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
def palm_proxy(model) -> str:
    return f"{os.getenv('PROXY')}v1/models/{model}:generateContent?key={os.getenv('PALM')}"

async def GEMINI_REST(ctx: commands.Context, arg: str):
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
                        base64_image_data = base64.b64encode(image_data).decode('utf-8')
                        data = {
                            "contents": [
                                {
                                    "parts": [
                                        {"text": arg if arg else 'What is this a picture of?'},
                                        {
                                            "inline_data": {
                                                "mime_type": "image/jpeg",
                                                "data": base64_image_data
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                        response = requests.post(palm_proxy("gemini-pro-vision"), headers=headers, json=data)
                        response_data = response.json()
                        try:
                            if "error" not in response_data:
                                text = response_data.get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                            else:
                                text = f"**Error! :(**\n{response_data.get('error', {}).get('message', 'Unknown error')}"
                        except Exception as e:
                            # with open('gemini_response.json', 'w') as json_file:
                            #     json.dump(response.json(), json_file, indent=4)
                            # print(f"Response saved to 'gemini_response.json'")
                            text = f"**Error! :(**\n{response_data.get('errorType', '')}"
        # text
        else:
            if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose." # if nothing was supplied
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": arg}
                        ]
                    }
                ]
            }
            response = requests.post(palm_proxy("gemini-pro"), headers=headers, json=data)
            response_data = response.json()
            try:
                if "error" not in response_data:
                    text = response_data.get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                else:
                    text = f"**Error! :(**\n{response_data.get('error', {}).get('message', 'Unknown error')}"
            except Exception as e: 
                # with open('gemini_response.json', 'w') as json_file:
                #     json.dump(response.json(), json_file, indent=4)
                # print(f"Response saved to 'gemini_response.json'")
                text = f"**Error! :(**\n{response_data.get('errorType', '')}"
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