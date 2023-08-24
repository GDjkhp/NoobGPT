import yt_dlp
from discord.ext import commands
import discord
import os

async def YTDLP(ctx: commands.Context, arg1: str, arg2: str):
    formats = ['mp3', 'm4a']
    if arg2 and not arg1 in formats: return await ctx.reply(f"Unsupported format :(\nAvailable conversion formats: `{formats}`")
    elif not arg2: arg2, arg1 = arg1, None
    ydl_opts = get_ydl_opts(arg1)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(arg2, download=False)
        filename = ydl.prepare_filename(info_dict) if not arg1 else f"{os.path.splitext(ydl.prepare_filename(info_dict))[0]}.{arg1}"
        msg = await ctx.reply(f"Preparing `{filename}`\nLet me cook.")
        try:
            ydl.download(arg2) # this is faulty
            if os.path.isfile(filename):
                try: 
                    await ctx.reply(content=None, file=discord.File(filename))
                    await msg.edit(content=f"`{filename}` has been prepared successfully!")
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
            }]
        }
    
    elif arg in video_formats: # disabled
        return {
            'match_filter': checkSize,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': arg,
            }]
        }
    else: 
        return {
            'match_filter': checkSize,
        }
