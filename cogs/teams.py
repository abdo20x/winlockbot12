import discord
from discord import app_commands
from discord.ext import commands
import logging
import sqlite3

import database as db
from config import EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR, ADMIN_USER_ID
from utils.embeds import create_team_embed
from utils.helpers import is_admin_or_captain, is_captain_or_vice_captain

logger = logging.getLogger("blue_lock_bot")

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # Add regular text commands (not slash commands)
    @commands.command(name="فريق")
    async def team_cmd(self, ctx, *, team_name=None):
        """عرض معلومات فريق محدد"""
        if not team_name:
            await ctx.send("يرجى تحديد اسم الفريق. مثال: !فريق باسترز")
            return
            
        # Get team information
        team = db.get_team(ctx.guild.id, team_name=team_name)
        
        if not team:
            await ctx.send(f"لم يتم العثور على فريق باسم **{team_name}**")
            return
            
        # Create team embed
        embed = await create_team_embed(self.bot, ctx.guild, team)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="الفرق")
    async def teams_cmd(self, ctx):
        """عرض قائمة الفرق المتاحة في السيرفر"""
        # Get all teams
        teams = db.get_all_teams(ctx.guild.id)
        
        if not teams:
            await ctx.send("لا توجد فرق مسجلة في هذا السيرفر.")
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
                captain = ctx.guild.get_member(team["captain_id"])
                if captain:
                    captain_text = captain.mention
            
            # Get team role if exists
            role = ctx.guild.get_role(team["role_id"])
            role_text = role.mention if role else "غير موجود"
            
            # Get player count
            players = db.get_team_players(ctx.guild.id, team["id"])
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
        embed.set_footer(text="استخدم أمر !فريق متبوعًا باسم الفريق لعرض تفاصيل أكثر")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="روستر")
    async def roster_cmd(self, ctx, *, team_name=None):
        """عرض قائمة لاعبي فريق محدد أو جميع الفرق"""
        # Get roster cap
        settings = db.get_guild_settings(ctx.guild.id)
        roster_cap = settings["roster_cap"]
        
        # If no team name specified, show all teams
        if not team_name:
            # Get all teams
            teams = db.get_all_teams(ctx.guild.id)
            
            if not teams:
                await ctx.send("لا توجد فرق مسجلة في هذا السيرفر.")
                return
                
            # Create embed response
            embed = discord.Embed(
                title="📋 قائمة الفرق",
                description=f"عرض عدد الأعضاء بكل فريق",
                color=EMBED_COLOR
            )
            
            # Iterate through teams
            for team in teams:
                # Get team role
                role = ctx.guild.get_role(team["role_id"])
                role_name = role.name if role else team["name"]
                role_mention = role.mention if role else team["name"]
                
                # Count members with this role
                role_members_count = len(role.members) if role else 0
                
                # Get captain info
                captain_name = "غير معين"
                if team["captain_id"]:
                    captain = ctx.guild.get_member(team["captain_id"])
                    if captain:
                        captain_name = captain.mention
                
                # Get team emoji
                team_emoji = team["emoji"] if team["emoji"] else "⚽"
                
                # Get registered players count 
                players = db.get_team_players(ctx.guild.id, team["id"])
                player_count = len(players)
                
                # Add team field
                embed.add_field(
                    name=f"{team_emoji} {role_name}",
                    value=f"👥 عدد الأعضاء: **{role_members_count}**",
                    inline=True
                )
                
            # Add thumbnail and footer
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
            embed.set_footer(text="استخدم أمر !روستر متبوعًا باسم الفريق لعرض تفاصيل الفريق المحدد")
            
            await ctx.send(embed=embed)
            return
        
        # If team name specified, show that team's roster
        team = db.get_team(ctx.guild.id, team_name=team_name)
        
        if not team:
            await ctx.send(f"لم يتم العثور على فريق باسم **{team_name}**")
            return
            
        # Get team players
        players = db.get_team_players(ctx.guild.id, team["id"])
        
        # Get roster cap
        settings = db.get_guild_settings(ctx.guild.id)
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
            captain = ctx.guild.get_member(team["captain_id"])
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
                
            player = ctx.guild.get_member(player_data["user_id"])
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
                player = ctx.guild.get_member(player_data["user_id"])
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
        
        await ctx.send(embed=embed)
        
    @app_commands.command(name="اضافة_فريق", description="إضافة فريق جديد إلى السيرفر باستخدام رتبة موجودة")
    @app_commands.describe(
        role="رتبة الفريق",
        emoji="إيموجي الفريق (اختياري)"
    )
    async def add_team(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role,
        emoji: str = None
    ):
        # Check if user is the admin (only you can use this command)
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("فقط مالك البوت يمكنه إضافة فرق جديدة.", ephemeral=True)
            return
        
        try:
            # Use role name as team name
            name = role.name
            
            # Check if team with this name already exists
            existing_team = db.get_team(interaction.guild.id, team_name=name)
            if existing_team:
                await interaction.response.send_message(f"يوجد فريق بهذا الاسم بالفعل: **{name}**", ephemeral=True)
                return
                
            # Check if team with this role already exists
            existing_role_team = db.get_team(interaction.guild.id, role_id=role.id)
            if existing_role_team:
                await interaction.response.send_message(f"هذه الرتبة مستخدمة بالفعل لفريق: **{existing_role_team['name']}**", ephemeral=True)
                return
            
            # Add team to database with no captain (None)
            team_id = db.add_team(interaction.guild.id, name, role.id, emoji, None)
            
            if team_id is None:
                await interaction.response.send_message(f"فشل إنشاء الفريق: حدث خطأ في قاعدة البيانات.", ephemeral=True)
                return
                
            # Create embed response
            embed = discord.Embed(
                title="✅ تم إنشاء الفريق بنجاح",
                description=f"تم إنشاء فريق **{name}** بنجاح",
                color=SUCCESS_COLOR
            )
            
            if emoji:
                embed.description += f" {emoji}"
                
            embed.add_field(name="الرتبة", value=role.mention, inline=False)
            
            # Count members with this role
            role_members_count = len(role.members)
            embed.add_field(name="عدد الأعضاء بالرتبة", value=f"{role_members_count} عضو", inline=False)
            
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
    @app_commands.describe(role="رتبة الفريق الذي تريد إزالته")
    async def remove_team(self, interaction: discord.Interaction, role: discord.Role):
        # Check if user is the admin (only you can use this command)
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("فقط مالك البوت يمكنه إزالة الفرق.", ephemeral=True)
            return
            
        # Get team information based on role
        team = db.get_team(interaction.guild.id, role_id=role.id)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق بالرتبة {role.mention}", ephemeral=True)
            return
            
        team_name = team["name"]
            
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
    
    @app_commands.command(name="روستر", description="عرض قائمة الفرق وعدد الأعضاء لكل فريق")
    @app_commands.describe(team_name="اسم الفريق المحدد (اختياري)")
    async def team_roster(self, interaction: discord.Interaction, team_name: str = None):
        # Get roster cap
        settings = db.get_guild_settings(interaction.guild.id)
        roster_cap = settings["roster_cap"]
        
        # If a specific team is requested
        if team_name:
            # Get team information
            team = db.get_team(interaction.guild.id, team_name=team_name)
            
            if not team:
                await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
                return
                
            # Get team players
            players = db.get_team_players(interaction.guild.id, team["id"])
            
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
        
        # If no team specified, show all teams
        else:
            # Get all teams
            teams = db.get_all_teams(interaction.guild.id)
            
            if not teams:
                await interaction.response.send_message("لا توجد فرق مسجلة في هذا السيرفر.", ephemeral=True)
                return
                
            # Create embed response
            embed = discord.Embed(
                title="📋 قائمة الفرق",
                description=f"عرض عدد الأعضاء بكل فريق",
                color=EMBED_COLOR
            )
            
            # Iterate through teams
            for team in teams:
                # Get team role
                role = interaction.guild.get_role(team["role_id"])
                role_name = role.name if role else team["name"]
                role_mention = role.mention if role else team["name"]
                
                # Count members with this role
                role_members_count = len(role.members) if role else 0
                
                # Get captain info
                captain_name = "غير معين"
                if team["captain_id"]:
                    captain = interaction.guild.get_member(team["captain_id"])
                    if captain:
                        captain_name = captain.mention
                
                # Get team emoji
                team_emoji = team["emoji"] if team["emoji"] else "⚽"
                
                # Get registered players count 
                players = db.get_team_players(interaction.guild.id, team["id"])
                player_count = len(players)
                
                # Count players by role
                captain_count = 0
                vice_captain_count = 0
                normal_player_count = 0
                
                for player_data in players:
                    position = player_data["position"] or ""
                    if position == "cap":
                        captain_count += 1
                    elif position == "vc":
                        vice_captain_count += 1
                    else:
                        normal_player_count += 1
                
                # Add team field
                embed.add_field(
                    name=f"{team_emoji} {role_name}",
                    value=f"👥 عدد الأعضاء: **{role_members_count}**",
                    inline=True
                )
        
        # Add detailed player information only if a specific team is requested
        if team_name:
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
        
        # Add footer with help text
        if team_name:
            embed.set_footer(text="استخدم أمر /روستر بدون اسم فريق لعرض جميع الفرق")
        else:
            embed.set_footer(text="استخدم أمر /روستر متبوعًا باسم الفريق لعرض تفاصيل الفريق المحدد")
            
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="اعدادات", description="ضبط إعدادات السيرفر")
    @app_commands.describe(
        roster_cap="الحد الأقصى لعدد اللاعبين في الفريق",
        notification_channel="قناة إرسال إشعارات التعاقدات"
    )
    async def settings(
        self, 
        interaction: discord.Interaction, 
        roster_cap: int = None,
        notification_channel: discord.TextChannel = None
    ):
        # Check if user is the admin (only you can use this command)
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("فقط مالك البوت يمكنه ضبط الإعدادات.", ephemeral=True)
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
    
    @app_commands.command(name="اضافة_رتب", description="تعيين كابتن أو نائب كابتن للفريق")
    @app_commands.describe(
        role="رتبة الفريق",
        captain="العضو المراد تعيينه",
        role_type="نوع الرتبة (كابتن/نائب)"
    )
    @app_commands.choices(role_type=[
        app_commands.Choice(name="🎖️ كابتن", value="captain"),
        app_commands.Choice(name="🥈 نائب كابتن", value="vice"),
        app_commands.Choice(name="🎽 لاعب عادي", value="player")
    ])
    async def set_captain_role(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role,
        captain: discord.Member = None,
        role_type: str = "captain"
    ):
        # Check if user is the admin (only you can use this command)
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("فقط مالك البوت يمكنه تعيين الكابتن أو نائب الكابتن.", ephemeral=True)
            return
            
        # Get team information based on role
        team = db.get_team(interaction.guild.id, role_id=role.id)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق بالرتبة {role.mention}", ephemeral=True)
            return
            
        team_name = team["name"]
        
        # If no new member is specified, just show current captain/vice-captain info
        if not captain:
            # Get current captain if exists
            current_captain = None
            if team["captain_id"]:
                current_captain = interaction.guild.get_member(team["captain_id"])
                
            # Find vice-captain (if any)
            current_vice = None
            team_players = db.get_team_players(interaction.guild.id, team["id"])
            for player_data in team_players:
                if player_data["position"] == "vc":
                    current_vice = interaction.guild.get_member(player_data["user_id"])
                    break
                
            # Create info message
            info_message = f"معلومات فريق **{team_name}**:\n"
            if current_captain:
                info_message += f"الكابتن: {current_captain.mention}\n"
            else:
                info_message += "الكابتن: غير معين\n"
                
            if current_vice:
                info_message += f"نائب الكابتن: {current_vice.mention}"
            else:
                info_message += "نائب الكابتن: غير معين"
                
            await interaction.response.send_message(info_message, ephemeral=True)
            return
        
        # Check if player is already in a team
        player = db.get_player(interaction.guild.id, captain.id)
        if player and player["team_id"] is not None and player["team_id"] != team["id"]:
            # Get the player's team name
            player_team = db.get_team(interaction.guild.id, team_id=player["team_id"])
            if player_team:
                await interaction.response.send_message(
                    f"هذا اللاعب منضم بالفعل إلى فريق **{player_team['name']}**. يجب إنهاء تعاقده أولاً.",
                    ephemeral=True
                )
                return
                
        # Process based on role type
        if role_type == "captain":
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
            if not player or player["team_id"] != team["id"]:
                db.add_player_to_team(interaction.guild.id, captain.id, team["id"], "cap")
            else:
                # Update existing player's position to captain
                conn = db.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET position = 'cap' WHERE user_id = ? AND guild_id = ?",
                    (captain.id, interaction.guild.id)
                )
                conn.commit()
                conn.close()
                
            title = "✅ تم تعيين الكابتن"
            description = f"تم تعيين {captain.mention} ككابتن لفريق **{team_name}**"
        elif role_type == "vice":  # vice-captain
            # Add player as vice-captain to team
            if not player or player["team_id"] != team["id"]:
                db.add_player_to_team(interaction.guild.id, captain.id, team["id"], "vc")
            else:
                # Update existing player's position to vice-captain
                conn = db.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET position = 'vc' WHERE user_id = ? AND guild_id = ?",
                    (captain.id, interaction.guild.id)
                )
                conn.commit()
                conn.close()
                
            title = "✅ تم تعيين نائب الكابتن"
            description = f"تم تعيين {captain.mention} كنائب كابتن لفريق **{team_name}**"
        else:  # normal player
            # Add player as regular player to team
            if not player or player["team_id"] != team["id"]:
                db.add_player_to_team(interaction.guild.id, captain.id, team["id"], "player")
            else:
                # Update existing player's position to regular player
                conn = db.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET position = 'player' WHERE user_id = ? AND guild_id = ?",
                    (captain.id, interaction.guild.id)
                )
                conn.commit()
                conn.close()
                
            title = "✅ تم تعيين لاعب"
            description = f"تم تعيين {captain.mention} كلاعب في فريق **{team_name}**"
        
        # Add team role to the player
        role = interaction.guild.get_role(team["role_id"])
        if role:
            await captain.add_roles(role)
        
        # Create embed response
        embed = discord.Embed(
            title=title,
            description=description,
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
        
    @app_commands.command(name="تعاقد", description="التعاقد مع لاعب جديد للفريق مقابل مبلغ محدد")
    @app_commands.describe(
        player="اللاعب الذي تريد التعاقد معه"
    )
    async def sign_player(
        self, 
        interaction: discord.Interaction, 
        player: discord.Member
    ):
        # Check if user is a team captain or vice-captain
        is_authorized = is_captain_or_vice_captain(interaction, interaction.user.id)
        if not is_authorized:
            await interaction.response.send_message("هذا الأمر مقيد للكابتن أو نائب الكابتن فقط.", ephemeral=True)
            return
        
        # Get the team (for captains or admin)
        team = db.get_team_by_captain(interaction.guild.id, interaction.user.id)
        
        # If user is vice captain, need to get their team
        if not team and interaction.user.id != ADMIN_USER_ID:
            player_data = db.get_player(interaction.guild.id, interaction.user.id)
            if player_data and player_data["team_id"] is not None and player_data["position"] == "vc":
                team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
        
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
            
        # Check player price and team captain's balance
        player_price = 0
        if player_data:
            player_price = player_data.get("price", 0) or 0
            
        # Admin can bypass the price check
        if interaction.user.id != ADMIN_USER_ID and player_price > 0:
            # Get captain's balance
            captain_data = db.get_player(interaction.guild.id, interaction.user.id)
            captain_balance = captain_data["balance"] if captain_data else 0
            
            if captain_balance < player_price:
                await interaction.response.send_message(
                    f"ليس لديك رصيد كافٍ للتعاقد مع هذا اللاعب. سعر اللاعب: {player_price:,} بلو باك، رصيدك: {captain_balance:,} بلو باك",
                    ephemeral=True
                )
                return
                
            # Deduct coins from captain
            db.update_player_balance(interaction.guild.id, interaction.user.id, -player_price)
            
            # Add coins to player if they exist in database
            if player_data:
                db.update_player_balance(interaction.guild.id, player.id, player_price)
        
        # استخدام مركز "لاعب" كافتراضي
        position = "player"
        
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
        
        # Add price field if a transaction occurred
        if player_price > 0 and interaction.user.id != ADMIN_USER_ID:
            embed.add_field(name="💲 سعر التعاقد", value=f"{player_price:,} بلو باك", inline=True)
        
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
        # Check if user is a team captain or vice-captain
        is_authorized = is_captain_or_vice_captain(interaction, interaction.user.id)
        if not is_authorized:
            await interaction.response.send_message("هذا الأمر مقيد للكابتن أو نائب الكابتن فقط.", ephemeral=True)
            return
        
        # Get the team (for captains or admin)
        team = db.get_team_by_captain(interaction.guild.id, interaction.user.id)
        
        # If user is vice captain, need to get their team
        if not team and interaction.user.id != ADMIN_USER_ID:
            player_data = db.get_player(interaction.guild.id, interaction.user.id)
            if player_data and player_data["team_id"] is not None and player_data["position"] == "vc":
                team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
                
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
