import wavelink
from discord.ext import commands
import discord
from util_discord import command_check, get_database2, set_dj_role_db, check_if_master_or_admin
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

async def set_dj_role(ctx: commands.Context):
    if not ctx.guild: return await ctx.reply("not supported")
    if await command_check(ctx, "music", "media"): return
    if not await check_if_master_or_admin(ctx): return await ctx.reply("not a bot master or an admin")
    permissions = ctx.channel.permissions_for(ctx.me)
    if not permissions.manage_roles:
        return await ctx.reply("**manage roles permission is disabled :(**")
    
    db = await get_database2(ctx.guild.id)
    if not db.get("bot_dj_role") or not db["bot_dj_role"]:
        role = await ctx.guild.create_role(name="noobgpt disc jockey", mentionable=False)
        await set_dj_role_db(ctx.guild.id, role.id)
        await ctx.reply(f"dj role <@&{role.id}> has been created")
    else:
        role = ctx.guild.get_role(db["bot_dj_role"])
        await role.delete()
        await set_dj_role_db(ctx.guild.id, 0)
        await ctx.reply("dj role has been removed")

async def check_if_dj(ctx: commands.Context):
    db = await get_database2(ctx.guild.id)
    if db.get("bot_dj_role"):
        if db["bot_dj_role"]:
            return ctx.guild.get_role(db["bot_dj_role"]) in ctx.author.roles
    return True

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
    elif track.source == "soundcloud":
        embed.set_author(name="SoundCloud", icon_url="https://gdjkhp.github.io/img/soundcloud-icon.png")
    elif track.source == "bandcamp":
        embed.set_author(name="Bandcamp", icon_url="https://gdjkhp.github.io/img/bandcamp-button-circle-aqua-512.png")
    elif track.source == "applemusic":
        embed.set_author(name="Apple Music", icon_url="https://gdjkhp.github.io/img/applemoosic.png")
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