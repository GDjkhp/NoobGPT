import requests
from discord.ext import commands
import asyncio

async def get_server_members(client_discord: commands.Bot, guild_id):
    guild = client_discord.get_guild(guild_id)
    members = []
    if guild:
        members = [member.id for member in guild.members]
    return members

async def check_and_send_level_up(client_discord: commands.Bot, old_data, new_data, server_members):
    for old_player, new_player in zip(old_data["players"], new_data["players"]):
        # if new_player['id'] in server_members: # filter gde members
            old_level = old_player["level"]
            new_level = new_player["level"]

            if new_level > old_level: # new_level % 10 == 0 and 
                channel_id = 1201128975712387072 # change this to target channel soon
                channel = client_discord.get_channel(channel_id)
                await channel.send(f"Level up! {new_player['username']} reached level {new_level}!")

async def main():
    # guild_id = your_discord_guild_id
    # server_members = await get_server_members(guild_id)

    while True:
        # Record data
        data = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/398627612299362304?limit=1000").json()

        # Wait for 1 minute
        await asyncio.sleep(60)

        # Fetch new data
        new_data = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/398627612299362304?limit=1000").json()

        # Compare old to new data and send messages for level ups
        await check_and_send_level_up(data, new_data, None) # server_members