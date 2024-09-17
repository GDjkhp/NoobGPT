import yt_dlp
from discord.ext import commands
from discord import app_commands
import discord
import os
import asyncio
import time
from util_discord import command_check, description_helper

async def YTDLP(ctx: commands.Context, arg1: str, arg2: str):
    if await command_check(ctx, "ytdlp", "media"): return
    # async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
    old = round(time.time() * 1000)
    if not arg1: arg1, arg2 = "mp3", "dQw4w9WgXcQ"
    formats = ['mp3', 'm4a']
    if arg2 and not arg1 in formats: return await ctx.channel.send(f"Unsupported format :(\nAvailable conversion formats: `{formats}`")
    elif not arg2: arg2, arg1 = arg1, None
    ydl_opts = get_ydl_opts(arg1)
    msg = await ctx.channel.send("Cooking…")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # fixme: broken if generic
            info_dict = ydl.extract_info(arg2, download=False)
            filename = ydl.prepare_filename(info_dict) if not arg1 else f"{os.path.splitext(ydl.prepare_filename(info_dict))[0]}.{arg1}"
            await msg.edit(content=f"Preparing `{filename}`\nLet me cook.")
            # ydl.download(arg2) # this is faulty
            await asyncio.to_thread(ydl.download, [arg2])  # Use asyncio to run download asynchronously
            if os.path.isfile(filename):
                try: 
                    await ctx.channel.send(file=discord.File(filename))
                    await msg.edit(content=f"`{filename}` has been prepared successfully!\nTook {round(time.time() * 1000)-old}ms")
                except: await msg.edit(content=f"Error: An error occured while cooking `{filename}`\nFile too large!")
                os.remove(filename)
            else: 
                await msg.edit(content=f"Error: An error occured while cooking `{filename}`\nFile too large!")
        except Exception as e: await msg.edit(content=f"**Error! :(**\n{e}")

def checkSize(info, *, incomplete):
    filesize = info.get('filesize') if info.get('filesize') else info.get('filesize_approx')
    if filesize and filesize > 25000000: # 25mb
        return f'File too large! {filesize} bytes'

def get_ydl_opts(arg):
    audio_formats = ["mp3", "m4a"]
    video_formats = ["mp4", "webm"]
    if arg in audio_formats:
        return {
            'format': 'm4a/bestaudio/best',
            'match_filter': checkSize,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': arg,
                'preferredquality': '320',
            }],
            'noplaylist': True,
        }
    
    elif arg in video_formats: # disabled
        return {
            'match_filter': checkSize,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': arg,
            }],
            'noplaylist': True,
        }
    else: 
        return {
            'match_filter': checkSize,
            'noplaylist': True,
        }

class CogYT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ytdlp(self, ctx: commands.Context, arg1:str=None, arg2:str=None):
        await YTDLP(ctx, arg1, arg2)

    @app_commands.command(name="ytdlp", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_basic(self, ctx: commands.Context, link:str=None):
        await YTDLP(ctx, link, None)

    @app_commands.command(name="ytdlp-mp3", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_mp3(self, ctx: commands.Context, link:str=None):
        await YTDLP(ctx, "mp3", link)

    @app_commands.command(name="ytdlp-m4a", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_m4a(self, ctx: commands.Context, link:str=None):
        await YTDLP(ctx, "m4a", link)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogYT(bot))