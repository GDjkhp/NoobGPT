import requests
from discord.ext import commands
import asyncio

gde_guild_id = 1092112710667358218
gde_channel_id = 1201314997419130931
gds_guild_id = 398627612299362304
api = f"https://mee6.xyz/api/plugins/levels/leaderboard/{gds_guild_id}?limit=1000"

async def get_server_members(client_discord: commands.Bot, guild_id: int):
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

async def check_and_send_level_up(client_discord: commands.Bot, old_data, new_data, server_members):
    for new_player in new_data["players"]:
        if new_player["id"] in server_members: # filter gde members
            old_player = get_player_data(old_data["players"], new_player['id'])
            if old_player:
                # level
                old_level = old_player["level"]
                new_level = new_player["level"]
                # hundred_moment = new_level % 10 == 0 and new_level > old_level if old_level < 100 else new_level > old_level
                if new_level > old_level:
                    channel = client_discord.get_channel(gde_channel_id)
                    await channel.send(f"GG <@{new_player['id']}>, you just advanced to level {new_level}!") # GG @GDjkhp, you just advanced to level 100!
                # rank
                old_rank_index = cook_rank_index(old_data["players"], new_player["id"])
                new_rank_index = cook_rank_index(new_data["players"], new_player["id"])
                if old_rank_index and new_rank_index and old_rank_index > new_rank_index:
                    channel = client_discord.get_channel(gde_channel_id)
                    await channel.send(f"GG {new_player['username']}, you just advanced to rank #{new_rank_index}!")
                # xp
                # old_xp = old_player["xp"]
                # new_xp = new_player["xp"]
                # if new_xp > old_xp:
                #     channel = client_discord.get_channel(gde_channel_id)
                #     await channel.send(f"GG {new_player['username']}, you just earned {new_xp-old_xp} XP!")

async def main(client_discord: commands.Bot):
    old_data = requests.get(api).json()
    while True:
        await asyncio.sleep(60)
        new_data = requests.get(api).json()
        server_members = await get_server_members(client_discord, gde_guild_id)
        await check_and_send_level_up(client_discord, old_data, new_data, server_members)
        old_data = new_data