import discord
from discord import app_commands
from discord.ext import commands
import logging

import database as db
from config import EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR, ADMIN_USER_ID

logger = logging.getLogger("blue_lock_bot")

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ستاتس", description="إضافة أو تعديل إحصائيات لاعب")
    @app_commands.describe(
        player="اللاعب الذي تريد تعديل إحصائياته",
        goals="عدد الأهداف",
        assists="عدد التمريرات الحاسمة",
        saves="عدد التصديات"
    )
    async def update_stats(
        self, 
        interaction: discord.Interaction, 
        player: discord.Member,
        goals: int = None,
        assists: int = None,
        saves: int = None
    ):
        # Check if user is the admin
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لاستخدام هذا الأمر.", ephemeral=True)
            return
        
        # Get current player stats
        player_data = db.get_player(interaction.guild.id, player.id)
        
        current_goals = player_data["goals"] if player_data else 0
        current_assists = player_data["assists"] if player_data else 0
        current_saves = player_data["saves"] if player_data else 0
        
        # Update player stats
        db.update_player_stats(
            interaction.guild.id,
            player.id,
            goals if goals is not None else current_goals,
            assists if assists is not None else current_assists,
            saves if saves is not None else current_saves
        )
        
        # Get updated player data
        updated_player = db.get_player(interaction.guild.id, player.id)
        
        # Get player team if exists
        team_name = "بدون فريق"
        team_emoji = ""
        
        if updated_player and updated_player["team_id"]:
            team = db.get_team(interaction.guild.id, team_id=updated_player["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else ""
        
        # Create embed response
        embed = discord.Embed(
            title="📊 تحديث الإحصائيات",
            description=f"تم تحديث إحصائيات {player.mention} بنجاح",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=False)
        
        if goals is not None:
            embed.add_field(name="⚽ الأهداف", value=f"{goals}", inline=True)
        
        if assists is not None:
            embed.add_field(name="👟 التمريرات الحاسمة", value=f"{assists}", inline=True)
        
        if saves is not None:
            embed.add_field(name="🧤 التصديات", value=f"{saves}", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
