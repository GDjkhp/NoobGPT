from discord.ext import commands
import time
import requests
import websockets
import json

# TODO: support read replies
async def petalsWebsocket(ctx: commands.Context, arg: str, model: str):
    """
    Connects to a WebSocket server and generates text using a specified model.

    This function connects to the WebSocket server at 'wss://chat.petals.dev/api/v2/generate',
    opens an inference session with the 'stabilityai/StableBeluga2' model, and generates text based on
    the given prompt.

    Returns:
        None
    """
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("**Starting session…**")
        if not arg: arg = "Explain who you are, your functions, capabilities, limitations, and purpose."
        text = None
        text_mod = text_inc = 50
        old = round(time.time() * 1000)
        uri = "wss://chat.petals.dev/api/v2/generate"
        max_length = 512

        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "open_inference_session",
                "model": model,
                "max_length": max_length
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
                        if text: 
                            await send(ctx, text)
                            await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**\nLength: {len(text)}")
                        else: await msg.edit(content=f"**Error! :(**\nEmpty response.\n{PETALS()}")
                        await ws.close()
                else:
                    # print("Error:", data.get("traceback"))
                    if text: await send(ctx, text)
                    else: await msg.edit(content=f"**Error! :(**\n{PETALS()}")
                    await ws.close()

async def send(ctx: commands.Context, text: str):
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await ctx.reply(chunk)
        else:
            await ctx.send(chunk)

async def BELUGA2(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'stabilityai/StableBeluga2')

async def LLAMA2(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'meta-llama/Llama-2-70b-chat-hf') # meta-llama/Llama-2-70b-hf

async def GUANACO(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'timdettmers/guanaco-65b')

async def LLAMA(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'huggyllama/llama-65b')

async def BLOOMZ(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'bigscience/bloomz')

async def CODELLAMA(ctx: commands.Context, arg: str):
    await petalsWebsocket(ctx, arg, 'codellama/CodeLlama-34b-Instruct-hf')

def PETALS() -> str:
    status = requests.get("https://health.petals.dev/api/v1/state").json()
    text = "# [Petals](https://petals.dev/)\nRun large language models at home, BitTorrent‑style.\n\n"
    text += "Commands:\n`-beluga2, -llama2, -guanaco, -llama, -bloomz, -codellama`\n\nModels:```diff\n"
    for i in status["model_reports"]: 
        text += f"{'+ ' if i['state'] == 'healthy' else '- '}{i['name']}: {i['state']}\n"
    text += "```"
    return text