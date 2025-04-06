import discord
from discord.ext import commands
import database as db
from config import EMBED_COLOR

async def create_team_embed(bot, guild, team):
    """Create a rich embed for team information"""
    # Get team captain if exists
    captain_text = "غير معين"
    if team["captain_id"]:
        captain = guild.get_member(team["captain_id"])
        if captain:
            captain_text = captain.mention
    
    # Get team role if exists
    role = guild.get_role(team["role_id"])
    role_text = role.mention if role else "غير موجود"
    
    # Get team players
    players = db.get_team_players(guild.id, team["id"])
    
    # Get guild settings
    settings = db.get_guild_settings(guild.id)
    roster_cap = settings["roster_cap"]
    
    # Create embed
    team_emoji = team["emoji"] if team["emoji"] else "⚽"
    embed = discord.Embed(
        title=f"{team_emoji} فريق {team['name']}",
        description=f"معلومات الفريق وقائمة اللاعبين",
        color=EMBED_COLOR
    )
    
    embed.add_field(name="الكابتن", value=captain_text, inline=True)
    embed.add_field(name="الرتبة", value=role_text, inline=True)
    embed.add_field(name="عدد اللاعبين", value=f"{len(players)}/{roster_cap}", inline=True)
    
    # Group players by position
    positions = {
        "cf": [],
        "rw": [],
        "lw": [],
        "cm": [],
        "gk": [],
        "cap": [],
        "": []
    }
    
    for player_data in players:
        player = guild.get_member(player_data["user_id"])
        if not player:
            continue
        
        position = player_data["position"] or ""
        if position not in positions:
            positions[""] += [player_data]
        else:
            positions[position] += [player_data]
    
    # Add position fields
    position_names = {
        "cf": "⚔️ المهاجمين (CF)",
        "rw": "🏹 الجناح الأيمن (RW)",
        "lw": "🏹 الجناح الأيسر (LW)",
        "cm": "🛡️ لاعبي الوسط (CM)",
        "gk": "🧤 حراس المرمى (GK)",
        "cap": "🎖️ الكابتن",
        "": "🔍 غير معين"
    }
    
    # Always show captain first if exists
    if positions["cap"]:
        player_text = ""
        for player_data in positions["cap"]:
            player = guild.get_member(player_data["user_id"])
            if player:
                stats = f"⚽ {player_data['goals']} | 👟 {player_data['assists']}"
                player_text += f"{player.mention} - {stats}\n"
        
        if player_text:
            embed.add_field(
                name=position_names["cap"],
                value=player_text,
                inline=False
            )
    
    # Add other positions
    for position, players_list in positions.items():
        if position == "cap" or not players_list:
            continue
        
        player_text = ""
        for player_data in players_list:
            player = guild.get_member(player_data["user_id"])
            if player:
                stats = f"⚽ {player_data['goals']} | 👟 {player_data['assists']}"
                if position == "gk":
                    stats = f"🧤 {player_data['saves']}"
                player_text += f"{player.mention} - {stats}\n"
        
        if player_text:
            embed.add_field(
                name=position_names[position],
                value=player_text,
                inline=False
            )
    
    if not any(len(p) > 0 for p in positions.values()):
        embed.add_field(name="📝 ملاحظة", value="لا يوجد لاعبين في هذا الفريق حاليًا", inline=False)
    
    # Add thumbnail
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
    
    return embed
