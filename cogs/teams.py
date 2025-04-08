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

def get_role_member_count(guild, role_id):
    """الحصول على عدد الأعضاء الذين يملكون رتبة معينة"""
    role = guild.get_role(role_id)
    if role:
        return len(role.members)
    return 0

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.animator = None  # سيتم تهيئة هذا المتغير عند ربط الفرق بالمؤثرات
        
    # Add regular text commands (not slash commands)
    @commands.command(name="عرض")
    async def offer_cmd(self, ctx, player: discord.Member, amount: int):
        """تقديم عرض للتعاقد مع لاعب"""
        # التحقق من وجود قناة للتعاقدات
        settings = db.get_guild_settings(ctx.guild.id)
        if not settings.get("contract_channel_id"):
            await ctx.send("لم يتم تعيين قناة للتعاقدات. يرجى استخدام أمر /اضافة_روم_الانتقالات أولاً.")
            return
            
        # إنشاء تفاعل اصطناعي
        fake_interaction = type('FakeInteraction', (), {
            'guild': ctx.guild,
            'guild_id': ctx.guild.id,
            'user': ctx.author,
            'channel': ctx.channel
        })
        fake_interaction.user = ctx.author
        fake_interaction.response = type('FakeResponse', (), {})
        
        async def send_message(content=None, embed=None, view=None, ephemeral=False):
            if content:
                await ctx.send(content)
            elif embed:
                await ctx.send(embed=embed)
        
        fake_interaction.response.send_message = send_message
        
        # استدعاء الأمر الأصلي
        await self.make_offer(fake_interaction, player, amount)
        
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
        
        # Count players by role assignment
        role = ctx.guild.get_role(team["role_id"])
        role_members_count = len(role.members) if role else 0
        
        # Create embed response
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        embed = discord.Embed(
            title=f"{team_emoji} روستر فريق {team['name']}",
            description=f"عدد اللاعبين: {role_members_count}/{roster_cap}",
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
            
    # تم حذف أوامر /فريق و /الفرق حسب طلب المستخدم
    
    @app_commands.command(name="عرض_شعار", description="عرض شعار الفريق بتأثير متحرك")
    @app_commands.describe(
        team_name="اسم الفريق المراد عرض شعاره",
        logo_url="رابط شعار الفريق (اختياري، سيتم استخدام الشعار الافتراضي في حال عدم توفره)"
    )
    async def show_team_logo(
        self, 
        interaction: discord.Interaction, 
        team_name: str,
        logo_url: str = None
    ):
        # التحقق من أن مستخدم البوت هو مالك البوت أو كابتن الفريق
        if interaction.user.id != ADMIN_USER_ID and not is_captain_or_vice_captain(interaction, interaction.user.id):
            await interaction.response.send_message("هذا الأمر متاح فقط للمشرفين وقادة الفرق.", ephemeral=True)
            return
            
        # نبحث عن الفريق في قاعدة البيانات
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
            
        # إذا لم يتم توفير رابط للشعار، نستخدم الشعار الافتراضي
        if not logo_url:
            logo_url = "https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
            
        # الحصول على معلومات الفريق
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        
        # الحصول على عدد اللاعبين
        players = db.get_team_players(interaction.guild.id, team["id"])
        player_count = len(players)
        
        # الحصول على معلومات الكابتن
        captain_info = "غير معين"
        if team["captain_id"]:
            captain = interaction.guild.get_member(team["captain_id"])
            if captain:
                captain_info = f"{captain.mention} • {captain.display_name}"
        
        # إنشاء حقول للعرض
        fields = [
            {'name': '👑 الكابتن', 'value': captain_info, 'inline': False},
            {'name': '👥 عدد اللاعبين', 'value': f"{player_count} لاعب", 'inline': True}
        ]
        
        # رسالة الانتظار
        await interaction.response.send_message("جاري تحميل شعار الفريق، انتظر قليلاً...")
        
        # التحقق من وجود فئة المؤثرات
        if self.animator:
            # عرض شعار الفريق بتأثير متحرك
            await self.animator.animate_logo_reveal(
                channel=interaction.channel,
                team_name=team_name,
                logo_url=logo_url,
                emoji=team_emoji,
                description=f"شعار فريق {team_name}",
                fields=fields
            )
        else:
            # إذا لم يتم تحميل فئة المؤثرات، نعرض الشعار بطريقة عادية
            embed = discord.Embed(
                title=f"{team_emoji} {team_name}",
                description=f"شعار فريق {team_name}",
                color=EMBED_COLOR
            )
            embed.set_image(url=logo_url)
            
            # إضافة الحقول
            for field in fields:
                embed.add_field(
                    name=field['name'],
                    value=field['value'],
                    inline=field.get('inline', True)
                )
                
            await interaction.channel.send(embed=embed)
    
    @app_commands.command(name="روستر", description="عرض قائمة الفرق وعدد الأعضاء لكل فريق")
    async def team_roster(self, interaction: discord.Interaction):
        # Get roster cap
        settings = db.get_guild_settings(interaction.guild.id)
        roster_cap = settings["roster_cap"]
        
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
            
            # Add team field
            embed.add_field(
                name=f"{team_emoji} {role_name}",
                value=f"👥 عدد الأعضاء: **{role_members_count}**/{roster_cap}",
                inline=True
            )
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        # Add footer with help text
        embed.set_footer(text="يمكنك استخدام أمر !روستر لعرض التفاصيل")
        
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
    
    @app_commands.command(name="اضافة_روم_تقديم", description="تحديد قناة طلبات الانضمام للفرق")
    @app_commands.describe(
        channel="قناة طلبات الانضمام"
    )
    async def set_application_channel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel
    ):
        # التحقق من صلاحيات الإدارة
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("يجب أن تكون مشرفاً في السيرفر لتعيين قناة التقديم.", ephemeral=True)
            return
            
        # تحديث الإعدادات في قاعدة البيانات
        db.update_guild_settings(
            interaction.guild.id,
            application_channel_id=channel.id
        )
        
        # إنشاء رسالة تأكيد
        embed = discord.Embed(
            title="✅ تم تحديد قناة طلبات الانضمام",
            description=f"تم تحديد {channel.mention} كقناة طلبات الانضمام للفرق.",
            color=SUCCESS_COLOR
        )
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="اضافة_روم_الانتقالات", description="تحديد قناة عروض التعاقدات مع اللاعبين")
    @app_commands.describe(
        channel="قناة عروض التعاقدات والانتقالات"
    )
    async def set_contract_channel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel
    ):
        # التحقق من صلاحيات الإدارة
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("يجب أن تكون مشرفاً في السيرفر لتعيين قناة التعاقدات.", ephemeral=True)
            return
            
        # تحديث الإعدادات في قاعدة البيانات
        db.update_guild_settings(
            interaction.guild.id,
            contract_channel_id=channel.id
        )
        
        # إنشاء رسالة تأكيد
        embed = discord.Embed(
            title="✅ تم تحديد قناة عروض التعاقدات",
            description=f"تم تحديد {channel.mention} كقناة عروض التعاقدات.",
            color=SUCCESS_COLOR
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
        app_commands.Choice(name="🥈 نائب كابتن", value="vice")
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
            
            # Update the captain_role_id in the database
            db.update_captain_role(interaction.guild.id, team["id"], role.id)
            
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
        # التحقق من أن المستخدم لديه صلاحية استخدام هذا الأمر
        if not is_captain_or_vice_captain(interaction, interaction.user.id) and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("هذا الأمر مقيد للمسؤولين وقادة الفرق فقط.", ephemeral=True)
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
        
        # Check using role members count instead of database entries
        team_role = interaction.guild.get_role(team["role_id"])
        if team_role:
            role_members_count = len(team_role.members)
            if role_members_count >= roster_cap:
                await interaction.response.send_message(
                    f"لقد وصلت إلى الحد الأقصى من اللاعبين ({role_members_count}/{roster_cap}).",
                    ephemeral=True
                )
                return
        else:
            # Fallback to database check if role not found
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
        
        # إرسال إشعار إلى قناة التعاقدات المخصصة
        try:
            # الحصول على قناة التعاقدات من الإعدادات
            settings = db.get_guild_settings(interaction.guild.id)
            contract_channel_id = settings.get("contract_channel_id")
            
            # إذا لم تكن قناة التعاقدات محددة، نستخدم القناة الافتراضية
            if contract_channel_id is None:
                contract_channel_id = 1345407172866998342
                
            notification_channel = self.bot.get_channel(contract_channel_id)
            if notification_channel:
                # إنشاء إمبد للنشر في قناة الإشعارات
                coach = interaction.user
                notification_embed = discord.Embed(
                    title=f"🔄 {team['name']} {team_emoji}",
                    description=f"The 🎖️ <@{team['captain_id'] or coach.id}> • {coach.display_name} have **signed** <@{player.id}>",
                    color=discord.Color.from_rgb(51, 102, 153)  # لون أزرق غامق
                )
                
                # إضافة معلومات الكابتن والروستر
                players = db.get_team_players(interaction.guild.id, team["id"])
                notification_embed.add_field(
                    name="Coach:",
                    value=f"CN <@{team['captain_id'] or coach.id}> 🔵 {coach.display_name}",
                    inline=False
                )
                notification_embed.add_field(
                    name="Roster:",
                    value=f"{len(players)}/22",
                    inline=False
                )
                
                # إضافة شعار الفريق كصورة مصغرة
                notification_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                
                await notification_channel.send(embed=notification_embed)
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار التعاقد للقناة المخصصة: {e}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="فسخ_تعاقد", description="إنهاء تعاقد لاعب من الفريق")
    @app_commands.describe(player="اللاعب الذي تريد إنهاء تعاقده")
    async def release_player(self, interaction: discord.Interaction, player: discord.Member):
        # التحقق من أن المستخدم لديه صلاحية استخدام هذا الأمر
        if not is_captain_or_vice_captain(interaction, interaction.user.id) and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("هذا الأمر مقيد للمسؤولين وقادة الفرق فقط.", ephemeral=True)
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
        
        # إرسال إشعار إلى قناة التعاقدات المخصصة
        try:
            # الحصول على قناة التعاقدات من الإعدادات
            settings = db.get_guild_settings(interaction.guild.id)
            contract_channel_id = settings.get("contract_channel_id")
            
            # إذا لم تكن قناة التعاقدات محددة، نستخدم القناة الافتراضية
            if contract_channel_id is None:
                contract_channel_id = 1345407172866998342
                
            notification_channel = self.bot.get_channel(contract_channel_id)
            if notification_channel:
                # إنشاء إمبد للنشر في قناة الإشعارات
                coach = interaction.user
                notification_embed = discord.Embed(
                    title=f"🔄 {team['name']} {team_emoji}",
                    description=f"The 🎖️ <@{team['captain_id'] or coach.id}> • {coach.display_name} have **released** <@{player.id}>",
                    color=discord.Color.from_rgb(153, 0, 0)  # لون أحمر غامق
                )
                
                # إضافة معلومات الكابتن والروستر
                players = db.get_team_players(interaction.guild.id, team["id"])
                notification_embed.add_field(
                    name="Coach:",
                    value=f"CN <@{team['captain_id'] or coach.id}> 🔵 {coach.display_name}",
                    inline=False
                )
                notification_embed.add_field(
                    name="Roster:",
                    value=f"{len(players)}/22",
                    inline=False
                )
                
                # إضافة شعار الفريق كصورة مصغرة
                notification_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                
                await notification_channel.send(embed=notification_embed)
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار فسخ التعاقد للقناة المخصصة: {e}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="عرض", description="تقديم عرض للتعاقد مع لاعب")
    @app_commands.describe(
        player="اللاعب الذي تريد التعاقد معه",
        amount="المبلغ المعروض (بلو باك)"
    )
    async def make_offer(self, interaction: discord.Interaction, player: discord.Member, amount: int):
        # التحقق من أن المستخدم لديه صلاحية استخدام هذا الأمر
        if not is_captain_or_vice_captain(interaction, interaction.user.id) and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("هذا الأمر مقيد للمسؤولين وقادة الفرق فقط.", ephemeral=True)
            return
        # التحقق من وجود قناة للتعاقدات
        settings = db.get_guild_settings(interaction.guild.id)
        if not settings.get("contract_channel_id"):
            await interaction.response.send_message("لم يتم تعيين قناة للتعاقدات. يرجى استخدام أمر /اضافة_روم_الانتقالات أولاً.", ephemeral=True)
            return
            
        # تحقق مما إذا كان المستخدم كابتن أو نائب كابتن
        is_authorized = is_captain_or_vice_captain(interaction, interaction.user.id)
        if not is_authorized:
            await interaction.response.send_message("هذا الأمر مقيد للكابتن أو نائب الكابتن فقط.", ephemeral=True)
            return
        
        # الحصول على معلومات الفريق (للكابتن أو المشرف)
        team = db.get_team_by_captain(interaction.guild.id, interaction.user.id)
        
        # إذا كان المستخدم نائب كابتن، نحتاج إلى الحصول على فريقه
        if not team and interaction.user.id != ADMIN_USER_ID:
            player_data = db.get_player(interaction.guild.id, interaction.user.id)
            if player_data and player_data["team_id"] is not None and player_data["position"] == "vc":
                team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
        
        # إذا كان المشرف يستخدم هذا الأمر ولم يتم تحديد الفريق
        if interaction.user.id == ADMIN_USER_ID and not team:
            await interaction.response.send_message(
                "أنت مسؤول، ولكن لم يتم تحديد الفريق. استخدم أمر /اضافة_رتب لتعيين نفسك ككابتن أولاً.",
                ephemeral=True
            )
            return
            
        # التحقق مما إذا كان اللاعب في فريق بالفعل
        player_data = db.get_player(interaction.guild.id, player.id)
        player_price = 0  # السعر الافتراضي للاعب الحر
        player_team_id = None
        player_team_name = "بدون فريق"
        team_captain_id = None
        
        # لا نسمح بتقديم عرض للاعب موجود في نفس الفريق
        if player_data and player_data["team_id"] is not None:
            if player_data["team_id"] == team["id"]:
                await interaction.response.send_message(
                    f"هذا اللاعب منضم بالفعل إلى فريقك.",
                    ephemeral=True
                )
                return
            else:
                # اللاعب في فريق آخر، نحتاج إلى معرفة تفاصيل الفريق والسعر
                player_team_id = player_data["team_id"]
                player_team = db.get_team(interaction.guild.id, team_id=player_team_id)
                
                if player_team:
                    player_team_name = player_team["name"]
                    team_captain_id = player_team["captain_id"]
                
                # نحتاج إلى التحقق من سعر اللاعب
                player_price = player_data["price"] if player_data["price"] > 0 else 0
        
        # التحقق من رصيد الكابتن
        captain_data = db.get_player(interaction.guild.id, interaction.user.id)
        captain_balance = captain_data["balance"] if captain_data else 0
        
        if captain_balance < amount and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message(
                f"ليس لديك رصيد كافٍ لتقديم هذا العرض. رصيدك: {captain_balance:,} بلو باك",
                ephemeral=True
            )
            return
        
        # إنشاء العرض
        offer_id = db.create_player_offer(
            interaction.guild.id, 
            player.id, 
            team["id"], 
            interaction.user.id, 
            amount
        )
        
        if not offer_id:
            await interaction.response.send_message("حدث خطأ أثناء إنشاء العرض. الرجاء المحاولة مرة أخرى.", ephemeral=True)
            return
        
        # إنشاء أزرار للموافقة أو الرفض
        class OfferView(discord.ui.View):
            def __init__(self, bot, offer_id):
                super().__init__(timeout=None)
                self.bot = bot
                self.offer_id = offer_id
            
            @discord.ui.button(label="قبول العرض", style=discord.ButtonStyle.green, custom_id=f"accept_offer_{offer_id}")
            async def accept_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                # تحقق من أن الشخص الذي ضغط على الزر هو اللاعب نفسه
                if button_interaction.user.id != player.id:
                    await button_interaction.response.send_message("فقط اللاعب المعني يمكنه قبول العرض.", ephemeral=True)
                    return
                
                # الحصول على معلومات العرض
                offer = db.get_offer_by_id(self.offer_id)
                if not offer:
                    await button_interaction.response.send_message("لم يتم العثور على العرض. ربما تم إلغاؤه.", ephemeral=True)
                    return
                
                # التحقق من رصيد الكابتن مرة أخرى
                from_captain = button_interaction.guild.get_member(offer["from_captain_id"])
                captain_data = db.get_player(button_interaction.guild.id, offer["from_captain_id"])
                captain_balance = captain_data["balance"] if captain_data else 0
                
                if captain_balance < offer["amount"] and offer["from_captain_id"] != ADMIN_USER_ID:
                    await button_interaction.response.send_message(
                        "لم يعد لدى الكابتن رصيد كافٍ لإتمام الصفقة.",
                        ephemeral=True
                    )
                    # تحديث حالة العرض إلى مرفوض
                    db.update_offer_status(self.offer_id, "rejected")
                    return
                
                # خصم المبلغ من الكابتن (إلا إذا كان المشرف)
                if offer["from_captain_id"] != ADMIN_USER_ID:
                    db.update_player_balance(button_interaction.guild.id, offer["from_captain_id"], -offer["amount"])
                
                # التحقق مما إذا كان اللاعب في فريق بالفعل
                player_data = db.get_player(button_interaction.guild.id, player.id)
                player_old_team_id = None
                player_old_team = None
                player_price = 0
                team_captain_id = None
                
                if player_data and player_data["team_id"] is not None:
                    player_old_team_id = player_data["team_id"]
                    player_old_team = db.get_team(button_interaction.guild.id, team_id=player_old_team_id)
                    
                    if player_old_team:
                        team_captain_id = player_old_team["captain_id"]
                    
                    # نحتاج إلى التحقق من سعر اللاعب
                    player_price = player_data["price"] if player_data["price"] > 0 else 0
                    
                    # إذا كان للاعب سعر محدد وكان في فريق آخر، يجب دفع قيمة العقد للفريق القديم
                    if player_price > 0 and team_captain_id:
                        db.update_player_balance(button_interaction.guild.id, team_captain_id, player_price)
                        
                        # إرسال إشعار لكابتن الفريق القديم
                        try:
                            old_captain = button_interaction.guild.get_member(team_captain_id)
                            if old_captain:
                                old_captain_embed = discord.Embed(
                                    title="💰 تم بيع لاعب",
                                    description=f"تم بيع اللاعب {player.mention} من فريقك مقابل **{player_price:,}** بلو باك",
                                    color=EMBED_COLOR
                                )
                                await old_captain.send(embed=old_captain_embed)
                        except Exception as e:
                            logger.error(f"خطأ في إرسال إشعار لكابتن الفريق السابق: {e}")
                    
                    # إزالة اللاعب من فريقه القديم
                    if player_old_team and player_old_team["role_id"]:
                        old_role = button_interaction.guild.get_role(player_old_team["role_id"])
                        if old_role and old_role in player.roles:
                            await player.remove_roles(old_role)
                
                # تقسيم المبلغ: جزء للاعب وجزء للفريق السابق إذا كان في فريق
                player_amount = offer["amount"] - player_price
                if player_amount > 0:
                    # إضافة المبلغ المتبقي للاعب
                    db.update_player_balance(button_interaction.guild.id, player.id, player_amount)
                
                # تحديث حالة العرض إلى مقبول
                db.update_offer_status(self.offer_id, "accepted")
                
                # الحصول على معلومات الفريق الجديد
                team = db.get_team(button_interaction.guild.id, team_id=offer["team_id"])
                
                # إضافة اللاعب إلى الفريق الجديد
                db.add_player_to_team(button_interaction.guild.id, player.id, team["id"], "player")
                
                # إضافة رتبة الفريق للاعب
                role = button_interaction.guild.get_role(team["role_id"])
                if role:
                    await player.add_roles(role)
                
                # إرسال رسالة للاعب لتأكيد قبول العرض
                try:
                    from_captain = button_interaction.guild.get_member(offer["from_captain_id"])
                    captain_name = from_captain.display_name if from_captain else "الكابتن"
                    team_emoji = team["emoji"] if team["emoji"] else "⚽"
                    
                    player_embed = discord.Embed(
                        title="✅ تم قبول عرض الانتقال",
                        description=f"تم الموافقة على انتقالك إلى فريق **{team['name']}** {team_emoji}",
                        color=SUCCESS_COLOR
                    )
                    
                    player_embed.add_field(
                        name="كابتن الفريق الجديد",
                        value=f"{from_captain.mention} • {captain_name}",
                        inline=False
                    )
                    
                    player_embed.add_field(
                        name="مبلغ الصفقة",
                        value=f"{offer['amount']:,} بلو باك",
                        inline=False
                    )
                    
                    player_embed.add_field(
                        name="💰 حصتك من الصفقة",
                        value=f"{offer['amount'] - player_price:,} بلو باك",
                        inline=False
                    )
                    
                    player_embed.set_footer(text="بالتوفيق في فريقك الجديد! 🌟")
                    
                    await player.send(embed=player_embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار قبول العرض للاعب: {e}")
                
                # إنشاء رسالة تأكيد
                team_emoji = team["emoji"] if team["emoji"] else "⚽"
                embed = discord.Embed(
                    title="✅ تم قبول العرض",
                    description=f"قبل {player.mention} عرض الانضمام إلى فريق **{team['name']}** {team_emoji}",
                    color=SUCCESS_COLOR
                )
                
                embed.add_field(name="💲 مبلغ الصفقة", value=f"{offer['amount']:,} بلو باك", inline=True)
                
                # إضافة معلومات عن توزيع المال
                if player_old_team and player_price > 0:
                    old_team_emoji = player_old_team["emoji"] if player_old_team["emoji"] else "⚽"
                    embed.add_field(
                        name="💰 توزيع المبلغ",
                        value=f"مبلغ للفريق السابق: **{player_price:,}** بلو باك\n" + 
                              f"مبلغ للاعب: **{offer['amount'] - player_price:,}** بلو باك",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="📊 تفاصيل الانتقال",
                        value=f"من: {old_team_emoji} **{player_old_team['name']}**\n" + 
                              f"إلى: {team_emoji} **{team['name']}**",
                        inline=False
                    )
                
                # إرسال إشعار
                settings = db.get_guild_settings(button_interaction.guild.id)
                if settings and settings["notification_channel_id"]:
                    try:
                        channel = self.bot.get_channel(settings["notification_channel_id"])
                        if channel:
                            await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"خطأ في إرسال إشعار: {e}")
                
                # إرسال إشعار إلى قناة التعاقدات المخصصة
                try:
                    # الحصول على قناة التعاقدات من الإعدادات
                    settings = db.get_guild_settings(button_interaction.guild.id)
                    contract_channel_id = settings.get("contract_channel_id")
                    
                    # إذا لم تكن قناة التعاقدات محددة، نستخدم القناة الافتراضية
                    if contract_channel_id is None:
                        contract_channel_id = 1345407172866998342
                    
                    notification_channel = self.bot.get_channel(contract_channel_id)
                    if notification_channel:
                        # إنشاء إمبد للنشر في قناة الإشعارات أو تأثير متحرك
                        from_captain = button_interaction.guild.get_member(offer["from_captain_id"])
                        
                        # محاولة إظهار الانتقال بشكل متحرك إذا كانت التأثيرات المتحركة متاحة
                        animation_success = False
                        try:
                            if self.animator:
                                # عرض الانتقال بتأثير متحرك
                                animation_success = await self.show_animated_transfer(
                                    channel=notification_channel,
                                    player=player,
                                    from_team=player_old_team,
                                    to_team=team,
                                    amount=offer['amount']
                                )
                        except Exception as anim_error:
                            logger.error(f"خطأ في عرض التأثير المتحرك للانتقال: {anim_error}")
                            animation_success = False
                            
                        # إذا فشل عرض التأثير المتحرك، نعرض إشعار عادي
                        if not animation_success:
                            notification_embed = discord.Embed(
                                title=f"🔄 {team['name']} {team_emoji}",
                                description=f"The 🎖️ <@{team['captain_id'] or offer['from_captain_id']}> • {from_captain.display_name} have **signed** <@{player.id}>",
                                color=discord.Color.from_rgb(51, 102, 153)  # لون أزرق غامق
                            )
                            
                            # إضافة معلومات الكابتن والروستر
                            players = db.get_team_players(button_interaction.guild.id, team["id"])
                            notification_embed.add_field(
                                name="Coach:",
                                value=f"CN <@{team['captain_id'] or offer['from_captain_id']}> 🔵 {from_captain.display_name}",
                                inline=False
                            )
                            notification_embed.add_field(
                                name="Transfer fee:",
                                value=f"{offer['amount']:,} Blue bucks",
                                inline=False
                            )
                            notification_embed.add_field(
                                name="Roster:",
                                value=f"{len(players)}/22",
                                inline=False
                            )
                            
                            # إضافة شعار الفريق كصورة مصغرة
                            notification_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                            
                            # إضافة شعار النادي (Blue Lock Rivals)
                            notification_embed.set_author(
                                name="Blue Lock Rivals - Transfer News",
                                icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                            )
                            notification_embed.set_footer(
                                text="Blue Lock Rivals Transfer System",
                                icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                            )
                            
                            await notification_channel.send(embed=notification_embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار قبول العرض للقناة المخصصة: {e}")
                
                # تعطيل الأزرار
                for child in self.children:
                    child.disabled = True
                
                await button_interaction.response.edit_message(embed=embed, view=self)
            
            @discord.ui.button(label="رفض العرض", style=discord.ButtonStyle.red, custom_id=f"reject_offer_{offer_id}")
            async def reject_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                # الحصول على معلومات العرض
                offer = db.get_offer_by_id(self.offer_id)
                if not offer:
                    await button_interaction.response.send_message("لم يتم العثور على العرض. ربما تم إلغاؤه بالفعل.", ephemeral=True)
                    return
                
                # تحقق من أن الشخص الذي ضغط على الزر هو اللاعب نفسه أو الكابتن الذي أرسل العرض
                if button_interaction.user.id != player.id and button_interaction.user.id != offer["from_captain_id"]:
                    await button_interaction.response.send_message("فقط اللاعب المعني أو الكابتن الذي أرسل العرض يمكنه رفض/إلغاء العرض.", ephemeral=True)
                    return
                
                # تحديث حالة العرض إلى مرفوض
                db.update_offer_status(self.offer_id, "rejected")
                
                # الحصول على معلومات الفريق
                team = db.get_team(button_interaction.guild.id, team_id=offer["team_id"])
                
                # إرسال رسالة للاعب لتأكيد رفض العرض (إذا كان الكابتن هو من رفض)
                if button_interaction.user.id == offer["from_captain_id"]:
                    try:
                        the_player = button_interaction.guild.get_member(player.id)
                        team_emoji = team["emoji"] if team["emoji"] else "⚽"
                        
                        player_embed = discord.Embed(
                            title="❌ تم إلغاء عرض الانتقال",
                            description=f"تم إلغاء عرض انتقالك إلى فريق **{team['name']}** {team_emoji} من قبل الكابتن",
                            color=discord.Color.red()
                        )
                        
                        from_captain = button_interaction.guild.get_member(offer["from_captain_id"])
                        captain_name = from_captain.display_name if from_captain else "الكابتن"
                        
                        player_embed.add_field(
                            name="كابتن الفريق",
                            value=f"{from_captain.mention} • {captain_name}",
                            inline=False
                        )
                        
                        player_embed.add_field(
                            name="مبلغ العرض",
                            value=f"{offer['amount']:,} بلو باك",
                            inline=False
                        )
                        
                        # إضافة شعار الفريق كصورة مصغرة
                        player_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                        
                        # إضافة شعار النادي (Blue Lock Rivals)
                        player_embed.set_author(
                            name="Blue Lock Rivals - Transfer Cancelled",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        player_embed.set_footer(
                            text="Blue Lock Rivals Transfer System",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        
                        await the_player.send(embed=player_embed)
                    except Exception as e:
                        logger.error(f"خطأ في إرسال إشعار إلغاء العرض للاعب: {e}")
                        
                # إنشاء رسالة تأكيد
                team_emoji = team["emoji"] if team["emoji"] else "⚽"
                
                # تحديد من الذي قام بالرفض
                action_taker = player
                action_verb = "رفض"
                
                # إذا كان الكابتن هو من رفض العرض
                if button_interaction.user.id == offer["from_captain_id"]:
                    action_taker = button_interaction.user
                    action_verb = "ألغى"
                
                embed = discord.Embed(
                    title="❌ تم " + ("إلغاء" if button_interaction.user.id == offer["from_captain_id"] else "رفض") + " العرض",
                    description=f"{action_verb} {action_taker.mention} عرض انضمام {player.mention} إلى فريق **{team['name']}** {team_emoji}",
                    color=discord.Color.red()
                )
                
                # إرسال إشعار إلى قناة التعاقدات المخصصة
                try:
                    # الحصول على قناة التعاقدات من الإعدادات
                    settings = db.get_guild_settings(button_interaction.guild.id)
                    contract_channel_id = settings.get("contract_channel_id")
                    
                    # إذا لم تكن قناة التعاقدات محددة، نستخدم القناة الافتراضية
                    if contract_channel_id is None:
                        contract_channel_id = 1345407172866998342
                    
                    notification_channel = self.bot.get_channel(contract_channel_id)
                    if notification_channel:
                        # إنشاء إمبد للنشر في قناة الإشعارات
                        from_captain = button_interaction.guild.get_member(offer["from_captain_id"])
                        action_text = "cancelled" if button_interaction.user.id == offer["from_captain_id"] else "rejected"
                        
                        notification_embed = discord.Embed(
                            title=f"🔄 {team['name']} {team_emoji}",
                            description=f"The offer to <@{player.id}> has been **{action_text}**",
                            color=discord.Color.from_rgb(153, 0, 0)  # لون أحمر غامق
                        )
                        
                        # إضافة معلومات إضافية
                        notification_embed.add_field(
                            name="Action by:",
                            value=f"{'Coach' if button_interaction.user.id == offer['from_captain_id'] else 'Player'} <@{button_interaction.user.id}> • {button_interaction.user.display_name}",
                            inline=False
                        )
                        
                        # إضافة شعار الفريق كصورة مصغرة
                        notification_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                        
                        # إضافة شعار النادي (Blue Lock Rivals)
                        notification_embed.set_author(
                            name="Blue Lock Rivals - Transfer News",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        notification_embed.set_footer(
                            text="Blue Lock Rivals Transfer System",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        
                        await notification_channel.send(embed=notification_embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار رفض العرض للقناة المخصصة: {e}")
                
                # تعطيل الأزرار
                for child in self.children:
                    child.disabled = True
                
                await button_interaction.response.edit_message(embed=embed, view=self)
        
        # إنشاء رسالة العرض
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        embed = discord.Embed(
            title="💰 عرض انضمام",
            description=f"{interaction.user.mention} يقدم عرضًا لـ {player.mention} للانضمام إلى فريق **{team['name']}** {team_emoji}",
            color=EMBED_COLOR
        )
        
        embed.add_field(name="💲 المبلغ المعروض", value=f"{amount:,} بلو باك", inline=True)
        
        # إضافة معلومات عن حالة اللاعب الحالية
        if player_team_id is not None:
            embed.add_field(
                name="⚠️ ملاحظة هامة",
                value=f"أنت حالياً في فريق **{player_team_name}**\n" + 
                      (f"سعر عقدك: **{player_price:,}** بلو باك\n" if player_price > 0 else "") +
                      f"سيحصل فريقك الحالي على **{player_price:,}** بلو باك من قيمة الصفقة",
                inline=False
            )
            
        # إضافة شعار الفريق كصورة مصغرة
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        # إضافة شعار النادي (Blue Lock Rivals)
        embed.set_author(
            name="Blue Lock Rivals - Transfer Offer",
            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
        )
        
        embed.set_footer(text="يرجى قبول أو رفض العرض باستخدام الأزرار أدناه • Blue Lock Rivals Transfer System")
        
        # إرسال العرض إلى اللاعب
        view = OfferView(self.bot, offer_id)
        try:
            await player.send(embed=embed, view=view)
            
            # إرسال تأكيد للكابتن
            confirmation_embed = discord.Embed(
                title="✅ تم إرسال العرض",
                description=f"تم إرسال عرضك إلى {player.mention} بنجاح",
                color=SUCCESS_COLOR
            )
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            
            # إرسال نسخة من العرض إلى قناة التعاقدات إذا كانت محددة
            settings = db.get_guild_settings(interaction.guild.id)
            contract_channel_id = settings.get("contract_channel_id")
            
            if contract_channel_id:
                try:
                    contract_channel = self.bot.get_channel(contract_channel_id)
                    if contract_channel:
                        team_emoji = team.get("emoji", "⚽")
                        offer_embed = discord.Embed(
                            title=f"💰 عرض تعاقد جديد من {team.get('name')} {team_emoji}",
                            description=f"تم تقديم عرض من {interaction.user.mention} إلى اللاعب {player.mention}",
                            color=EMBED_COLOR
                        )
                        offer_embed.add_field(name="قيمة العرض", value=f"{amount:,} بلو باك", inline=True)
                        
                        # إضافة شعار الفريق كصورة مصغرة
                        offer_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
                        
                        # إضافة شعار النادي (Blue Lock Rivals)
                        offer_embed.set_author(
                            name="Blue Lock Rivals - Transfer Offer",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        offer_embed.set_footer(
                            text="Blue Lock Rivals Transfer System",
                            icon_url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
                        )
                        
                        await contract_channel.send(embed=offer_embed)
                except Exception as e:
                    logger.error(f"خطأ في إرسال العرض إلى قناة التعاقدات: {e}")
        except discord.Forbidden:
            # في حالة تعذر إرسال رسالة مباشرة للاعب
            await interaction.response.send_message(
                f"تعذر إرسال العرض إلى {player.mention}. يجب أن تكون الرسائل المباشرة مفتوحة.",
                ephemeral=True
            )
            # إلغاء العرض
            db.update_offer_status(offer_id, "cancelled")

    @app_commands.command(name="عرض_اعدادات", description="عرض جميع إعدادات السيرفر الحالية")
    async def show_settings(self, interaction: discord.Interaction):
        # التحقق من صلاحيات الإدارة
        if not interaction.user.guild_permissions.administrator and interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("يجب أن تكون مشرفاً في السيرفر لعرض الإعدادات.", ephemeral=True)
            return
            
        # الحصول على الإعدادات من قاعدة البيانات
        settings = db.get_guild_settings(interaction.guild.id)
        
        # إنشاء رسالة إظهار الإعدادات
        embed = discord.Embed(
            title="⚙️ إعدادات السيرفر",
            description="الإعدادات الحالية للسيرفر",
            color=EMBED_COLOR
        )
        
        # إضافة الحد الأقصى لعدد اللاعبين في كل فريق
        embed.add_field(
            name="🧢 الحد الأقصى للاعبين في كل فريق:",
            value=f"{settings['roster_cap']} لاعبين",
            inline=False
        )
        
        # قناة الإشعارات العامة
        notification_channel = None
        if settings["notification_channel_id"]:
            notification_channel = interaction.guild.get_channel(settings["notification_channel_id"])
        
        embed.add_field(
            name="📢 قناة الإشعارات العامة:",
            value=notification_channel.mention if notification_channel else "غير محددة",
            inline=False
        )
        
        # قناة طلبات الانضمام
        application_channel = None
        if settings["application_channel_id"]:
            application_channel = interaction.guild.get_channel(settings["application_channel_id"])
        
        embed.add_field(
            name="📝 قناة طلبات الانضمام:",
            value=application_channel.mention if application_channel else "غير محددة",
            inline=False
        )
        
        # قناة إشعارات التعاقدات
        contract_channel = None
        if settings["contract_channel_id"]:
            contract_channel = interaction.guild.get_channel(settings["contract_channel_id"])
        
        embed.add_field(
            name="💼 قناة إشعارات التعاقدات:",
            value=contract_channel.mention if contract_channel else "غير محددة (سيتم استخدام القناة الافتراضية)",
            inline=False
        )
        
        # عرض معلومات الفرق ورتب الكابتن
        teams = db.get_all_teams(interaction.guild.id)
        if teams:
            teams_info = []
            for team in teams:
                captain_role = None
                team_role = None
                
                if team["captain_role_id"]:
                    captain_role = interaction.guild.get_role(team["captain_role_id"])
                
                if team["role_id"]:
                    team_role = interaction.guild.get_role(team["role_id"])
                
                captain_text = ""
                if team["captain_id"]:
                    captain = interaction.guild.get_member(team["captain_id"])
                    if captain:
                        captain_text = f" (الكابتن: {captain.display_name})"
                
                teams_info.append(f"{team['name']}{captain_text}")
                teams_info.append(f"  رتبة الفريق: {team_role.mention if team_role else 'غير محددة'}")
                teams_info.append(f"  رتبة الكابتن: {captain_role.mention if captain_role else 'غير محددة'}")
            
            if teams_info:
                embed.add_field(
                    name="🏆 الفرق ورتب الكابتن:",
                    value="\n".join(teams_info),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @commands.command(name="عرض_اعدادات_نص")
    async def show_settings_cmd(self, ctx):
        """عرض جميع إعدادات السيرفر الحالية"""
        # إنشاء تفاعل اصطناعي
        fake_interaction = type('FakeInteraction', (), {
            'guild': ctx.guild,
            'guild_id': ctx.guild.id,
            'user': ctx.author,
            'channel': ctx.channel
        })
        fake_interaction.user = ctx.author
        fake_interaction.response = type('FakeResponse', (), {})
        
        async def send_message(content=None, embed=None, view=None, ephemeral=False):
            if content:
                await ctx.send(content)
            elif embed:
                await ctx.send(embed=embed)
        
        fake_interaction.response.send_message = send_message
        
        # استدعاء الأمر الأصلي
        await self.show_settings(fake_interaction)
        
    # This method gets called after the cog is loaded and will be used
    # to initialize the animator from the animations cog
    def initialize_animator(self, animations_cog):
        if animations_cog:
            self.animator = animations_cog.logo_animator
            return True
        return False

    # Helper method to display animated player transfer
    async def show_animated_transfer(self, channel, player, from_team, to_team, amount=0):
        """عرض انتقال اللاعب بين الفرق بشكل متحرك"""
        if not self.animator:
            return False
        
        # الحصول على صورة اللاعب
        player_avatar = player.display_avatar.url
        
        # الحصول على شعارات الفرق (استخدام شعار افتراضي إذا كان غير متوفر)
        team_logo = "https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
        
        await self.animator.animate_player_transfer(
            channel=channel,
            player_name=player.display_name,
            player_avatar=player_avatar,
            from_team=from_team["name"] if from_team else "بدون فريق",
            to_team=to_team["name"],
            from_logo=team_logo,
            to_logo=team_logo,
            transfer_fee=amount
        )
        return True

async def setup(bot):
    await bot.add_cog(Teams(bot))
