import discord
from discord.ext import commands
import random
import asyncio
from datetime import timedelta
from util_discord import command_check

# Constants
ROPE_LENGTH = 20  # Total length of the rope (team positions will be relative to this)
PULL_COOLDOWN = 0.5  # Reduced cooldown for faster gameplay
GAME_DURATION = 60  # Default game duration in seconds
PULL_STRENGTH_RANGE = (0.5, 1.5)  # Random pull strength for each pull

async def TUG_OF_WAR(ctx: commands.Context | discord.Interaction, duration: int = GAME_DURATION):
    """Main function to start and manage a tug-of-war game"""
    if await command_check(ctx, "tug", "games"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    
    # Initialize game state
    game_state = {
        "team_a": {},  # Players in team A: {user_id: {name, last_pull_time, total_pulls}}
        "team_b": {},  # Players in team B: {user_id: {name, last_pull_time, total_pulls}}
        "rope_position": ROPE_LENGTH // 2,  # Start in the middle
        "running": True,
        "start_time": discord.utils.utcnow(),
        "end_time": discord.utils.utcnow() + timedelta(seconds=duration),
        "duration": duration,
        "winner": None,
        "team_a_pulls": 0,
        "team_b_pulls": 0
    }
    
    # Send initial game message
    embed = build_game_embed(game_state)
    view = TugOfWarView(game_state)
    
    if isinstance(ctx, commands.Context):
        message = await ctx.reply(embed=embed, view=view)
    else:
        await ctx.response.send_message(embed=embed, view=view)
        message = await ctx.original_response()
    
    # Start game update loop
    try:
        while game_state["running"]:
            # Check if game should end
            if discord.utils.utcnow() >= game_state["end_time"]:
                game_state["running"] = False
                if game_state["rope_position"] < ROPE_LENGTH // 2:
                    game_state["winner"] = "Team A"
                elif game_state["rope_position"] > ROPE_LENGTH // 2:
                    game_state["winner"] = "Team B"
                else:
                    game_state["winner"] = "Tie"
            
            # Update the game display
            embed = build_game_embed(game_state)
            await message.edit(embed=embed, view=view if game_state["running"] else None)
            
            # Check for win condition
            if game_state["rope_position"] <= 0:
                game_state["running"] = False
                game_state["winner"] = "Team A"
            elif game_state["rope_position"] >= ROPE_LENGTH:
                game_state["running"] = False
                game_state["winner"] = "Team B"
            
            await asyncio.sleep(1)
        
        # Show final results
        embed = build_results_embed(game_state)
        await message.edit(embed=embed, view=None)
    
    except Exception as e:
        print(f"Error in tug of war game: {e}")
        game_state["running"] = False
        embed = discord.Embed(
            title="Tug of War - Error",
            description=f"Game stopped due to an error: {e}",
            color=0xff0000
        )
        await message.edit(embed=embed, view=None)

def build_game_embed(game_state):
    """Create the game display embed"""
    # Time remaining calculation
    if game_state["running"]:
        time_remaining = (game_state["end_time"] - discord.utils.utcnow()).total_seconds()
        time_str = f"{int(time_remaining // 60):02d}:{int(time_remaining % 60):02d}"
    else:
        time_str = "Game Over!"
    
    # Team counts and pulls
    team_a_count = len(game_state["team_a"])
    team_b_count = len(game_state["team_b"])
    team_a_pulls = game_state.get("team_a_pulls", 0)
    team_b_pulls = game_state.get("team_b_pulls", 0)
    
    # Create the rope visual
    rope = build_rope_visual(game_state["rope_position"])
    
    # Create embed
    embed = discord.Embed(
        title="🔴 Tug of War! 🔵",
        description=f"**SPAM your team's button to pull the rope and win!**\n\n{rope}\n\nTime: {time_str}",
        color=0x00ff00
    )
    
    # Add team fields with pull counts
    embed.add_field(
        name=f"Team A ({team_a_count} players, {team_a_pulls} pulls)", 
        value=format_team_players(game_state["team_a"]) or "No players"
    )
    embed.add_field(
        name=f"Team B ({team_b_count} players, {team_b_pulls} pulls)", 
        value=format_team_players(game_state["team_b"]) or "No players"
    )
    
    return embed

def format_team_players(team_dict):
    """Format player names with their pull counts"""
    player_strings = []
    for player_id, player_data in team_dict.items():
        pull_count = player_data.get("total_pulls", 0)
        player_strings.append(f"{player_data['name']} ({pull_count} pulls)")
    
    return "\n".join(player_strings[:10])  # Limit to first 10 players to avoid embed limits

def build_results_embed(game_state):
    """Create the final results embed"""
    # Team counts and pulls
    team_a_count = len(game_state["team_a"])
    team_b_count = len(game_state["team_b"])
    team_a_pulls = game_state.get("team_a_pulls", 0)
    team_b_pulls = game_state.get("team_b_pulls", 0)
    
    # Find MVP (most pulls) from each team
    team_a_mvp = get_team_mvp(game_state["team_a"])
    team_b_mvp = get_team_mvp(game_state["team_b"])
    
    # Create the rope visual
    rope = build_rope_visual(game_state["rope_position"])
    
    # Choose embed color based on winner
    color = 0xffcc00  # Default gold
    if game_state["winner"] == "Team A":
        color = 0xff0000  # Red
    elif game_state["winner"] == "Team B":
        color = 0x0000ff  # Blue
    
    # Create embed with winner announcement
    embed = discord.Embed(
        title="Tug of War - Game Over!",
        description=f"**{game_state['winner']}** has won the tug of war!\n\n{rope}",
        color=color
    )
    
    # Add team fields with pull counts and MVPs
    team_a_field = format_team_players(game_state["team_a"]) or "No players"
    if team_a_mvp:
        team_a_field += f"\n\n**MVP:** {team_a_mvp['name']} ({team_a_mvp['total_pulls']} pulls)"
    
    team_b_field = format_team_players(game_state["team_b"]) or "No players"
    if team_b_mvp:
        team_b_field += f"\n\n**MVP:** {team_b_mvp['name']} ({team_b_mvp['total_pulls']} pulls)"
    
    embed.add_field(
        name=f"Team A ({team_a_count} players, {team_a_pulls} pulls)", 
        value=team_a_field
    )
    embed.add_field(
        name=f"Team B ({team_b_count} players, {team_b_pulls} pulls)", 
        value=team_b_field
    )
    
    return embed

def get_team_mvp(team_dict):
    """Find the player with the most pulls in a team"""
    if not team_dict:
        return None
    
    mvp_id = max(team_dict, key=lambda player_id: team_dict[player_id].get("total_pulls", 0))
    return team_dict[mvp_id]

def build_rope_visual(position):
    """Create a visual representation of the rope position"""
    rope_length = ROPE_LENGTH
    marker_position = int(position)  # Convert float position to int for string multiplication
    
    # Create a more visually distinct rope
    left_side = "=" * marker_position
    right_side = "=" * (rope_length - marker_position)
    
    rope = f"🔴 Team A {left_side}🧩{right_side} Team B 🔵"
    
    # Add strength indicator based on position
    team_a_percent = ((ROPE_LENGTH / 2) - min(position, ROPE_LENGTH / 2)) / (ROPE_LENGTH / 2) * 100
    team_b_percent = (max(position, ROPE_LENGTH / 2) - (ROPE_LENGTH / 2)) / (ROPE_LENGTH / 2) * 100
    
    strength_indicator = ""
    if team_a_percent > 0:
        strength_indicator = f"Team A leading by {team_a_percent:.0f}%"
    elif team_b_percent > 0:
        strength_indicator = f"Team B leading by {team_b_percent:.0f}%"
    else:
        strength_indicator = "Teams are evenly matched!"
    
    return f"{rope}\n{strength_indicator}"

class TugOfWarView(discord.ui.View):
    def __init__(self, game_state):
        super().__init__(timeout=None)
        self.game_state = game_state
        
        # Add only two buttons - one for each team
        self.add_item(TeamPullButton("Team A", "team_a", "🔴", discord.ButtonStyle.primary, 0))
        self.add_item(TeamPullButton("Team B", "team_b", "🔵", discord.ButtonStyle.danger, 0))

class TeamPullButton(discord.ui.Button):
    def __init__(self, label, team_id, emoji, style, row):
        super().__init__(style=style, label=label, emoji=emoji, row=row)
        self.team_id = team_id
    
    async def callback(self, interaction: discord.Interaction):
        game_state = self.view.game_state
        
        # Check if game is still running
        if not game_state["running"]:
            return await interaction.response.send_message("The game has ended!", ephemeral=True)
        
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        current_time = discord.utils.utcnow().timestamp()
        
        # Check if user is already on the OTHER team
        other_team = "team_b" if self.team_id == "team_a" else "team_a"
        if user_id in game_state[other_team]:
            # Prevent team switching
            return await interaction.response.send_message(
                f"You've already joined {other_team.replace('_', ' ').title()}! No switching teams.", 
                ephemeral=True
            )
        
        # If user is not on this team yet, add them
        if user_id not in game_state[self.team_id]:
            # Add to selected team
            game_state[self.team_id][user_id] = {
                "name": user_name,
                "last_pull_time": 0,  # Initialize with no cooldown
                "total_pulls": 0
            }
            await interaction.response.defer()
            return
        
        # User is on this team, check cooldown for pulling
        last_pull = game_state[self.team_id][user_id].get("last_pull_time", 0)
        if current_time - last_pull < PULL_COOLDOWN:
            remaining = PULL_COOLDOWN - (current_time - last_pull)
            return await interaction.response.send_message(f"Wait {remaining:.1f}s!", ephemeral=True)
        
        # Update last pull time
        game_state[self.team_id][user_id]["last_pull_time"] = current_time
        
        # Update pull counts
        game_state[self.team_id][user_id]["total_pulls"] = game_state[self.team_id][user_id].get("total_pulls", 0) + 1
        if self.team_id == "team_a":
            game_state["team_a_pulls"] = game_state.get("team_a_pulls", 0) + 1
        else:
            game_state["team_b_pulls"] = game_state.get("team_b_pulls", 0) + 1
        
        # Calculate pull strength with randomness
        pull_strength = random.uniform(PULL_STRENGTH_RANGE[0], PULL_STRENGTH_RANGE[1])
        
        # Apply pull to rope position
        if self.team_id == "team_a":
            game_state["rope_position"] -= pull_strength
        else:
            game_state["rope_position"] += pull_strength
        
        await interaction.response.defer()

class CogTugOfWar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tug(self, ctx: commands.Context, duration: int = GAME_DURATION):
        """Start a tug of war game"""
        await TUG_OF_WAR(ctx, duration)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogTugOfWar(bot))