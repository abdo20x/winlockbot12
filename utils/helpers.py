import discord
from config import ADMIN_USER_ID
import database as db

def is_admin_or_captain(interaction: discord.Interaction, user_id: int):
    """Check if a user is an admin or a team captain"""
    # Check if user is admin
    if user_id == ADMIN_USER_ID or interaction.user.guild_permissions.administrator:
        return True
    
    # Check if user is a team captain
    return db.is_team_captain(interaction.guild.id, user_id)

def is_captain_or_vice_captain(interaction: discord.Interaction, user_id: int):
    """Check if a user is a captain or vice-captain of any team"""
    # Check if user is admin (always gets permission)
    if user_id == ADMIN_USER_ID:
        return True
    
    # Check if user is a team captain
    if db.is_team_captain(interaction.guild.id, user_id):
        return True
    
    # Get user's team if they are in one
    player_data = db.get_player(interaction.guild.id, user_id)
    if not player_data or player_data["team_id"] is None:
        return False
    
    # Check if they have the position of "vc" (vice captain)
    if player_data["position"] == "vc":
        return True
        
    return False
