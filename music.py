import wavelink
from discord.ext import commands
import discord
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]

async def setup_hook_music(bot: commands.Bot):
    await wavelink.Pool.close()
    cursor = mycol.find()
    data = await cursor.to_list(None)
    nodes = []
    for lava in data[0]["nodes"]:
        nodes.append(wavelink.Node(uri=f'{"https://" if lava["https"] else "http://"}{lava["host"]}:{lava["port"]}', 
                                   password=lava["password"], retries=1))
    await wavelink.Pool.connect(client=bot, nodes=nodes)
    
def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def music_now_playing_embed(track: wavelink.Playable):
    embed = discord.Embed(title="🎵 Now playing", color=0x00ff00,
                          description=f"[{track.title}]({track.uri})" if track.uri else track.title)
    embed.add_field(name="Author", value=track.author)
    if track.album.name: embed.add_field(name="Album", value=track.album.name)
    embed.add_field(name="Duration", value=format_mil(track.length))

    if track.artwork: embed.set_thumbnail(url=track.artwork)
    elif track.album.url: embed.set_thumbnail(url=track.album.url)
    elif track.artist.url: embed.set_thumbnail(url=track.artist.url)

    if track.source == "spotify": 
        embed.set_author(name="Spotify", icon_url="https://gdjkhp.github.io/img/Spotify_App_Logo.svg.png")
    elif track.source == "youtube": 
        embed.set_author(name="YouTube", icon_url="https://gdjkhp.github.io/img/771384-512.png")
    else: print(track.source)
    return embed

def format_mil(milliseconds: int):
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    formatted_time = []
    if days:
        formatted_time.append(f"{days:02}")
    if hours or formatted_time:
        formatted_time.append(f"{hours:02}")
    formatted_time.append(f"{minutes:02}:{seconds:02}")

    return ":".join(formatted_time)