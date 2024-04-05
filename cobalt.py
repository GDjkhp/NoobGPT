import aiohttp
from discord.ext import commands
import time
import asyncio
import discord

async def the_real_req(payload: dict):
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://co.wuk.sh/api/json", json=payload, headers=headers) as response:
            return await response.json()

async def payload_cooker(
        url:str,
        vCodec:str,
        vQuality:str,
        aFormat:str,
        filenamePattern:str,
        isAudioOnly:bool,
        isTTFullAudio:bool,
        isAudioMuted:bool,
        dubLang:bool,
        disableMetadata:bool,
        twitterGif:bool,
        vimeoDash:bool):

    payload = {
        "url" : url
    }

    if vCodec:
        payload["vCodec"] = vCodec
    if vQuality:
        payload["vQuality"] = vQuality
    if aFormat:
        payload["aFormat"] = aFormat
    if filenamePattern:
        payload["filenamePattern"] = filenamePattern
    if isAudioOnly:
        payload["isAudioOnly"] = isAudioOnly
    if isTTFullAudio:
        payload["isTTFullAudio"] = isTTFullAudio
    if isAudioMuted:
        payload["isAudioMuted"] = isAudioMuted
    if dubLang:
        payload["dubLang"] = dubLang
    if disableMetadata:
        payload["disableMetadata"] = disableMetadata
    if twitterGif:
        payload["twitterGif"] = twitterGif
    if vimeoDash:
        payload["vimeoDash"] = vimeoDash

    # print(payload)
    return await the_real_req(payload)

async def COBALT_API(ctx: commands.Context, args: list[str]):
    async with ctx.typing():
        msg = await ctx.reply("…")
        old = round(time.time() * 1000)

        url:str = None
        vCodec:str = None
        vQuality:str = None
        aFormat:str = None
        filenamePattern:str = None
        isAudioOnly:bool = False
        isTTFullAudio:bool = False
        isAudioMuted:bool = False
        dubLang:bool = False
        disableMetadata:bool = False
        twitterGif:bool = False
        vimeoDash:bool = False

        for x in list(args):
            if x in ["h264", "av1", "vp9"]:
                vCodec = x
                args.remove(x)
            if x in ["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"]:
                vQuality = x
                args.remove(x)
            if x in ["best", "mp3", "ogg", "wav", "opus"]:
                aFormat = x
                isAudioOnly = True
                args.remove(x)
            if x in ["classic", "pretty", "basic", "nerdy"]:
                filenamePattern = x
                args.remove(x)
            if x == "isAudioOnly":
                isAudioOnly = True
                args.remove(x)
            if x == "isTTFullAudio":
                isTTFullAudio = True
                args.remove(x)
            if x == "isAudioMuted":
                isAudioMuted = True
                args.remove(x)
            if x == "dubLang":
                dubLang = True
                args.remove(x)
            if x == "disableMetadata":
                disableMetadata = True
                args.remove(x)
            if x == "twitterGif":
                twitterGif = True
                args.remove(x)
            if x == "vimeoDash":
                vimeoDash = True
                args.remove(x)

        help_text = '-cob [url]'
        help_text+= '\n["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"]'
        help_text+= '\n["best", "mp3", "ogg", "wav", "opus"]'
        help_text+= '\n[more here](https://github.com/wukko/cobalt/blob/current/docs/api.md#request-body-variables)'

        if not args: return await msg.edit(content=help_text)
        url = args[0]
        response = await payload_cooker(url, vCodec, vQuality, aFormat, filenamePattern, 
                                        isAudioOnly, isTTFullAudio, isAudioMuted, dubLang, disableMetadata, twitterGif, vimeoDash)
        bad = ["error", "rate-limit", "redirect", "picker"]
        return await msg.edit(content=f"status: {response['status']}\n{round(time.time() * 1000)-old}ms", 
                              view=None if response["status"] in bad else DownloadView(response["url"]))
        
class DownloadView(discord.ui.View):
    def __init__(self, link: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=link, label="Download", emoji="⬇️"))
        
# async def test():
#     resp = await payload_cooker("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "mp3")
#     print(resp)

# asyncio.run(test())