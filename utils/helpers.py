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
