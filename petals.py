from discord.ext import commands
import time
import aiohttp
import websockets
import json
import re

# list of old models
models = [
    'stabilityai/StableBeluga2',
    'meta-llama/Llama-2-70b-chat-hf',
    'meta-llama/Llama-2-70b-hf',
    'timdettmers/guanaco-65b',
    'huggyllama/llama-65b',
    'bigscience/bloomz',
    'meta-llama/Meta-Llama-3-70B',
    'petals-team/StableBeluga2',
]

# TODO: support read replies (just supply conversation history in inputs, weird)
async def petalsWebsocket(ctx: commands.Context, arg: str, model: int):
    """
    Connects to a WebSocket server and generates text using a specified model.

    This function connects to the WebSocket server at 'wss://chat.petals.dev/api/v2/generate',
    opens an inference session with the 'stabilityai/StableBeluga2' model, and generates text based on
    the given prompt.

    Returns:
        None
    """
    async with ctx.typing():
        msg = await ctx.reply("**Starting session…**")
        if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose."
        text = ""
        text_mod = text_inc = 50
        old = round(time.time() * 1000)
        uri = "wss://chat.petals.dev/api/v2/generate"
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({
                    "type": "open_inference_session",
                    "model": models[model],
                    "max_length": 2000
                }))
                
                await ws.send(json.dumps({
                    "type": "generate",
                    "inputs": f"A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.###Assistant: Hi! How can I help you?###Human: {arg}###Assistant:",
                    "max_new_tokens": 1,
                    "do_sample": 1,
                    "temperature": 0.6,
                    "top_p": 0.9,
                    "extra_stop_sequences": ["</s>"],
                    "stop_sequence": "###"
                }))

                async for message in ws:
                    data = json.loads(message)
                    if data.get("ok"):
                        if data.get("outputs") is None:
                            await msg.edit(content="**Session opened, generating…**")
                        elif not data["stop"]:
                            text += data["outputs"]
                            if len(text)//text_mod!=0: 
                                await msg.edit(content=f"**Generating response…**\nLength: {len(text)}")
                                text_mod += text_inc
                        else: 
                            if text != "": 
                                await send(ctx, text)
                                await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**\nLength: {len(text)}")
                            else: await msg.edit(content=f"**Error! :(**\nEmpty response.\n{PETALS()}")
                            await ws.close()
                    else:
                        print("Error:", data.get("traceback"))
                        # Use regular expressions to extract the error message
                        error_match = re.search(r'Error:(.*?)(?=(\n\s{2,}File|\Z))', data.get("traceback"), re.DOTALL)
                        error_message = "Error message not found."
                        if error_match:
                            error_message = error_match.group(1).strip()
                        if text != "": 
                            await send(ctx, text)
                            await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms and got interrupted with an error.**\n{error_message}\nLength: {len(text)}")
                        else: 
                            await msg.edit(content=f"**Error! :(**\n{error_message}\n{PETALS()}")
                        await ws.close()
        except:
            await msg.edit(content=f"**Error! :(**\nConnection timed out.\n{PETALS()}")

async def send(ctx: commands.Context, text: str):
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else:
            await ctx.send(chunk)

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: print(e)

async def PETALS(ctx: commands.Context):
    status = await req_real("https://health.petals.dev/api/v1/state")
    text = "`-beluga2`: petals-team/StableBeluga2```diff\n"
    for i in status["model_reports"]: 
        text += f"{'+ ' if i['state'] == 'healthy' else '- '}{i['name']}: {i['state']}\n"
    text += "```"
    await ctx.reply(text)