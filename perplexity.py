import aiohttp
import os
import discord
from discord import app_commands
from discord.ext import commands
import time
import base64
import re
from util_discord import command_check, description_helper, get_guild_prefix

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
    role = "assistant" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content, prefix)
    content = "Hello!" if content and content.startswith(prefix) else content
    base_data = [{"role": role, "content": content}]
    if not message.reference: return base_data
    try:
        repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    except:
        print("Exception in loopMsg:perplexity")
        return base_data
    previousMessages = await loopMsg(repliedMessage, prefix)
    return previousMessages + base_data

async def loopMsgSlash(prompt: str, image: discord.Attachment=None):
    data = [{"role": "user", "content": prompt}]
    if image:
        image_data = await image.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        # data[0]["data"]={"imageBase64": f"data:image/jpeg;base64,{base64_data}"} # blackbox
        data[0]["content"]+=[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_data}"}}] # openai/github
    return data

async def loopMsgGH(message: discord.Message, prefix: str):
    role = "assistant" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content, prefix)
    
    # vision support?
    base64_data = None
    if len(message.attachments) > 0:
        attachment = message.attachments[0]
        image_data = await attachment.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        content = "What’s in this image?" if content and content.startswith(prefix) else content
    content = "Hello!" if content and content.startswith(prefix) else content # if none is supplied

    base_data = [{
        "role": role, 
        "content": [{"type": "text", "text": content}]
    }]
    if base64_data:
        base_data[0]["content"]+=[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_data}"}}]

    if not message.reference: return base_data
    try:
        repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    except:
        print("Exception in loopMsgGH")
        return base_data
    previousMessages = await loopMsgGH(repliedMessage, prefix)
    return previousMessages + base_data

def remove_lines(text: str):
    lines = text.split('\n')
    if len(lines) >= 5:
        return lines[4]
    else:
        return text

models = [
    "llama-2-70b-chat", # ll
    "codellama-70b-instruct", # cll
    "mistral-7b-instruct", # mis
    "mixtral-8x7b-instruct", # mix
    "sonar-small-chat", # ssc
    "sonar-small-online", # sso
    "sonar-medium-chat", # smc
    "sonar-medium-online", #smo
]
models_claude=[
    "claude-2.1", # cla
    "claude-3-opus-20240229", # c3o
    "claude-3-sonnet-20240229", #c3s
]
models_mistral=[
    "open-mistral-7b", # m7b
    "open-mixtral-8x7b", # mx7b
    "open-mixtral-8x22b", # mx22b
    "mistral-small-latest", # ms
    "mistral-medium-latest", # mm
    "mistral-large-latest", # ml
    "codestral-latest", # mcode
]
models_groq=[
    "llama-3.1-405b-reasoning", # l31405
    "llama-3.1-70b-versatile", # l3170
    "llama-3.1-8b-instant", # l318
    "llama3-70b-8192", # l370
    "llama3-8b-8192", # l38
    "mixtral-8x7b-32768", # mix7b
    "gemma-7b-it", # g7b
    "gemma2-9b-it", # g29b
]
models_github=[
    "gpt-4o",
    "gpt-4o-mini",
    "Meta-Llama-3-70B-Instruct",
    "Meta-Llama-3-8B-Instruct",
    "Meta-Llama-3-1-405B-Instruct",
    "Meta-Llama-3-1-70B-Instruct",
    "Meta-Llama-3-1-8B-Instruct",
    "AI21-Jamba-Instruct",
    "Cohere-command-r",
    "Cohere-command-r-plus",
    "Mistral-large",
    "Mistral-large-2407",
    "Mistral-Nemo",
    "Mistral-small",
    "Phi-3-medium-128k-instruct",
    "Phi-3-medium-4k-instruct",
    "Phi-3-mini-128k-instruct",
    "Phi-3-mini-4k-instruct",
    "Phi-3-small-128k-instruct",
    "Phi-3-small-8k-instruct",
    "Phi-3.5-mini-instruct",
]
models_black=[
    None, # default
    "blackboxai-pro", 
    "gpt-4o", 
    "gemini-pro"
]

async def help_perplexity(ctx: commands.Context):
    if await command_check(ctx, "perplex", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
         f"`{p}ll` {models[0]}",
        f"`{p}cll` {models[1]}",
        f"`{p}mis` {models[2]}",
        f"`{p}mix` {models[3]}",
        f"`{p}ssc` {models[4]}",
        f"`{p}sso` {models[5]}",
        f"`{p}smc` {models[6]}",
        f"`{p}smo` {models[7]}",
    ]
    await ctx.reply("\n".join(text))

