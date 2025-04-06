import discord
from discord import app_commands
from discord.ext import commands
import logging

import database as db
from config import EMBED_COLOR, ERROR_COLOR, ADMIN_USER_ID

logger = logging.getLogger("blue_lock_bot")

class PlayerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="لاعب", description="عرض إحصائيات لاعب")
    @app_commands.describe(player="اللاعب الذي تريد عرض إحصائياته")
    async def player_stats(self, interaction: discord.Interaction, player: discord.Member = None):
        # If no player specified, default to the command user
        target_player = player or interaction.user
        
        # Get player data
        player_data = db.get_player(interaction.guild.id, target_player.id)
        
        if not player_data:
            # Create a new player entry with zero stats
            db.update_player_stats(interaction.guild.id, target_player.id, 0, 0, 0)
            player_data = {
                "user_id": target_player.id,
                "guild_id": interaction.guild.id,
                "team_id": None,
                "position": None,
                "goals": 0,
                "assists": 0,
                "saves": 0,
                "balance": 0
            }
        
        # Get player team if exists
        team_name = "بدون فريق"
        team_emoji = ""
        
        if player_data["team_id"]:
            team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else ""
        
        # Create embed response
        embed = discord.Embed(
            title=f"📊 إحصائيات {target_player.display_name}",
            description=f"معلومات وإحصائيات اللاعب",
            color=EMBED_COLOR
        )
        
        embed.set_thumbnail(url=target_player.display_avatar.url)
        
        # Add team info
        embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=False)
        
        # Add position if in a team
        if player_data["position"]:
            position_names = {
                "cf": "⚔️ مهاجم (CF)",
                "rw": "🏹 جناح أيمن (RW)",
                "lw": "🏹 جناح أيسر (LW)",
                "cm": "🛡️ لاعب وسط (CM)",
                "gk": "🧤 حارس مرمى (GK)",
                "cap": "🎖️ كابتن"
            }
            
            position = position_names.get(player_data["position"], "غير معروف")
            embed.add_field(name="المركز", value=position, inline=True)
        
        # Add statistics
        embed.add_field(name="⚽ الأهداف", value=str(player_data["goals"]), inline=True)
        embed.add_field(name="👟 التمريرات", value=str(player_data["assists"]), inline=True)
        embed.add_field(name="🧤 التصديات", value=str(player_data["saves"]), inline=True)
        
        # Calculate total score
        total_score = player_data["goals"] + player_data["assists"] + player_data["saves"]
        embed.add_field(name="📈 مجموع النقاط", value=str(total_score), inline=True)
        
        # Add balance
        embed.add_field(
            name="💰 الرصيد",
            value=f"{player_data['balance']:,} بلو باك",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PlayerStats(bot))
