import discord
from discord.ext import commands
import random
import asyncio
from datetime import timedelta
from util_discord import command_check

# Constants
MAX_ROUNDS = 6  # Total number of chambers/rounds
MIN_BULLETS = 1  # Minimum number of "live" rounds
MAX_BULLETS = 3  # Maximum number of "live" rounds
GAME_DURATION = 300  # Default game duration in seconds (increased for two-player games)
PLAYERS_REQUIRED = 2  # Exactly two players required

async def RUSSIAN_ROULETTE(ctx: commands.Context | discord.Interaction, duration: int = GAME_DURATION):
    """Main function to start and manage a Russian Roulette game"""
    if await command_check(ctx, "roulette", "games"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    
    # Initialize game state
    bullet_count = random.randint(MIN_BULLETS, MAX_BULLETS)
    chambers = [False] * MAX_ROUNDS  # False = safe, True = bullet
    
    # Randomly place bullets in chambers
    bullet_positions = random.sample(range(MAX_ROUNDS), bullet_count)
    for position in bullet_positions:
        chambers[position] = True
    
    game_state = {
        "players": {},  # Player data: {user_id: {name, alive, turns_played}}
        "player_ids": [],  # To maintain turn order
        "chambers": chambers,
        "current_chamber": 0,
        "waiting_for_players": True,  # New state for waiting phase
        "running": True,
        "start_time": None,  # Will be set when game actually starts
        "end_time": None,  # Will be set when game actually starts
        "duration": duration,
        "current_player_index": 0,  # Track whose turn it is
        "eliminated_players": [],
        "winners": [],
        "bullet_count": bullet_count,
        "game_log": ["Game created! Waiting for 2 players to join..."]
    }
    
    # Send initial game message
    embed = build_waiting_embed(game_state)
    view = RussianRouletteView(game_state)
    
    if isinstance(ctx, commands.Context):
        message = await ctx.reply(embed=embed, view=view)
    else:
        await ctx.response.send_message(embed=embed, view=view)
        message = await ctx.original_response()
    
    # Start game update loop
    try:
        while game_state["running"]:
            # If still waiting for players
            if game_state["waiting_for_players"]:
                if len(game_state["players"]) >= PLAYERS_REQUIRED:
                    # Transition from waiting to playing
                    game_state["waiting_for_players"] = False
                    game_state["start_time"] = discord.utils.utcnow()
                    game_state["end_time"] = discord.utils.utcnow() + timedelta(seconds=duration)
                    game_state["game_log"].append("🎮 Both players have joined! Game is starting...")
                    
                    # Fix the player order based on join time
                    game_state["player_ids"] = list(game_state["players"].keys())
                    
                    # Update the join button to a pull trigger button
                    view = RussianRouletteView(game_state)
                    embed = build_game_embed(game_state)
                    await message.edit(embed=embed, view=view)
            else:
                # Regular game running checks
                
                # Check if game should end by timeout
                if discord.utils.utcnow() >= game_state["end_time"]:
                    game_state["running"] = False
                    game_state["game_log"].append("⏰ Time's up! Game over.")
                    
                    # Any surviving players are winners
                    alive_players = [player_id for player_id, data in game_state["players"].items() if data["alive"]]
                    if alive_players:
                        game_state["winners"] = [game_state["players"][player_id]["name"] for player_id in alive_players]
                        game_state["game_log"].append(f"Survivor: {', '.join(game_state['winners'])}")
                    else:
                        game_state["game_log"].append("Everyone was eliminated!")
                
                # Check if all bullets have been fired
                fired_chambers = game_state["current_chamber"]
                bullets_left = sum(game_state["chambers"][fired_chambers:])
                
                if fired_chambers >= MAX_ROUNDS or (bullets_left == 0 and fired_chambers > 0):
                    game_state["running"] = False
                    game_state["game_log"].append("🎮 All rounds complete!")
                    
                    # Add survivors to winners
                    alive_players = [player_id for player_id, data in game_state["players"].items() if data["alive"]]
                    if alive_players:
                        game_state["winners"] = [game_state["players"][player_id]["name"] for player_id in alive_players]
                        game_state["game_log"].append(f"Survivor: {', '.join(game_state['winners'])}")
                    else:
                        game_state["game_log"].append("Everyone was eliminated!")
                
                # Check if only one player is left alive
                alive_players = [player_id for player_id, data in game_state["players"].items() if data["alive"]]
                if len(alive_players) == 1 and len(game_state["players"]) >= PLAYERS_REQUIRED:
                    winner_name = game_state["players"][alive_players[0]]["name"]
                    game_state["winners"] = [winner_name]
                    game_state["running"] = False
                    game_state["game_log"].append(f"🏆 {winner_name} is the last player standing!")
                
                # Update the game display
                embed = build_game_embed(game_state)
                await message.edit(embed=embed, view=view if game_state["running"] else None)
            
            await asyncio.sleep(1)
        
        # Show final results
        embed = build_results_embed(game_state)
        await message.edit(embed=embed, view=None)
    
    except Exception as e:
        print(f"Error in Russian Roulette game: {e}")
        game_state["running"] = False
        embed = discord.Embed(
            title="Russian Roulette - Error",
            description=f"Game stopped due to an error: {e}",
            color=0xff0000
        )
        await message.edit(embed=embed, view=None)

def build_waiting_embed(game_state):
    """Create the waiting for players embed"""
    player_count = len(game_state["players"])
    players_needed = PLAYERS_REQUIRED - player_count
    
    # Create embed
    embed = discord.Embed(
        title="🔫 Russian Roulette - Waiting for Players 🎲",
        description=f"**Waiting for {players_needed} more player{'s' if players_needed != 1 else ''} to join!**\nPress the Join button to enter the game.",
        color=0xff5500
    )
    
    # Add player list
    if player_count > 0:
        player_names = [data["name"] for data in game_state["players"].values()]
        embed.add_field(
            name=f"Players ({player_count}/{PLAYERS_REQUIRED})", 
            value="\n".join(player_names),
            inline=False
        )
    
    return embed

def build_game_embed(game_state):
    """Create the game display embed"""
    # Time remaining calculation
    if game_state["running"] and not game_state["waiting_for_players"]:
        time_remaining = (game_state["end_time"] - discord.utils.utcnow()).total_seconds()
        time_str = f"{int(time_remaining // 60):02d}:{int(time_remaining % 60):02d}"
    else:
        time_str = "Game Over!" if not game_state["waiting_for_players"] else "Waiting for players..."
    
    # Player count
    player_count = len(game_state["players"])
    alive_count = sum(1 for player in game_state["players"].values() if player["alive"])
    eliminated_count = len(game_state["eliminated_players"])
    
    # Create the revolver visual
    revolver = build_revolver_visual(game_state)
    
    # Determine whose turn it is
    current_turn_text = ""
    if game_state["running"] and not game_state["waiting_for_players"] and len(game_state["player_ids"]) > 0:
        current_player_index = game_state["current_player_index"] % len(game_state["player_ids"])
        current_player_id = game_state["player_ids"][current_player_index]
        if current_player_id in game_state["players"] and game_state["players"][current_player_id]["alive"]:
            current_player_name = game_state["players"][current_player_id]["name"]
            current_turn_text = f"\n**🎯 Current Turn: {current_player_name}**"
    
    # Create embed
    embed = discord.Embed(
        title="🔫 Russian Roulette 🎲",
        description=f"**Take turns pulling the trigger!**\n{revolver}\nTime: {time_str}{current_turn_text}",
        color=0xff5500
    )
    
    # Add player stats
    embed.add_field(
        name=f"Players ({alive_count} alive, {eliminated_count} eliminated)", 
        value=format_players(game_state) or "No players yet"
    )
    
    # Add game log field
    log_entries = game_state["game_log"][-5:]  # Show last 5 entries
    log_text = "\n".join(log_entries)
    embed.add_field(
        name="Game Log", 
        value=log_text,
        inline=False
    )
    
    # Add chamber info (debug info that can be removed in production)
    if not game_state["running"] and not game_state["waiting_for_players"]:
        chambers_info = " ".join(["🔴" if chamber else "⚪" for chamber in game_state["chambers"]])
        embed.add_field(
            name="Chambers Revealed", 
            value=chambers_info,
            inline=False
        )
    
    return embed

def format_players(game_state):
    """Format player names with their status"""
    player_strings = []
    
    # First add alive players
    for player_id, player_data in game_state["players"].items():
        if player_data["alive"]:
            status = "🟢" if player_data["alive"] else "💀"
            turns = player_data.get("turns_played", 0)
            player_strings.append(f"{status} {player_data['name']} ({turns} turns)")
    
    # Then add eliminated players
    for player_name in game_state["eliminated_players"]:
        player_strings.append(f"💀 ~~{player_name}~~")
    
    return "\n".join(player_strings)

def build_results_embed(game_state):
    """Create the final results embed"""
    # Player stats
    player_count = len(game_state["players"])
    alive_count = sum(1 for player in game_state["players"].values() if player["alive"])
    eliminated_count = len(game_state["eliminated_players"])
    
    # Determine color based on if there are winners
    color = 0x00ff00 if game_state["winners"] else 0xff0000
    
    # Create embed
    embed = discord.Embed(
        title="🔫 Russian Roulette - Game Over! 🎲",
        color=color
    )
    
    # Add winners or "everyone eliminated" message
    if game_state["winners"]:
        winners_text = ", ".join(game_state["winners"])
        embed.description = f"**WINNER:** {winners_text} 👑\nThey faced death and lived to tell the tale!"
    else:
        embed.description = "**GAME OVER**\nNo one survived! The Grim Reaper claims all!"
    
    # Add revolver visualization
    revolver = build_revolver_visual(game_state, reveal_all=True)
    embed.add_field(
        name="Final Chamber State",
        value=revolver,
        inline=False
    )
    
    # Add player stats
    embed.add_field(
        name=f"Players ({alive_count} alive, {eliminated_count} eliminated)", 
        value=format_players(game_state) or "No players participated",
        inline=False
    )
    
    # Add game log
    log_entries = game_state["game_log"][-8:]  # Show more entries in final results
    log_text = "\n".join(log_entries)
    embed.add_field(
        name="Game Log", 
        value=log_text,
        inline=False
    )
    
    return embed

def build_revolver_visual(game_state, reveal_all=False):
    """Create a visual representation of the revolver's chambers"""
    chambers = game_state["chambers"]
    current_pos = game_state["current_chamber"]
    
    # Create visuals for each chamber
    chamber_visuals = []
    for i in range(MAX_ROUNDS):
        if i < current_pos:
            # Already fired chambers
            if chambers[i]:
                chamber_visuals.append("💥")  # Fired, had bullet
            else:
                chamber_visuals.append("🔳")  # Fired, was empty
        elif i == current_pos and game_state["running"] and not game_state["waiting_for_players"]:
            chamber_visuals.append("🔄")  # Current chamber
        else:
            # Future chambers or game over reveal
            if reveal_all:
                if chambers[i]:
                    chamber_visuals.append("🔴")  # Unfired bullet
                else:
                    chamber_visuals.append("⚪")  # Unfired empty
            else:
                chamber_visuals.append("⬜")  # Unknown
    
    # Create the revolver visual
    revolver = " ".join(chamber_visuals)
    
    # Add additional info
    bullets_info = f"Revolver loaded with {game_state['bullet_count']} bullets"
    if reveal_all or (not game_state["waiting_for_players"] and current_pos > 0):
        bullets_info += f" | Fired: {current_pos}/{MAX_ROUNDS} chambers"
    
    return f"{revolver}\n{bullets_info}"

class RussianRouletteView(discord.ui.View):
    def __init__(self, game_state):
        super().__init__(timeout=None)
        self.game_state = game_state
        
        # Different buttons based on game state
        if game_state["waiting_for_players"]:
            self.add_item(JoinGameButton("Join Game", "join", "👤", discord.ButtonStyle.primary, 0))
        else:
            self.add_item(RoulettePullButton("Shoot Self", "self", "🎯", discord.ButtonStyle.danger, 0))
            self.add_item(RouletteOpponentButton("Shoot Opponent", "opponent", "👥", discord.ButtonStyle.secondary, 0))

class JoinGameButton(discord.ui.Button):
    def __init__(self, label, action_id, emoji, style, row):
        super().__init__(style=style, label=label, emoji=emoji, row=row)
        self.action_id = action_id
    
    async def callback(self, interaction: discord.Interaction):
        game_state = self.view.game_state
        
        # Check if game is still in waiting state
        if not game_state["waiting_for_players"]:
            return await interaction.response.send_message("The game has already started!", ephemeral=True)
        
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        
        # Check if player already joined
        if user_id in game_state["players"]:
            return await interaction.response.send_message("You've already joined this game!", ephemeral=True)
        
        # Check if game is full
        if len(game_state["players"]) >= PLAYERS_REQUIRED:
            return await interaction.response.send_message("This game is already full!", ephemeral=True)
        
        # Add player to the game
        game_state["players"][user_id] = {
            "name": user_name,
            "alive": True,
            "turns_played": 0
        }
        
        # Add to player order list
        game_state["player_ids"].append(user_id)
        
        # Update game log
        game_state["game_log"].append(f"👤 **{user_name}** has joined the game!")
        
        # Update the embed
        embed = build_waiting_embed(game_state)
        await interaction.response.edit_message(embed=embed)

class RouletteOpponentButton(discord.ui.Button):
    def __init__(self, label, action_id, emoji, style, row):
        super().__init__(style=style, label=label, emoji=emoji, row=row)
        self.action_id = action_id
    
    async def callback(self, interaction: discord.Interaction):
        game_state = self.view.game_state
        
        # Check if game is still running
        if not game_state["running"] or game_state["waiting_for_players"]:
            return await interaction.response.send_message(
                "The game isn't ready for play yet!" if game_state["waiting_for_players"] else "The game has ended!", 
                ephemeral=True
            )
        
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        
        # Check if it's this player's turn
        current_player_index = game_state["current_player_index"] % len(game_state["player_ids"])
        current_player_id = game_state["player_ids"][current_player_index]
        
        if user_id != current_player_id:
            current_player_name = game_state["players"][current_player_id]["name"]
            return await interaction.response.send_message(
                f"It's not your turn! Waiting for {current_player_name} to play.", 
                ephemeral=True
            )
        
        # Check if player is already eliminated
        if not game_state["players"][user_id]["alive"]:
            return await interaction.response.send_message(
                "You've been eliminated! You can't play anymore.", 
                ephemeral=True
            )
        
        # Find opponent (in a two-player game, it's the other player)
        opponent_id = None
        for player_id in game_state["player_ids"]:
            if player_id != user_id and game_state["players"][player_id]["alive"]:
                opponent_id = player_id
                break
        
        if opponent_id is None:
            return await interaction.response.send_message(
                "No opponent found to shoot at!", 
                ephemeral=True
            )
        
        opponent_name = game_state["players"][opponent_id]["name"]
        
        # Process their turn
        current_chamber = game_state["current_chamber"]
        if current_chamber < MAX_ROUNDS:
            # Check if current chamber has a bullet
            if game_state["chambers"][current_chamber]:
                # Opponent is eliminated
                game_state["players"][opponent_id]["alive"] = False
                game_state["eliminated_players"].append(opponent_name)
                game_state["game_log"].append(f"💥 **{user_name}** shot **{opponent_name}** and eliminated them!")
            else:
                # Shot missed
                game_state["game_log"].append(f"🔄 **{user_name}** shot at **{opponent_name}** but the chamber was empty!")
            
            # Increment player's turn count
            game_state["players"][user_id]["turns_played"] += 1
            
            # Move to next chamber
            game_state["current_chamber"] += 1
            
            # Move to next player's turn
            game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(game_state["player_ids"])
            
            # Skip eliminated players for next turn
            while (
                len(game_state["player_ids"]) > 0 and 
                not game_state["players"][game_state["player_ids"][game_state["current_player_index"]]]["alive"]
            ):
                game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(game_state["player_ids"])
        
        await interaction.response.defer()

class RoulettePullButton(discord.ui.Button):
    def __init__(self, label, action_id, emoji, style, row):
        super().__init__(style=style, label=label, emoji=emoji, row=row)
        self.action_id = action_id
    
    async def callback(self, interaction: discord.Interaction):
        game_state = self.view.game_state
        
        # Check if game is still running
        if not game_state["running"] or game_state["waiting_for_players"]:
            return await interaction.response.send_message(
                "The game isn't ready for play yet!" if game_state["waiting_for_players"] else "The game has ended!", 
                ephemeral=True
            )
        
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        
        # Check if it's this player's turn
        current_player_index = game_state["current_player_index"] % len(game_state["player_ids"])
        current_player_id = game_state["player_ids"][current_player_index]
        
        if user_id != current_player_id:
            current_player_name = game_state["players"][current_player_id]["name"]
            return await interaction.response.send_message(
                f"It's not your turn! Waiting for {current_player_name} to play.", 
                ephemeral=True
            )
        
        # Check if player is already eliminated
        if not game_state["players"][user_id]["alive"]:
            return await interaction.response.send_message(
                "You've been eliminated! You can't play anymore.", 
                ephemeral=True
            )
        
        # Process their turn
        current_chamber = game_state["current_chamber"]
        gets_extra_turn = False
        
        if current_chamber < MAX_ROUNDS:
            # Check if current chamber has a bullet
            if game_state["chambers"][current_chamber]:
                # Player is eliminated
                game_state["players"][user_id]["alive"] = False
                game_state["eliminated_players"].append(game_state["players"][user_id]["name"])
                game_state["game_log"].append(f"💥 **{user_name}** shot themself and was eliminated!")
            else:
                # Player survived this round and gets an extra turn
                game_state["game_log"].append(f"🔄 **{user_name}** shot themself, survived, and gets another turn!")
                gets_extra_turn = True
            
            # Increment player's turn count
            game_state["players"][user_id]["turns_played"] += 1
            
            # Move to next chamber
            game_state["current_chamber"] += 1
            
            # Only advance turn if player doesn't get an extra turn
            if not gets_extra_turn:
                # Move to next player's turn
                game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(game_state["player_ids"])
                
                # Skip eliminated players for next turn
                while (
                    len(game_state["player_ids"]) > 0 and 
                    not game_state["players"][game_state["player_ids"][game_state["current_player_index"]]]["alive"]
                ):
                    game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(game_state["player_ids"])
        
        await interaction.response.defer()

class CogRussianRoulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roulette(self, ctx: commands.Context, duration: int = GAME_DURATION):
        """Start a Russian Roulette game"""
        await RUSSIAN_ROULETTE(ctx, duration)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogRussianRoulette(bot))