async def help_claude(ctx: commands.Context):
    if await command_check(ctx, "claude", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}cla` {models_claude[0]}",
        f"`{p}c3o` {models_claude[1]}",
        f"`{p}c3s` {models_claude[2]}",
    ]
    await ctx.reply("\n".join(text))

async def help_mistral(ctx: commands.Context):
    if await command_check(ctx, "mistral", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}m7b` {models_mistral[0]}",
        f"`{p}mx7b` {models_mistral[1]}",
        f"`{p}mx22b` {models_mistral[2]}",
        f"`{p}ms` {models_mistral[3]}",
        f"`{p}mm` {models_mistral[4]}",
        f"`{p}ml` {models_mistral[5]}",
        f"`{p}mcode` {models_mistral[6]}",
    ]
    await ctx.reply("\n".join(text))

async def help_groq(ctx: commands.Context):
    if await command_check(ctx, "groq", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}l31405` {models_groq[0]}",
        f"`{p}l3170` {models_groq[1]}",
        f"`{p}l318` {models_groq[2]}",
        f"`{p}l370` {models_groq[3]}",
        f"`{p}l38` {models_groq[4]}",
        f"`{p}mix7b` {models_groq[5]}",
        f"`{p}g7b` {models_groq[6]}",
        f"`{p}g29b` {models_groq[7]}",
    ]
    await ctx.reply("\n".join(text))

async def help_github(ctx: commands.Context):
    if await command_check(ctx, "github", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}gpt4o` {models_github[0]}",
        f"`{p}gpt4om` {models_github[1]}",
        f"`{p}ai21` {models_github[7]}",
        f"`{p}ccr` {models_github[8]}",
        f"`{p}ccrp` {models_github[9]}",
    ]
    await ctx.reply("\n".join(text))

async def the_real_req(url: str, payload: dict, headers: dict = None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else: print(await response.content.read())

async def the_real_req_black(url: str, payload: dict, headers: dict = None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            text = await response.content.read()
            if response.status == 200:
                return text
            else: print(text.decode())

async def make_request_black(model: str, messages: list, image: bool=False):
    url = "https://www.blackbox.ai/api/chat"
    payload = {
        "messages": messages,
        "agentMode": {
            "id": "ImageGenerationLV45LJp" if image else "" # text-to-image
        },
        "trendingAgentMode": {},
        "maxTokens": 1024,
        "userSelectedModel": model
    }
    return await the_real_req_black(url, payload)

async def make_request(model: str, messages: list, url: str, key: str):
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            }
        ] + messages
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {key}"
    }
    return await the_real_req(url, payload, headers)

async def make_request_claude(model: str, messages: list):
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model, # claude-2.1, claude-instant-1.2
        "max_tokens": 1024,
        "messages": messages
    }
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": os.getenv('ANTHROPIC')
    }
    return await the_real_req(url, payload, headers)

async def make_request_mistral(model: str, messages: list, code: bool):
    url = f"https://api.mistral.ai/v1/{'fim' if code else 'chat'}/completions"
    payload = {
        "model": model,
        "prompt" if code else "messages": messages[0]["content"] if code else messages
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {os.getenv('MISTRAL')}"
    }
    return await the_real_req(url, payload, headers)

