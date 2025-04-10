import os
import discord
from discord import app_commands
from discord.ext import commands
import database as db
from config import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, ADMIN_USER_ID
from utils.helpers import is_admin_or_captain, is_captain_or_vice_captain

"""
سكربت عرض - Blue Lock Rivals Bot
يحتوي على أوامر عرض معلومات الفرق واللاعبين بتصميم أنيق
"""

class Display(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="عرض_تفاصيل", description="عرض تفاصيل الفرق واللاعبين بشكل جميل")
    @app_commands.describe(
        team="اسم الفريق المراد عرض تفاصيله",
        player="اللاعب المراد عرض إحصائياته"
    )
    async def display_command(
        self, 
        interaction: discord.Interaction, 
        team: str = None,
        player: discord.Member = None
    ):
        # إذا تم تحديد لاعب، نعرض إحصائياته
        if player:
            await self.display_player_stats(interaction, player)
            return
            
        # إذا تم تحديد فريق، نعرض تفاصيله
        if team:
            await self.display_team_details(interaction, team)
            return
            
        # إذا لم يتم تحديد أي خيار، نعرض قائمة الفرق
        await self.display_teams_list(interaction)
    
    async def display_player_stats(self, interaction: discord.Interaction, player: discord.Member):
        """عرض إحصائيات اللاعب بشكل جميل"""
        # الحصول على معلومات اللاعب من قاعدة البيانات
        player_data = db.get_player(interaction.guild.id, player.id)
        
        if not player_data:
            await interaction.response.send_message(f"لا توجد إحصائيات مسجلة للاعب {player.mention}", ephemeral=True)
            return
            
        # الحصول على معلومات الفريق إذا كان اللاعب منضمًا لفريق
        team_name = "لا يوجد"
        team_emoji = "⚽"
        team_logo = None
        
        if player_data["team_id"]:
            team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else "⚽"
                team_logo = team.get("logo_url")
        
        # إنشاء رسالة مخصصة للاعب
        embed = discord.Embed(
            title=f"{team_emoji} إحصائيات اللاعب | {player.display_name}",
            description=f"عرض الإحصائيات الكاملة للاعب {player.mention}",
            color=EMBED_COLOR
        )
        
        # إضافة صورة اللاعب
        embed.set_thumbnail(url=player.display_avatar.url)
        
        # إضافة معلومات الفريق
        embed.add_field(
            name="🎖️ الفريق",
            value=team_name,
            inline=True
        )
        
        # إضافة سعر اللاعب
        player_price = player_data.get("price", 0)
        embed.add_field(
            name="💰 سعر اللاعب",
            value=f"{player_price:,} عملة" if player_price else "غير محدد",
            inline=True
        )
        
        # إضافة رصيد اللاعب
        player_balance = player_data.get("balance", 0)
        embed.add_field(
            name="💵 الرصيد",
            value=f"{player_balance:,} عملة",
            inline=True
        )
        
        # إضافة الإحصائيات
        goals = player_data.get("goals", 0)
        assists = player_data.get("assists", 0)
        saves = player_data.get("saves", 0)
        
        stats_value = f"⚽ **الأهداف**: {goals}\n"
        stats_value += f"👟 **التمريرات الحاسمة**: {assists}\n"
        stats_value += f"🧤 **التصديات**: {saves}\n"
        stats_value += f"📊 **المجموع**: {goals + assists + saves}"
        
        embed.add_field(
            name="📈 الإحصائيات",
            value=stats_value,
            inline=False
        )
        
        # إضافة شعار الفريق إذا كان متوفرًا
        if team_logo:
            embed.set_image(url=team_logo)
            
        # إضافة فوتر
        embed.set_footer(text=f"Blue Lock Rivals | معرف اللاعب: {player.id}")
        
        await interaction.response.send_message(embed=embed)
    
    async def display_team_details(self, interaction: discord.Interaction, team_name: str):
        """عرض تفاصيل الفريق بشكل جميل"""
        # الحصول على معلومات الفريق من قاعدة البيانات
        team = db.get_team(interaction.guild.id, team_name=team_name)
        
        if not team:
            await interaction.response.send_message(f"لم يتم العثور على فريق باسم **{team_name}**", ephemeral=True)
            return
            
        # الحصول على معلومات الفريق
        team_emoji = team["emoji"] if team["emoji"] else "⚽"
        team_logo = team.get("logo_url")
        
        # الحصول على معلومات الكابتن
        captain_info = "غير معين"
        if team["captain_id"]:
            captain = interaction.guild.get_member(team["captain_id"])
            if captain:
                captain_info = f"{captain.mention} • {captain.display_name}"
        
        # الحصول على قائمة اللاعبين
        players = db.get_team_players(interaction.guild.id, team["id"])
        
        # إنشاء رسالة مخصصة للفريق
        embed = discord.Embed(
            title=f"{team_emoji} فريق {team_name}",
            description=f"عرض تفاصيل ولاعبي فريق **{team_name}**",
            color=EMBED_COLOR
        )
        
        # إضافة معلومات الكابتن
        embed.add_field(
            name="👑 الكابتن",
            value=captain_info,
            inline=False
        )
        
        # الحصول على رتبة الفريق
        role = None
        if team["role_id"]:
            role = interaction.guild.get_role(team["role_id"])
            if role:
                embed.add_field(
                    name="🎖️ رتبة الفريق",
                    value=role.mention,
                    inline=True
                )
        
        # إضافة عدد اللاعبين
        embed.add_field(
            name="👥 عدد اللاعبين",
            value=f"{len(players)} لاعب",
            inline=True
        )
        
        # معالجة قائمة اللاعبين
        if players:
            players_text = ""
            
            # تجميع اللاعبين حسب المراكز
            captains = []
            vice_captains = []
            regulars = []
            
            for player_data in players:
                member = interaction.guild.get_member(player_data["user_id"])
                if not member:
                    continue
                    
                stats = f"⚽{player_data.get('goals', 0)} 👟{player_data.get('assists', 0)} 🧤{player_data.get('saves', 0)}"
                player_entry = f"{member.mention} • {stats}\n"
                
                if player_data["position"] == "cap":
                    captains.append(player_entry)
                elif player_data["position"] == "vc":
                    vice_captains.append(player_entry)
                else:
                    regulars.append(player_entry)
            
            # إضافة الكابتن ونائب الكابتن أولاً
            if captains:
                players_text += "**👑 الكابتن:**\n" + "".join(captains) + "\n"
            
            if vice_captains:
                players_text += "**🥈 نائب الكابتن:**\n" + "".join(vice_captains) + "\n"
            
            if regulars:
                players_text += "**👤 اللاعبون:**\n" + "".join(regulars)
                
            # التأكد من أن النص ليس طويلاً جدًا
            if len(players_text) > 1024:
                players_text = players_text[:1021] + "..."
                
            embed.add_field(
                name="📋 قائمة اللاعبين",
                value=players_text or "لا يوجد لاعبين مسجلين",
                inline=False
            )
        else:
            embed.add_field(
                name="📋 قائمة اللاعبين",
                value="لا يوجد لاعبين مسجلين حاليًا",
                inline=False
            )
        
        # إضافة شعار الفريق إذا كان متوفرًا
        if team_logo:
            embed.set_image(url=team_logo)
        
        # إضافة فوتر
        embed.set_footer(text=f"Blue Lock Rivals | معرف الفريق: {team['id']}")
        
        await interaction.response.send_message(embed=embed)
    
    async def display_teams_list(self, interaction: discord.Interaction):
        """عرض قائمة جميع الفرق بشكل جميل"""
        # الحصول على جميع الفرق
        teams = db.get_all_teams(interaction.guild.id)
        
        if not teams:
            await interaction.response.send_message("لا توجد فرق مسجلة في هذا السيرفر.", ephemeral=True)
            return
            
        # الحصول على إعدادات السيرفر
        settings = db.get_guild_settings(interaction.guild.id)
        roster_cap = settings["roster_cap"]
        
        # إنشاء رسالة مخصصة لقائمة الفرق
        embed = discord.Embed(
            title="🏆 قائمة الفرق",
            description=f"عرض جميع الفرق المسجلة في {interaction.guild.name}",
            color=EMBED_COLOR
        )
        
        # إضافة معلومات كل فريق
        for team in teams:
            # الحصول على رتبة الفريق
            role = interaction.guild.get_role(team["role_id"]) if team["role_id"] else None
            role_name = role.name if role else team["name"]
            
            # الحصول على عدد اللاعبين
            players = db.get_team_players(interaction.guild.id, team["id"])
            
            # الحصول على معلومات الكابتن
            captain_name = "غير معين"
            if team["captain_id"]:
                captain = interaction.guild.get_member(team["captain_id"])
                if captain:
                    captain_name = captain.display_name
            
            # الحصول على رمز الفريق
            team_emoji = team["emoji"] if team["emoji"] else "⚽"
            
            # إنشاء نص معلومات الفريق
            team_value = f"👑 الكابتن: {captain_name}\n"
            team_value += f"👥 اللاعبين: {len(players)}/{roster_cap}"
            
            embed.add_field(
                name=f"{team_emoji} {team['name']}",
                value=team_value,
                inline=True
            )
        
        # إضافة صورة عامة
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        # إضافة فوتر بمعلومات
        embed.set_footer(text="استخدم /عرض_تفاصيل مع اسم الفريق أو اسم اللاعب لعرض المزيد من التفاصيل")
        
        await interaction.response.send_message(embed=embed)
        
    @commands.command(name="عرض_تفاصيل")
    async def display_cmd(self, ctx, *, query=None):
        """عرض تفاصيل الفرق واللاعبين (الأمر النصي)"""
        # إنشاء تفاعل مزيف
        class FakeInteraction:
            response = None
            user = None
            guild = ctx.guild
            channel = ctx.channel
            
        class FakeResponse:
            async def send_message(self, content=None, embed=None, view=None, ephemeral=False):
                return await ctx.send(content=content, embed=embed, view=view)
                
        # تهيئة التفاعل المزيف
        interaction = FakeInteraction()
        interaction.user = ctx.author
        interaction.response = FakeResponse()
        
        # التحقق من وجود إشارة إلى لاعب
        if ctx.message.mentions and len(ctx.message.mentions) > 0:
            await self.display_player_stats(interaction, ctx.message.mentions[0])
            return
            
        # التحقق من وجود استعلام عن الفريق
        if query:
            await self.display_team_details(interaction, query)
            return
            
        # عرض قائمة الفرق إذا لم يتم تحديد شيء
        await self.display_teams_list(interaction)
            
async def setup(bot):
    await bot.add_cog(Display(bot))