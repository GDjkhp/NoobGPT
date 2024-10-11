import aiohttp
from discord.ext import commands
import time
import discord
from discord import app_commands
from util_discord import command_check, description_helper
import asyncio
from curl_cffi.requests import AsyncSession
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )
session = AsyncSession(impersonate='chrome110')

async def the_real_req(payload: dict):
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    req = await session.post("https://api.cobalt.tools/api/json", json=payload, headers=headers)
    return req.json()

    # async with aiohttp.ClientSession() as session:
    #     async with session.post("https://api.cobalt.tools/api/json", json=payload, headers=headers) as response:
    #         # text = await response.read()
    #         # print(text)
    #         return await response.json()

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

async def get_filename(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                filename_start = content_disposition.find('filename=') + len('filename=')
                filename_end = content_disposition.find(';', filename_start)
                if filename_end == -1:
                    filename_end = None
                filename = content_disposition[filename_start:filename_end].strip('"')
                return filename
            else:
                print("Content-Disposition header not found.")
                return ""

async def COBALT_API(ctx: commands.Context, args: str):
    if await command_check(ctx, "cob", "media"): return await ctx.reply("command disabled", ephemeral=True)
    # async with ctx.typing():
    msg = await ctx.reply("…")
    old = round(time.time() * 1000)

    help_text = [
        '-cob [link]\n\noptional:',
        'vCodec = ["h264", "av1", "vp9"]',
        'vQuality = ["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"]',
        'aFormat = ["best", "mp3", "ogg", "wav", "opus"]',
        'filenamePattern = ["classic", "pretty", "basic", "nerdy"]',
        'isAudioOnly, isTTFullAudio, isAudioMuted, dubLang, disableMetadata, twitterGif, vimeoDash'
    ]

    if not args: return await msg.edit(content="\n".join(help_text))
    args: list[str] = args.split()

    url:str = None
    vCodec:str = None
    vQuality:str = None
    aFormat:str = None
    filenamePattern:str = "nerdy" # default
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

    if not args: return await msg.edit(content="\n".join(help_text))
    url = args[0]
    response = await payload_cooker(url, vCodec, vQuality, aFormat, filenamePattern, 
                                    isAudioOnly, isTTFullAudio, isAudioMuted, dubLang, disableMetadata, twitterGif, vimeoDash)
    filename = ""
    links = []
    bad = ["error", "rate-limit"]
    if response["status"] in bad:
        filename = response["text"]
    else:
        if response["status"] == "picker":
            for link in response["picker"]:
                links.append(link["url"])
        else: 
            filename = await get_filename(response["url"])
            links.append(response["url"])
    
    await msg.edit(content=f"{filename}\nstatus: {response['status']}\n{round(time.time() * 1000)-old}ms", 
                   view=None if response["status"] in bad else DownloadView(links))
        
class DownloadView(discord.ui.View):
    def __init__(self, links: list):
        super().__init__(timeout=None)
        for x in links[:25]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x, label=f"Download", emoji="⬇️"))
        
# async def test():
#     args = ["mp3"]
#     url:str = None
#     vCodec:str = None
#     vQuality:str = None
#     aFormat:str = None
#     filenamePattern:str = "nerdy" # default
#     isAudioOnly:bool = False
#     isTTFullAudio:bool = False
#     isAudioMuted:bool = False
#     dubLang:bool = False
#     disableMetadata:bool = False
#     twitterGif:bool = False
#     vimeoDash:bool = False

#     for x in list(args):
#         if x in ["h264", "av1", "vp9"]:
#             vCodec = x
#             args.remove(x)
#         if x in ["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"]:
#             vQuality = x
#             args.remove(x)
#         if x in ["best", "mp3", "ogg", "wav", "opus"]:
#             aFormat = x
#             isAudioOnly = True
#             args.remove(x)
#         if x in ["classic", "pretty", "basic", "nerdy"]:
#             filenamePattern = x
#             args.remove(x)
#         if x == "isAudioOnly":
#             isAudioOnly = True
#             args.remove(x)
#         if x == "isTTFullAudio":
#             isTTFullAudio = True
#             args.remove(x)
#         if x == "isAudioMuted":
#             isAudioMuted = True
#             args.remove(x)
#         if x == "dubLang":
#             dubLang = True
#             args.remove(x)
#         if x == "disableMetadata":
#             disableMetadata = True
#             args.remove(x)
#         if x == "twitterGif":
#             twitterGif = True
#             args.remove(x)
#         if x == "vimeoDash":
#             vimeoDash = True
#             args.remove(x)
#     resp = await payload_cooker("https://www.youtube.com/watch?v=dQw4w9WgXcQ", vCodec, vQuality, aFormat, filenamePattern, 
#                                 isAudioOnly, isTTFullAudio, isAudioMuted, dubLang, disableMetadata, twitterGif, vimeoDash)
#     print(resp)

# asyncio.run(test())
            
class CogCob(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["cobalt"]}')
    @app_commands.describe(arg="cobalt arguments")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def cobalt(self, ctx: commands.Context, *, arg:str=None):
        await COBALT_API(ctx, arg)

    @commands.command() # alias
    async def cob(self, ctx: commands.Context, *, arg:str=None):
        await COBALT_API(ctx, arg)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogCob(bot))