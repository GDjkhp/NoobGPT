import aiohttp
from discord.ext import commands
import asyncio
import discord

# gde bot
delay = 60
gde_guild_id = 1092112710667358218
gde_channel_id = 1201314997419130931
gds_guild_id = 398627612299362304
api = f"https://mee6.xyz/api/plugins/levels/leaderboard/{gds_guild_id}?limit=1000"

def get_server_members(client_discord: commands.Bot, guild_id: int):
    guild = client_discord.get_guild(guild_id)
    members = []
    if guild:
        members = [str(member.id) for member in guild.members]
    return members

def cook_rank_index(data: list, id: str) -> int:
    index = 0
    for i in data:
        if i["id"] == id: return index + 1
        index+=1
    return None

def get_player_data(data: list, id: str):
    for player in data:
        if player["id"] == id: return player
    return None

def check_level_up(old_data, new_data, server_members) -> list:
    level_up_messages = []
    for new_player in new_data["players"]:
        if new_player["id"] in server_members: # filter gde members
            old_player = get_player_data(old_data["players"], new_player["id"])
            if old_player:
                # level
                old_level = old_player["level"]
                new_level = new_player["level"]
                # hundred_moment = new_level % 10 == 0 and new_level > old_level if old_level < 100 else new_level > old_level
                if new_level > old_level:
                    level_up_messages.append(f"GG <@{new_player['id']}>, you just advanced to level {new_level}!")
                # rank
                old_rank_index = cook_rank_index(old_data["players"], new_player["id"])
                new_rank_index = cook_rank_index(new_data["players"], new_player["id"])
                rank_logic = old_rank_index and new_rank_index and old_rank_index > new_rank_index and new_rank_index <= 100
                if rank_logic:
                    level_up_messages.append(f"GG {new_player['username']}, you just advanced to rank #{new_rank_index}!")
                # xp
                # old_xp = old_player["xp"]
                # new_xp = new_player["xp"]
                # if new_xp > old_xp:
                #     level_up_messages.append(f"GG {new_player['username']}, you just earned {new_xp-old_xp} XP!")
    return level_up_messages

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: print(e)

async def main_gde(client_discord: commands.Bot):
    print("gde bot started")
    old_data = await req_real(api)
    if old_data: print("mee6 api ok")
    while True:
        try:
            await asyncio.sleep(delay)
            new_data = await req_real(api)
            if new_data:
                server_members = get_server_members(client_discord, gde_guild_id)
                msgs = check_level_up(old_data, new_data, server_members)
                if msgs:
                    channel = client_discord.get_channel(gde_channel_id)
                    await channel.send("\n".join(msgs))
                old_data = new_data
        except Exception as e:
            print(f"Exception in main_gde: {e}")
            await asyncio.sleep(delay)
            old_data = await req_real(api) # fuckup

# styx bot
api2 = f"{api}&page=1" # rank 1001+
robert_id = 290162530720940034
styx_id = 539408209769922560
styx_server_id = 1213758959609978950 # no longer used
styx_channel_id = 1181993133647601716 # gde?
chan_ids = [1213946372093517885] # no longer used
role_id = 1214840725049446421 # no longer used

def check_robert(old_data, new_data) -> list:
    level_up_messages = []
    for new_player in new_data["players"]:
        old_player = get_player_data(old_data["players"], new_player["id"])
        if old_player and new_player["id"] == str(robert_id):
            # xp
            old_xp = old_player["xp"]
            new_xp = new_player["xp"]
            if new_xp > old_xp:
                level_up_messages.append(f"<@{styx_id}>, {new_player['username']} is currently in chat!")
    return level_up_messages

async def main_rob(client_discord: commands.Bot):
    await asyncio.sleep(30) # just to be safe
    print("robtop bot started")
    old_data = await req_real(api2)
    if old_data: print("mee6 api2 ok")
    while True:
        try:
            await asyncio.sleep(delay)
            new_data = await req_real(api2)
            if new_data:
                msgs = check_robert(old_data, new_data)
                if msgs:
                    channel = client_discord.get_channel(styx_channel_id)
                    await channel.send("\n".join(msgs))
                    print("robtop in chat")
                    await asyncio.sleep(3600) # 1 hour
                    new_data = await req_real(api2)
                old_data = new_data
        except Exception as e:
            print(f"Exception in main_rob: {e}")
            await asyncio.sleep(delay)
            old_data = await req_real(api2) # fuckup

def build_attachments(message: discord.Message) -> str:
    if message.attachments:
        build_str = ""
        for file in message.attachments:
            build_str += f"{file.url}\n" # don't even try (can be an image, video, or any file)
        return build_str
    return ""

# no longer used
async def main_styx(bot: commands.Bot, message: discord.Message):
    if message.author.id == bot.user.id: return # prevent spam on same channel
    if message.channel.id in chan_ids:
        chan = bot.get_channel(styx_channel_id)
        # link = f"https://discord.com/channels/{styx_server_id}/{message.channel.id}/{message.id}"
        await chan.send(content=f"<@&{role_id}>\n{message.content}\n{build_attachments(message)}", 
                        embeds=message.embeds) # \n{link}