async def main_perplexity(ctx: commands.Context | discord.Interaction, model: int):
    if await command_check(ctx, "perplex", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"{models[model]}\nGenerating response…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"{models[model]}\nGenerating response…")
    old = round(time.time() * 1000)
    try:
        url = "https://api.perplexity.ai/chat/completions"
        key = os.getenv('PERPLEXITY')
        messages = await loopMsg(ctx.message, await get_guild_prefix(ctx))
        response = await make_request(models[model], messages, url, key) # spicy
        text = response["choices"][0]["message"]["content"]
        if not text or text == "":
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        # bruh = response["detail"][0]["msg"] if response and response.get("detail") else e
        print(e)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"{models[model]}\n**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"{models[model]}\n**Took {round(time.time() * 1000)-old}ms**")

async def main_github(ctx: commands.Context | discord.Interaction,
                      model: int, prompt: str=None, image: discord.Attachment=None):
    if await command_check(ctx, "github", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"{models_github[model]}\nGenerating response…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"{models_github[model]}\nGenerating response…")
    old = round(time.time() * 1000)
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        key = os.getenv('GITHUB')
        messages = await loopMsgGH(ctx.message, await get_guild_prefix(ctx)) if not prompt else await loopMsgSlash(prompt, image)
        response = await make_request(models_github[model], messages, url, key) # spicy
        text = response["choices"][0]["message"]["content"]
        if not text or text == "":
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        # bruh = response["detail"][0]["msg"] if response and response.get("detail") else e
        print(e)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"{models_github[model]}\n**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"{models_github[model]}\n**Took {round(time.time() * 1000)-old}ms**")

async def main_groq(ctx: commands.Context | discord.Interaction, model: int, prompt: str=None):
    if await command_check(ctx, "groq", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"{models_groq[model]}\nGenerating response…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"{models_groq[model]}\nGenerating response…")
    old = round(time.time() * 1000)
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        key = os.getenv('GROQ')
        messages = await loopMsg(ctx.message, await get_guild_prefix(ctx)) if not prompt else await loopMsgSlash(prompt)
        response = await make_request(models_groq[model], messages, url, key) # spicy
        text = response["choices"][0]["message"]["content"]
        if not text or text == "":
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        # bruh = response["detail"][0]["msg"] if response and response.get("detail") else e
        print(e)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"{models_groq[model]}\n**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"{models_groq[model]}\n**Took {round(time.time() * 1000)-old}ms**")

async def main_anthropic(ctx: commands.Context | discord.Interaction, model: int):
    if await command_check(ctx, "claude", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"{models_claude[model]}\nGenerating response…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"{models_claude[model]}\nGenerating response…")
    old = round(time.time() * 1000)
    try:
        messages = await loopMsg(ctx.message, await get_guild_prefix(ctx))
        response = await make_request_claude(models_claude[model], messages) # spicy
        text = response["content"][0]["text"]
        if not text or text == "":
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        # bruh = response["error"]["message"] if response and response.get("error") else e
        print(e)
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"{models_claude[model]}\n**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"{models_claude[model]}\n**Took {round(time.time() * 1000)-old}ms**")

async def main_mistral(ctx: commands.Context | discord.Interaction, model: int, prompt: str=None):
    if await command_check(ctx, "mistral", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"{models_mistral[model]}\nGenerating response…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"{models_mistral[model]}\nGenerating response…")
    old = round(time.time() * 1000)
    try:
        messages = await loopMsg(ctx.message, await get_guild_prefix(ctx)) if not prompt else await loopMsgSlash(prompt)
        response = await make_request_mistral(models_mistral[model], messages, True if model == 6 else False)
        text = response["choices"][0]["message"]["content"]
        if not text or text == "":
            if isinstance(ctx, commands.Context):
                return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"{models_mistral[model]}\n**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"{models_mistral[model]}\n**Took {round(time.time() * 1000)-old}ms**")

async def main_blackbox(ctx: commands.Context | discord.Interaction, model: int, prompt: str=None, image: bool=False):
    if await command_check(ctx, "blackbox", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply(f"Generating image…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(f"Generating image…")
    old = round(time.time() * 1000)
    try:
        messages = await loopMsg(ctx.message, await get_guild_prefix(ctx)) if not prompt else await loopMsgSlash(prompt)
        response = await make_request_black(model, messages, image)

        if image:
            link = re.search(r'\((http.*?)\)', response.decode()).group(1) # text-to-image
            if isinstance(ctx, discord.Interaction): await ctx.followup.send(link)
            if isinstance(ctx, commands.Context): await ctx.reply(link)
        else:
            text = re.sub(r'^\$@\$\w+=.*\$', '', remove_lines(response.decode())) # not tested
            if not text or text == "":
                if isinstance(ctx, commands.Context):
                    return await msg.edit(content=f"**Error! :(**\nEmpty response.")
                if isinstance(ctx, discord.Interaction):
                    return await ctx.edit_original_response(content=f"**Error! :(**\nEmpty response.")
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
        if isinstance(ctx, commands.Context):
            return await msg.edit(content=f"**Error! :(**")
        if isinstance(ctx, discord.Interaction):
            return await ctx.edit_original_response(content=f"**Error! :(**")
    if isinstance(ctx, commands.Context):
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(content=f"**Took {round(time.time() * 1000)-old}ms**")

class CogPerplex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # HELP
    @commands.command()
    async def claude(self, ctx: commands.Context):
        await help_claude(ctx)

    @commands.command()
    async def mistral(self, ctx: commands.Context):
        await help_mistral(ctx)

    @commands.command()
    async def perplex(self, ctx: commands.Context):
        await help_perplexity(ctx)

    @commands.command()
    async def groq(self, ctx: commands.Context):
        await help_groq(ctx)

    @commands.command()
    async def github(self, ctx: commands.Context):
        await help_github(ctx)

    # MISTRAL
    @commands.command()
    async def m7b(self, ctx: commands.Context):
        await main_mistral(ctx, 0)

    @commands.command()
    async def mx7b(self, ctx: commands.Context):
        await main_mistral(ctx, 1)

    @commands.command()
    async def mx22b(self, ctx: commands.Context):
        await main_mistral(ctx, 2)

    @app_commands.command(name="mixtral", description=f"{description_helper['emojis']['ai']} {models_mistral[2]}")
    @app_commands.describe(prompt="Text prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def mx22b_slash(self, ctx: discord.Interaction, prompt: str):
        await main_mistral(ctx, 2, prompt)

    @commands.command()
    async def ms(self, ctx: commands.Context):
        await main_mistral(ctx, 3)

    @commands.command()
    async def mm(self, ctx: commands.Context):
        await main_mistral(ctx, 4)

    @commands.command()
    async def ml(self, ctx: commands.Context):
        await main_mistral(ctx, 5)

    @app_commands.command(name="mistral", description=f"{description_helper['emojis']['ai']} {models_mistral[5]}")
    @app_commands.describe(prompt="Text prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ml_slash(self, ctx: discord.Interaction, prompt: str):
        await main_mistral(ctx, 5, prompt)

    @commands.command()
    async def mcode(self, ctx: commands.Context):
        await main_mistral(ctx, 6)

    # CLAUDE (DEAD AS FUCK)
    @commands.command()
    async def cla(self, ctx: commands.Context):
        await main_anthropic(ctx, 0)

    @commands.command()
    async def c3o(self, ctx: commands.Context):
        await main_anthropic(ctx, 1)

    @commands.command()
    async def c3s(self, ctx: commands.Context):
        await main_anthropic(ctx, 2)

    # PERPLEXITY (DEAD AS FUCK)
    @commands.command()
    async def ll(self, ctx: commands.Context):
        await main_perplexity(ctx, 0)

    @commands.command()
    async def cll(self, ctx: commands.Context):
        await main_perplexity(ctx, 1)

    @commands.command()
    async def mis(self, ctx: commands.Context):
        await main_perplexity(ctx, 2)

    @commands.command()
    async def mix(self, ctx: commands.Context):
        await main_perplexity(ctx, 3)

    @commands.command()
    async def ssc(self, ctx: commands.Context):
        await main_perplexity(ctx, 4)

    @commands.command()
    async def sso(self, ctx: commands.Context):
        await main_perplexity(ctx, 5)

    @commands.command()
    async def smc(self, ctx: commands.Context):
        await main_perplexity(ctx, 6)

    @commands.command()
    async def smo(self, ctx: commands.Context):
        await main_perplexity(ctx, 7)

    # GROQ
    @commands.command()
    async def l31405(self, ctx: commands.Context):
        await main_groq(ctx, 0)

    @commands.command()
    async def l3170(self, ctx: commands.Context):
        await main_groq(ctx, 1)

    @app_commands.command(name="llama", description=f"{description_helper['emojis']['ai']} {models_groq[1]}")
    @app_commands.describe(prompt="Text prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def l3170_slash(self, ctx: discord.Interaction, prompt: str):
        await main_groq(ctx, 1, prompt)

    @commands.command()
    async def l318(self, ctx: commands.Context):
        await main_groq(ctx, 2)

    @commands.command()
    async def l370(self, ctx: commands.Context):
        await main_groq(ctx, 3)

    @commands.command()
    async def l38(self, ctx: commands.Context):
        await main_groq(ctx, 4)

    @commands.command()
    async def mix7b(self, ctx: commands.Context):
        await main_groq(ctx, 5)

    @commands.command()
    async def g7b(self, ctx: commands.Context):
        await main_groq(ctx, 6)

    @commands.command()
    async def g29b(self, ctx: commands.Context):
        await main_groq(ctx, 7)

    # GITHUB BETA (WIP)
    @commands.command()
    async def gpt4o(self, ctx: commands.Context):
        await main_github(ctx, 0)

    @app_commands.command(name="gpt4o", description=f"{description_helper['emojis']['ai']} {models_github[0]}")
    @app_commands.describe(prompt="Text prompt", image="Image prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gpt4o_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None):
        await main_github(ctx, 0, prompt, image)

    @commands.command()
    async def gpt4om(self, ctx: commands.Context):
        await main_github(ctx, 1)

    @app_commands.command(name="gpt4om", description=f"{description_helper['emojis']['ai']} {models_github[1]}")
    @app_commands.describe(prompt="Text prompt", image="Image prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gpt4om_slash(self, ctx: discord.Interaction, prompt: str, image: discord.Attachment=None):
        await main_github(ctx, 1, prompt, image)

    @commands.command()
    async def ai21(self, ctx: commands.Context):
        await main_github(ctx, 7)

    @commands.command()
    async def ccr(self, ctx: commands.Context):
        await main_github(ctx, 8)

    @commands.command()
    async def ccrp(self, ctx: commands.Context):
        await main_github(ctx, 9)

    # TODO: blackbox
    @commands.command()
    async def flux(self, ctx: commands.Context):
        await main_blackbox(ctx, 0, None, True)

    @app_commands.command(name="flux", description=f"{description_helper['emojis']['ai']} flux")
    @app_commands.describe(prompt="Text prompt")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def flux_slash(self, ctx: discord.Interaction, prompt: str):
        await main_blackbox(ctx, 0, prompt, True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogPerplex(bot))