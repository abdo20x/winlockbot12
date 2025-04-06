import discord
from discord import app_commands
from discord.ext import commands
import logging
import sqlite3

import database as db
from config import EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR, ADMIN_USER_ID
from utils.embeds import create_team_embed
from utils.helpers import is_admin_or_captain

logger = logging.getLogger("blue_lock_bot")

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="اضافة_فريق", description="إضافة فريق جديد إلى السيرفر")
    @app_commands.describe(
        name="اسم الفريق",
        captain="كابتن الفريق (اختياري)",
        emoji="إيموجي الفريق (اختياري)"
    )
    @app_commands.default_permissions(administrator=True)
    async def add_team(
        self, 
        interaction: discord.Interaction, 
        name: str,
        captain: discord.Member = None,
        emoji: str = None
    ):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لإضافة فريق جديد.", ephemeral=True)
            return
            
        # Create team role
        try:
            role = await interaction.guild.create_role(name=name, mentionable=True)
            
            # Add captain to role if specified
            if captain:
                await captain.add_roles(role)
            
            # Add team to database
            captain_id = captain.id if captain else None
            team_id = db.add_team(interaction.guild.id, name, role.id, emoji, captain_id)
            
            if team_id is None:
                await interaction.response.send_message(f"فشل إنشاء الفريق: يوجد فريق بنفس الاسم بالفعل.", ephemeral=True)
                await role.delete()
                return
                
            # Add captain to the team in the database if specified
            if captain:
                db.add_player_to_team(interaction.guild.id, captain.id, team_id, "cap")
                
            # Create embed response
            embed = discord.Embed(
                title="✅ تم إنشاء الفريق بنجاح",
                description=f"تم إنشاء فريق **{name}** بنجاح",
                color=SUCCESS_COLOR
            )
            
            if emoji:
                embed.description += f" {emoji}"
            
            if captain:
                embed.add_field(name="الكابتن", value=captain.mention, inline=False)
                
            embed.add_field(name="الرتبة", value=role.mention, inline=False)
            
            # Send notification
            settings = db.get_guild_settings(interaction.guild.id)
            if settings and settings["notification_channel_id"]:
                try:
                    channel = self.bot.get_channel(settings["notification_channel_id"])
                    if channel:
                        await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار: {e}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الفريق: {e}")
            await interaction.response.send_message(f"حدث خطأ أثناء إنشاء الفريق: {e}", ephemeral=True)
        
    @app_commands.command(name="ازالة_فريق", description="إزالة فريق من السيرفر")
    @app_commands.describe(team_name="اسم الفريق الذي تريد إزالته")
    @app_commands.default_permissions(administrator=True)
    async def remove_team(self, interaction: discord.Interaction, team_name: str):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لإزالة فريق.", ephemeral=True)
            return
            
        # Get team information
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
            
        # Remove team from database
        if db.remove_team(interaction.guild.id, team["id"]):
            # Delete team role
            try:
                role = interaction.guild.get_role(team["role_id"])
                if role:
                    await role.delete()
            except Exception as e:
                logger.error(f"خطأ في حذف رتبة الفريق: {e}")
                
            # Create embed response
            embed = discord.Embed(
                title="✅ تم حذف الفريق",
                description=f"تم حذف فريق **{team_name}** بنجاح",
                color=SUCCESS_COLOR
            )
            
            # Send notification
            settings = db.get_guild_settings(interaction.guild.id)
            if settings and settings["notification_channel_id"]:
                try:
                    channel = self.bot.get_channel(settings["notification_channel_id"])
                    if channel:
                        await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار: {e}")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("حدث خطأ أثناء حذف الفريق.", ephemeral=True)
            
    @app_commands.command(name="فريق", description="عرض معلومات فريق محدد")
    @app_commands.describe(team_name="اسم الفريق الذي تريد عرض معلوماته")
    async def team_info(self, interaction: discord.Interaction, team_name: str):
        # Get team information
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
            
        # Create team embed
        embed = await create_team_embed(self.bot, interaction.guild, team)
        
        await interaction.response.send_message(embed=embed)
            
    @app_commands.command(name="الفرق", description="عرض قائمة الفرق المتاحة في السيرفر")
    async def list_teams(self, interaction: discord.Interaction):
        # Get all teams
        teams = db.get_all_teams(interaction.guild.id)
        
        if not teams:
            await interaction.response.send_message("لا توجد فرق مسجلة في هذا السيرفر.", ephemeral=True)
            return
            
        # Create embed response
        embed = discord.Embed(
            title="🏆 قائمة الفرق",
            description="جميع الفرق المسجلة في السيرفر",
            color=EMBED_COLOR
        )
        
        for team in teams:
            # Get team captain if exists
            captain_text = "غير معين"
            if team["captain_id"]:
                captain = interaction.guild.get_member(team["captain_id"])
                if captain:
                    captain_text = captain.mention
            
            # Get team role if exists
            role = interaction.guild.get_role(team["role_id"])
            role_text = role.mention if role else "غير موجود"
            
            # Get player count
            players = db.get_team_players(interaction.guild.id, team["id"])
            player_count = len(players)
            
            # Add team field
            team_emoji = team["emoji"] if team["emoji"] else "⚽"
            embed.add_field(
                name=f"{team_emoji} {team['name']}",
                value=f"الكابتن: {captain_text}\nالرتبة: {role_text}\nعدد اللاعبين: {player_count}",
                inline=False
            )
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        embed.set_footer(text="استخدم أمر /فريق متبوعًا باسم الفريق لعرض تفاصيل أكثر")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="روستر", description="عرض قائمة لاعبي فريق محدد")
    @app_commands.describe(team_name="اسم الفريق الذي تريد عرض لاعبيه")
    async def team_roster(self, interaction: discord.Interaction, team_name: str):
        # Get team information
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
            
        # Get team players
        players = db.get_team_players(interaction.guild.id, team["id"])
        
        # Get roster cap
        settings = db.get_guild_settings(interaction.guild.id)
        roster_cap = settings["roster_cap"]
        
        # Create embed response
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        embed = discord.Embed(
            title=f"{team_emoji} روستر فريق {team['name']}",
            description=f"عدد اللاعبين: {len(players)}/{roster_cap}",
            color=EMBED_COLOR
        )
        
        # Get captain info
        captain_name = "غير معين"
        if team["captain_id"]:
            captain = interaction.guild.get_member(team["captain_id"])
            if captain:
                captain_name = captain.display_name
        
        embed.add_field(name="🎖️ الكابتن", value=captain_name, inline=False)
        
        # Group players by position
        positions = {
            "cf": [],
            "rw": [],
            "lw": [],
            "cm": [],
            "gk": [],
            "": []
        }
        
        for player_data in players:
            # Skip captain as they're already listed
            if player_data["user_id"] == team["captain_id"]:
                continue
                
            player = interaction.guild.get_member(player_data["user_id"])
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
            "": "🔍 غير معين"
        }
        
        for position, players_list in positions.items():
            if not players_list:
                continue
                
            player_text = ""
            for player_data in players_list:
                player = interaction.guild.get_member(player_data["user_id"])
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
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="اعدادات", description="ضبط إعدادات السيرفر")
    @app_commands.describe(
        roster_cap="الحد الأقصى لعدد اللاعبين في الفريق",
        notification_channel="قناة إرسال إشعارات التعاقدات"
    )
    @app_commands.default_permissions(administrator=True)
    async def settings(
        self, 
        interaction: discord.Interaction, 
        roster_cap: int = None,
        notification_channel: discord.TextChannel = None
    ):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لضبط الإعدادات.", ephemeral=True)
            return
        
        # Get current settings
        current_settings = db.get_guild_settings(interaction.guild.id)
        
        # Update settings
        notification_channel_id = notification_channel.id if notification_channel else current_settings["notification_channel_id"]
        roster_cap_value = roster_cap if roster_cap is not None else current_settings["roster_cap"]
        
        db.update_guild_settings(
            interaction.guild.id,
            roster_cap=roster_cap_value,
            notification_channel_id=notification_channel_id
        )
        
        # Create embed response
        embed = discord.Embed(
            title="⚙️ إعدادات السيرفر",
            description="تم تحديث إعدادات السيرفر بنجاح",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="🧢 الحد الأقصى للاعبين",
            value=str(roster_cap_value),
            inline=True
        )
        
        notification_channel_text = "غير محدد"
        if notification_channel_id:
            channel = self.bot.get_channel(notification_channel_id)
            if channel:
                notification_channel_text = channel.mention
        
        embed.add_field(
            name="📢 قناة الإشعارات",
            value=notification_channel_text,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="اضافة_رتب", description="إعطاء صلاحيات للكابتن")
    @app_commands.describe(
        team_name="اسم الفريق",
        captain="الكابتن الجديد (اختياري)"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_captain_role(
        self, 
        interaction: discord.Interaction, 
        team_name: str,
        captain: discord.Member = None
    ):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لإعطاء صلاحيات الكابتن.", ephemeral=True)
            return
            
        # Get team information
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
        
        # Get current captain if exists
        current_captain = None
        if team["captain_id"]:
            current_captain = interaction.guild.get_member(team["captain_id"])
        
        # If no new captain is specified, just show current captain
        if not captain:
            if current_captain:
                await interaction.response.send_message(f"الكابتن الحالي لفريق **{team_name}** هو {current_captain.mention}", ephemeral=True)
            else:
                await interaction.response.send_message(f"فريق **{team_name}** ليس لديه كابتن حاليًا", ephemeral=True)
            return
        
        # Update team captain in database
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE teams SET captain_id = ? WHERE id = ? AND guild_id = ?",
            (captain.id, team["id"], interaction.guild.id)
        )
        
        conn.commit()
        conn.close()
        
        # Add captain to team in players table if not already
        player = db.get_player(interaction.guild.id, captain.id)
        if not player or player["team_id"] != team["id"]:
            db.add_player_to_team(interaction.guild.id, captain.id, team["id"], "cap")
        
        # Add team role to new captain
        role = interaction.guild.get_role(team["role_id"])
        if role:
            await captain.add_roles(role)
        
        # Create embed response
        embed = discord.Embed(
            title="✅ تم تعيين الكابتن",
            description=f"تم تعيين {captain.mention} ككابتن لفريق **{team_name}**",
            color=SUCCESS_COLOR
        )
        
        # Send notification
        settings = db.get_guild_settings(interaction.guild.id)
        if settings and settings["notification_channel_id"]:
            try:
                channel = self.bot.get_channel(settings["notification_channel_id"])
                if channel:
                    await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"خطأ في إرسال إشعار: {e}")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="تعاقد", description="التعاقد مع لاعب جديد للفريق")
    @app_commands.describe(
        player="اللاعب الذي تريد التعاقد معه",
        position="مركز اللاعب"
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="مهاجم (CF)", value="cf"),
        app_commands.Choice(name="جناح أيمن (RW)", value="rw"),
        app_commands.Choice(name="جناح أيسر (LW)", value="lw"),
        app_commands.Choice(name="لاعب وسط (CM)", value="cm"),
        app_commands.Choice(name="حارس مرمى (GK)", value="gk")
    ])
    async def sign_player(
        self, 
        interaction: discord.Interaction, 
        player: discord.Member,
        position: str
    ):
        # Check if user is a team captain
        team = db.get_team_by_captain(interaction.guild.id, interaction.user.id)
        if not team and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("هذا الأمر مقيد للكابتن فقط.", ephemeral=True)
            return
        
        # If admin is using this command, they need to specify which team
        if interaction.user.id == ADMIN_USER_ID and not team:
            await interaction.response.send_message(
                "أنت مسؤول، ولكن لم يتم تحديد الفريق. استخدم أمر /اضافة_رتب لتعيين نفسك ككابتن أولاً.",
                ephemeral=True
            )
            return
            
        # Check if player is already in a team
        player_data = db.get_player(interaction.guild.id, player.id)
        if player_data and player_data["team_id"] is not None:
            # Get the team name
            player_team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
            if player_team and player_team["id"] != team["id"]:
                await interaction.response.send_message(
                    f"هذا اللاعب منضم بالفعل إلى فريق **{player_team['name']}**. يجب إنهاء تعاقده أولاً.",
                    ephemeral=True
                )
                return
        
        # Check roster cap
        settings = db.get_guild_settings(interaction.guild.id)
        roster_cap = settings["roster_cap"]
        
        team_players = db.get_team_players(interaction.guild.id, team["id"])
        if len(team_players) >= roster_cap:
            await interaction.response.send_message(
                f"لقد وصلت إلى الحد الأقصى من اللاعبين ({roster_cap}).",
                ephemeral=True
            )
            return
        
        # Add player to team
        db.add_player_to_team(interaction.guild.id, player.id, team["id"], position)
        
        # Add team role to player
        role = interaction.guild.get_role(team["role_id"])
        if role:
            await player.add_roles(role)
        
        # Create embed response
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        embed = discord.Embed(
            title="✅ تم التعاقد",
            description=f"تم التعاقد مع {player.mention} لفريق **{team['name']}** {team_emoji}",
            color=SUCCESS_COLOR
        )
        
        position_names = {
            "cf": "⚔️ مهاجم (CF)",
            "rw": "🏹 جناح أيمن (RW)",
            "lw": "🏹 جناح أيسر (LW)",
            "cm": "🛡️ لاعب وسط (CM)",
            "gk": "🧤 حارس مرمى (GK)"
        }
        
        embed.add_field(name="المركز", value=position_names.get(position, "غير معروف"), inline=True)
        
        # Send notification
        if settings and settings["notification_channel_id"]:
            try:
                channel = self.bot.get_channel(settings["notification_channel_id"])
                if channel:
                    await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"خطأ في إرسال إشعار: {e}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="فسخ_تعاقد", description="إنهاء تعاقد لاعب من الفريق")
    @app_commands.describe(player="اللاعب الذي تريد إنهاء تعاقده")
    async def release_player(self, interaction: discord.Interaction, player: discord.Member):
        # Check if user is a team captain or admin
        is_captain = is_admin_or_captain(interaction, interaction.user.id)
        if not is_captain:
            await interaction.response.send_message("هذا الأمر مقيد للكابتن فقط.", ephemeral=True)
            return
        
        # Get captain's team
        team = db.get_team_by_captain(interaction.guild.id, interaction.user.id)
        
        # If admin is using the command and is not a captain
        if interaction.user.id == ADMIN_USER_ID and not team:
            # Get player's team
            player_data = db.get_player(interaction.guild.id, player.id)
            if not player_data or player_data["team_id"] is None:
                await interaction.response.send_message(
                    "هذا اللاعب ليس منضمًا إلى أي فريق.",
                    ephemeral=True
                )
                return
            
            team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
        elif not team:
            await interaction.response.send_message("لم يتم العثور على فريقك.", ephemeral=True)
            return
        
        # Check if player is in captain's team
        player_data = db.get_player(interaction.guild.id, player.id)
        if not player_data or player_data["team_id"] != team["id"]:
            await interaction.response.send_message(
                "هذا اللاعب ليس في فريقك.",
                ephemeral=True
            )
            return
        
        # Check if player is the captain
        if player.id == team["captain_id"] and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message(
                "لا يمكنك إنهاء تعاقد الكابتن. استخدم أمر /اضافة_رتب لتغيير الكابتن أولاً.",
                ephemeral=True
            )
            return
        
        # Remove player from team
        db.remove_player_from_team(interaction.guild.id, player.id)
        
        # Remove team role from player
        role = interaction.guild.get_role(team["role_id"])
        if role:
            await player.remove_roles(role)
        
        # Create embed response
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        embed = discord.Embed(
            title="✅ تم إنهاء التعاقد",
            description=f"تم إنهاء تعاقد {player.mention} من فريق **{team['name']}** {team_emoji}",
            color=SUCCESS_COLOR
        )
        
        # Send notification
        settings = db.get_guild_settings(interaction.guild.id)
        if settings and settings["notification_channel_id"]:
            try:
                channel = self.bot.get_channel(settings["notification_channel_id"])
                if channel:
                    await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"خطأ في إرسال إشعار: {e}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Teams(bot))
