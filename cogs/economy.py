import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta

import database as db
from config import CURRENCY_NAME, DAILY_REWARD, DAILY_COOLDOWN, EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR, ADMIN_USER_ID

logger = logging.getLogger("blue_lock_bot")

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # Add regular text commands (not slash commands)
    @commands.command(name="يومي")
    async def daily_cmd(self, ctx):
        """الحصول على مكافأة يومية"""
        # Check if user has already claimed today
        last_claim = db.get_last_daily_claim(ctx.guild.id, ctx.author.id)
        
        if last_claim:
            # Parse the datetime string
            last_claim_time = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
            next_claim_time = last_claim_time + timedelta(seconds=DAILY_COOLDOWN)
            
            # Check if cooldown is active
            if datetime.utcnow() < next_claim_time:
                time_remaining = next_claim_time - datetime.utcnow()
                hours, remainder = divmod(time_remaining.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏳ انتظر قليلاً",
                    description=f"لقد حصلت على مكافأتك اليومية بالفعل. يمكنك الحصول على المكافأة مرة أخرى بعد {hours} ساعة و {minutes} دقيقة.",
                    color=ERROR_COLOR
                )
                
                await ctx.send(embed=embed)
                return
        
        # Update balance
        db.update_player_balance(ctx.guild.id, ctx.author.id, DAILY_REWARD)
        
        # Update claim time
        db.update_daily_reward(ctx.guild.id, ctx.author.id)
        
        # Get player balance
        player = db.get_player(ctx.guild.id, ctx.author.id)
        current_balance = player["balance"] if player else DAILY_REWARD
        
        # Create embed response
        embed = discord.Embed(
            title="💰 مكافأة يومية",
            description=f"تم إضافة {DAILY_REWARD:,} {CURRENCY_NAME} إلى رصيدك!",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="رصيدك الحالي",
            value=f"{current_balance:,} {CURRENCY_NAME}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="رصيدي")
    async def balance_cmd(self, ctx):
        """عرض رصيدك من العملات"""
        # Get player balance
        player = db.get_player(ctx.guild.id, ctx.author.id)
        
        if not player:
            # Create player with 0 balance
            db.update_player_balance(ctx.guild.id, ctx.author.id, 0)
            current_balance = 0
        else:
            current_balance = player["balance"]
        
        # Create embed response
        embed = discord.Embed(
            title="💰 رصيدك",
            description=f"رصيدك الحالي: **{current_balance:,}** {CURRENCY_NAME}",
            color=EMBED_COLOR
        )
        
        # Get player team if exists
        team_name = "لا يوجد"
        team_emoji = ""
        
        if player and player["team_id"]:
            team = db.get_team(ctx.guild.id, team_id=player["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else ""
        
        embed.add_field(
            name="الفريق",
            value=f"{team_emoji} {team_name}",
            inline=True
        )
        
        # Add position if in a team
        if player and player["position"] and player["team_id"]:
            position_names = {
                "cf": "⚔️ مهاجم (CF)",
                "rw": "🏹 جناح أيمن (RW)",
                "lw": "🏹 جناح أيسر (LW)",
                "cm": "🛡️ لاعب وسط (CM)",
                "gk": "🧤 حارس مرمى (GK)",
                "cap": "🎖️ كابتن"
            }
            
            position = position_names.get(player["position"], "غير معروف")
            embed.add_field(name="المركز", value=position, inline=True)
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="ليدر_بورد")
    async def leaderboard_cmd(self, ctx):
        """عرض أفضل 10 لاعبين"""
        # Get top players
        top_players = db.get_top_players(ctx.guild.id, 10)
        
        if not top_players:
            await ctx.send("لا يوجد لاعبين مسجلين بعد.")
            return
        
        # Create embed response
        embed = discord.Embed(
            title="🏆 قائمة أفضل اللاعبين",
            description="أفضل 10 لاعبين حسب مجموع الأهداف والتمريرات الحاسمة والتصديات",
            color=EMBED_COLOR
        )
        
        for i, player_data in enumerate(top_players):
            player = ctx.guild.get_member(player_data["user_id"])
            if not player:
                continue
            
            # Calculate total score
            total_score = player_data["goals"] + player_data["assists"] + player_data["saves"]
            
            # Get player team if exists
            team_text = "بدون فريق"
            if player_data["team_name"]:
                team_emoji = player_data["team_emoji"] if player_data["team_emoji"] else ""
                team_text = f"{team_emoji} {player_data['team_name']}"
            
            # Format player stats based on position
            stats_text = f"⚽ {player_data['goals']} | 👟 {player_data['assists']}"
            if player_data["position"] == "gk":
                stats_text = f"🧤 {player_data['saves']}"
            
            # Add player field
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            embed.add_field(
                name=f"{medal} {player.display_name}",
                value=f"الفريق: {team_text}\n{stats_text}\nالنقاط: {total_score}",
                inline=False
            )
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="يومي", description=f"الحصول على مكافأة يومية من {CURRENCY_NAME}")
    async def daily(self, interaction: discord.Interaction):
        # Check if user has already claimed today
        last_claim = db.get_last_daily_claim(interaction.guild.id, interaction.user.id)
        
        if last_claim:
            # Parse the datetime string
            last_claim_time = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
            next_claim_time = last_claim_time + timedelta(seconds=DAILY_COOLDOWN)
            
            # Check if cooldown is active
            if datetime.utcnow() < next_claim_time:
                time_remaining = next_claim_time - datetime.utcnow()
                hours, remainder = divmod(time_remaining.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏳ انتظر قليلاً",
                    description=f"لقد حصلت على مكافأتك اليومية بالفعل. يمكنك الحصول على المكافأة مرة أخرى بعد {hours} ساعة و {minutes} دقيقة.",
                    color=ERROR_COLOR
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Update balance
        db.update_player_balance(interaction.guild.id, interaction.user.id, DAILY_REWARD)
        
        # Update claim time
        db.update_daily_reward(interaction.guild.id, interaction.user.id)
        
        # Get player balance
        player = db.get_player(interaction.guild.id, interaction.user.id)
        current_balance = player["balance"] if player else DAILY_REWARD
        
        # Create embed response
        embed = discord.Embed(
            title="💰 مكافأة يومية",
            description=f"تم إضافة {DAILY_REWARD:,} {CURRENCY_NAME} إلى رصيدك!",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="رصيدك الحالي",
            value=f"{current_balance:,} {CURRENCY_NAME}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="رصيدي", description=f"عرض رصيدك من {CURRENCY_NAME}")
    async def balance(self, interaction: discord.Interaction):
        # Get player balance
        player = db.get_player(interaction.guild.id, interaction.user.id)
        
        if not player:
            # Create player with 0 balance
            db.update_player_balance(interaction.guild.id, interaction.user.id, 0)
            current_balance = 0
        else:
            current_balance = player["balance"]
        
        # Create embed response
        embed = discord.Embed(
            title="💰 رصيدك",
            description=f"رصيدك الحالي: **{current_balance:,}** {CURRENCY_NAME}",
            color=EMBED_COLOR
        )
        
        # Get player team if exists
        team_name = "لا يوجد"
        team_emoji = ""
        
        if player and player["team_id"]:
            team = db.get_team(interaction.guild.id, team_id=player["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else ""
        
        embed.add_field(
            name="الفريق",
            value=f"{team_emoji} {team_name}",
            inline=True
        )
        
        # Add position if in a team
        if player and player["position"] and player["team_id"]:
            position_names = {
                "cf": "⚔️ مهاجم (CF)",
                "rw": "🏹 جناح أيمن (RW)",
                "lw": "🏹 جناح أيسر (LW)",
                "cm": "🛡️ لاعب وسط (CM)",
                "gk": "🧤 حارس مرمى (GK)",
                "cap": "🎖️ كابتن"
            }
            
            position = position_names.get(player["position"], "غير معروف")
            embed.add_field(name="المركز", value=position, inline=True)
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="اضافة_عملات", description=f"إضافة عملات {CURRENCY_NAME} لمستخدم")
    @app_commands.describe(
        user="المستخدم الذي تريد إضافة العملات له",
        amount="المبلغ الذي تريد إضافته"
    )
    async def add_currency(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        # Check if user is admin
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("ليس لديك صلاحيات لاستخدام هذا الأمر.", ephemeral=True)
            return
        
        # Check amount
        if amount <= 0:
            await interaction.response.send_message("يجب أن يكون المبلغ أكبر من صفر.", ephemeral=True)
            return
        
        # Add currency to player
        db.update_player_balance(interaction.guild.id, user.id, amount)
        
        # Get updated balance
        player = db.get_player(interaction.guild.id, user.id)
        current_balance = player["balance"] if player else amount
        
        # Create embed response
        embed = discord.Embed(
            title="💰 إضافة عملات",
            description=f"تم إضافة {amount:,} {CURRENCY_NAME} إلى رصيد {user.mention}",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="الرصيد الحالي",
            value=f"{current_balance:,} {CURRENCY_NAME}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ليدر_بورد", description="عرض أفضل 10 لاعبين")
    async def leaderboard(self, interaction: discord.Interaction):
        # Get top players
        top_players = db.get_top_players(interaction.guild.id, 10)
        
        if not top_players:
            await interaction.response.send_message("لا يوجد لاعبين مسجلين بعد.", ephemeral=True)
            return
        
        # Create embed response
        embed = discord.Embed(
            title="🏆 قائمة أفضل اللاعبين",
            description="أفضل 10 لاعبين حسب مجموع الأهداف والتمريرات الحاسمة والتصديات",
            color=EMBED_COLOR
        )
        
        for i, player_data in enumerate(top_players):
            player = interaction.guild.get_member(player_data["user_id"])
            if not player:
                continue
            
            # Calculate total score
            total_score = player_data["goals"] + player_data["assists"] + player_data["saves"]
            
            # Get player team if exists
            team_text = "بدون فريق"
            if player_data["team_name"]:
                team_emoji = player_data["team_emoji"] if player_data["team_emoji"] else ""
                team_text = f"{team_emoji} {player_data['team_name']}"
            
            # Format player stats based on position
            stats_text = f"⚽ {player_data['goals']} | 👟 {player_data['assists']}"
            if player_data["position"] == "gk":
                stats_text = f"🧤 {player_data['saves']}"
            
            # Add player field
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            embed.add_field(
                name=f"{medal} {player.display_name}",
                value=f"الفريق: {team_text}\n{stats_text}\nالنقاط: {total_score}",
                inline=False
            )
        
        # Add thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="سعر_اللاعب", description="عرض سعر لاعب معين")
    @app_commands.describe(player="اللاعب الذي تريد معرفة سعره")
    async def player_price(self, interaction: discord.Interaction, player: discord.Member = None):
        target_player = player or interaction.user
        
        # Get player data
        player_data = db.get_player(interaction.guild.id, target_player.id)
        
        if not player_data:
            await interaction.response.send_message(
                f"لا توجد معلومات مسجلة عن {target_player.mention}.",
                ephemeral=True
            )
            return
            
        # Get player price
        player_price = player_data.get("price", 0) or 0
        
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
            title="💲 سعر اللاعب",
            description=f"معلومات سعر {target_player.mention}",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="السعر الحالي",
            value=f"{player_price:,} بلو باك" if player_price > 0 else "غير محدد (مجاني)",
            inline=False
        )
        
        embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=True)
        
        # Add position if in a team
        if player_data["position"] and player_data["team_id"]:
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
        
        # Add stats
        embed.add_field(
            name="الإحصائيات",
            value=f"⚽ الأهداف: {player_data['goals']}\n👟 التمريرات: {player_data['assists']}\n🧤 التصديات: {player_data['saves']}",
            inline=False
        )
        
        # Set player avatar as thumbnail
        embed.set_thumbnail(url=target_player.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    @commands.command(name="سعر")
    async def player_price_cmd(self, ctx, member: discord.Member = None):
        """عرض سعر لاعب معين"""
        target_player = member or ctx.author
        
        # Get player data
        player_data = db.get_player(ctx.guild.id, target_player.id)
        
        if not player_data:
            await ctx.send(f"لا توجد معلومات مسجلة عن {target_player.mention}.")
            return
            
        # Get player price
        player_price = player_data.get("price", 0) or 0
        
        # Get player team if exists
        team_name = "بدون فريق"
        team_emoji = ""
        
        if player_data["team_id"]:
            team = db.get_team(ctx.guild.id, team_id=player_data["team_id"])
            if team:
                team_name = team["name"]
                team_emoji = team["emoji"] if team["emoji"] else ""
        
        # Create embed response
        embed = discord.Embed(
            title="💲 سعر اللاعب",
            description=f"معلومات سعر {target_player.mention}",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="السعر الحالي",
            value=f"{player_price:,} بلو باك" if player_price > 0 else "غير محدد (مجاني)",
            inline=False
        )
        
        embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=True)
        
        # Add position if in a team
        if player_data["position"] and player_data["team_id"]:
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
        
        # Add stats
        embed.add_field(
            name="الإحصائيات",
            value=f"⚽ الأهداف: {player_data['goals']}\n👟 التمريرات: {player_data['assists']}\n🧤 التصديات: {player_data['saves']}",
            inline=False
        )
        
        # Set player avatar as thumbnail
        embed.set_thumbnail(url=target_player.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
