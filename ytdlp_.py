import yt_dlp
from discord.ext import commands
import discord
import os
import asyncio
import time
from util_discord import command_check

async def YTDLP(ctx: commands.Context, arg1: str, arg2: str):
    if await command_check(ctx, "ytdlp", "media"): return
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        old = round(time.time() * 1000)
        if not arg1: arg1, arg2 = "mp3", "dQw4w9WgXcQ"
        formats = ['mp3', 'm4a']
        if arg2 and not arg1 in formats: return await ctx.reply(f"Unsupported format :(\nAvailable conversion formats: `{formats}`")
        elif not arg2: arg2, arg1 = arg1, None
        ydl_opts = get_ydl_opts(arg1)
        msg = await ctx.reply("Cooking…")
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
                        await ctx.reply(file=discord.File(filename))
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
