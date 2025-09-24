import aiohttp
import urllib.parse
import discord
from discord.ext import commands

def parse_response(text):
    parts = text.strip().split('~|~')
    result = {}
    for i in range(0, len(parts) - 1, 2):
        key = parts[i].strip()
        value = parts[i+1].strip()
        result[key] = value
    return result

async def gj_song_info(song_id: str):
    if song_id and song_id.startswith("http"):
        parsed = urllib.parse.urlparse(song_id)
        if "newgrounds.com" in parsed.netloc and "/audio/listen/" in parsed.path:
            try:
                song_id = parsed.path.split("/audio/listen/")[1].split("/")[0]
            except Exception:
                pass

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://www.boomlings.com/database/getGJSongInfo.php",
            data={"secret": "Wmfd2893gb7", "songID": song_id,},
            headers={"User-Agent": "",}
        ) as resp:
            text = await resp.text()
            song_info = parse_response(text)
            return {
                "ID": int(song_info.get("1", 0)),
                "name": song_info.get("2", ""),
                "artistID": int(song_info.get("3", 0)),
                "artistName": song_info.get("4", ""),
                "size": float(song_info.get("5", 0)),
                "videoID": song_info.get("6", ""),
                "youtubeURL": song_info.get("7", ""),
                "isVerified": song_info.get("8", "0") == "1",
                "songPriority": int(song_info.get("9", 0)) if "9" in song_info else None,
                "link": urllib.parse.unquote(song_info.get("10", "")),
                "nongEnum": int(song_info.get("11", 0)) if "11" in song_info else None,
                "extraArtistIDs": [int(x) for x in song_info.get("12", "").split(".") if x] if "12" in song_info else [],
                "new": song_info.get("13", "0") == "1" if "13" in song_info else False,
                "newType": int(song_info.get("14", 0)) if "14" in song_info else None,
                "extraArtistNames": song_info.get("15", "").split(",") if "15" in song_info and song_info["15"] else [],
            }

async def process_song_id(ctx: commands.Context, song_id: str):
    if not song_id:
        return await ctx.send("Please provide a song ID or Newgrounds URL.")

    info = await gj_song_info(song_id)
    if not info or not info.get("ID"):
        return await ctx.send("Could not find song info.")

    embed = discord.Embed(
        title=f"Song Info: {info['name'] or 'Unknown'}",
        color=discord.Color.blue()
    )
    embed.add_field(name="ID", value=info["ID"], inline=True)
    embed.add_field(name="Name", value=info["name"] or "Unknown", inline=True)
    embed.add_field(name="Artist ID", value=info["artistID"], inline=True)
    embed.add_field(name="Artist Name", value=info["artistName"] or "Unknown", inline=True)
    embed.add_field(name="Size (MB)", value=f"{info['size']:.2f}", inline=True)
    embed.add_field(name="YouTube Video ID", value=info["videoID"] or "N/A", inline=True)
    embed.add_field(name="YouTube URL", value=f"[YouTube]({info['youtubeURL']})" if info["youtubeURL"] else "N/A", inline=False)
    embed.add_field(name="Artist Verified (Scouted)", value="Yes" if info["isVerified"] else "No", inline=True)
    embed.add_field(name="Song Priority", value=info["songPriority"] if info["songPriority"] is not None else "N/A", inline=True)
    embed.add_field(name="MP3 Link", value=f"[Download]({info['link']})" if info["link"] else "N/A", inline=False)
    nong_map = {0: "None", 1: "NCS"}
    nong_val = info["nongEnum"] if info["nongEnum"] is not None else None
    embed.add_field(name="NONG Type", value=nong_map.get(nong_val, str(nong_val) if nong_val is not None else "N/A"), inline=True)
    if info["extraArtistIDs"]:
        embed.add_field(name="Extra Artist IDs", value=", ".join(str(x) for x in info["extraArtistIDs"]), inline=True)
    embed.add_field(name="New Icon", value="Yes" if info.get("new") else "No", inline=True)
    if info.get("new"):
        new_type_map = {0: "Yellow", 1: "Blue"}
        embed.add_field(name="New Icon Type", value=new_type_map.get(info.get("newType"), str(info.get("newType"))), inline=True)
    if info["extraArtistNames"]:
        names = info["extraArtistNames"]
        if len(names) % 2 == 0:
            pairs = [f"{names[i]}: {names[i+1]}" for i in range(0, len(names), 2)]
            embed.add_field(name="Extra Artists", value="; ".join(pairs), inline=False)
        else:
            embed.add_field(name="Extra Artists", value=", ".join(names), inline=False)
    await ctx.send(embed=embed)

class CogGeometryJump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def songcheck(self, ctx: commands.Context, *, song_id:str=None):
        await process_song_id(ctx, song_id)