import discord
from discord import app_commands
from discord.ext import commands
import logging
import typing

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

    @app_commands.command(name="اضافة_كوينز", description="إضافة عملات لمستخدم")
    @app_commands.describe(
        user="المستخدم الذي تريد إضافة العملات له",
        amount="المبلغ الذي تريد إضافته"
    )
    async def add_coins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        # Check if user is the admin
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
            description=f"تم إضافة {amount:,} بلو باك إلى رصيد {user.mention}",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="الرصيد الحالي",
            value=f"{current_balance:,} بلو باك",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="اضافة_اسعار", description="تحديد سعر لاعب للتعاقدات")
    @app_commands.describe(
        player="اللاعب الذي تريد تحديد سعره",
        price="السعر بعملات بلو باك"
    )
    async def set_player_price_old(self, interaction: discord.Interaction, player: discord.Member, price: int):
        """نسخة احتياطية من أمر تحديد سعر اللاعب"""
        await self.set_player_price(interaction, player, price)
    
    @app_commands.command(name="تحديد_سعر", description="تحديد سعر لاعب للتعاقدات")
    @app_commands.describe(
        player="اللاعب الذي تريد تحديد سعره",
        price="السعر بعملات بلو باك"
    )
    async def set_player_price(self, interaction: discord.Interaction, player: discord.Member, price: int):
        try:
            # سجل محاولة استخدام الأمر
            logger.info(f"تم محاولة استخدام أمر تحديد_سعر بواسطة {interaction.user} (ID: {interaction.user.id})")
            
            # Check if user is the admin
            if interaction.user.id != ADMIN_USER_ID:
                logger.warning(f"محاولة غير مصرح بها لاستخدام أمر تحديد_سعر من قبل {interaction.user} (ID: {interaction.user.id})")
                await interaction.response.send_message("ليس لديك صلاحيات لاستخدام هذا الأمر.", ephemeral=True)
                return
            
            # Check price
            if price < 0:
                logger.warning(f"سعر غير صالح ({price}) تم إدخاله بواسطة {interaction.user}")
                await interaction.response.send_message("يجب أن يكون السعر أكبر من أو يساوي صفر.", ephemeral=True)
                return
            
            # Update player price
            logger.info(f"تعديل سعر اللاعب {player} (ID: {player.id}) إلى {price} بلو باك")
            db.update_player_price(interaction.guild.id, player.id, price)
            
            # Get player data
            player_data = db.get_player(interaction.guild.id, player.id)
            
            # Get player team if exists
            team_name = "بدون فريق"
            team_emoji = ""
            
            if player_data and player_data["team_id"]:
                team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
                if team:
                    team_name = team["name"]
                    team_emoji = team["emoji"] if team["emoji"] else ""
            
            # Create embed response
            embed = discord.Embed(
                title="💲 تحديد سعر لاعب",
                description=f"تم تحديد سعر {player.mention} بنجاح",
                color=SUCCESS_COLOR
            )
            
            embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=False)
            embed.add_field(name="السعر الجديد", value=f"{price:,} بلو باك", inline=True)
            
            if player_data:
                # Add position if in a team
                if player_data["position"]:
                    position_names = {
                        "cf": "⚔️ مهاجم (CF)",
                        "rw": "🏹 جناح أيمن (RW)",
                        "lw": "🏹 جناح أيسر (LW)",
                        "cm": "🛡️ لاعب وسط (CM)",
                        "gk": "🧤 حارس مرمى (GK)",
                        "cap": "🎖️ كابتن",
                        "vc": "🥈 نائب كابتن",
                        "player": "🎽 لاعب"
                    }
                    
                    position = position_names.get(player_data["position"], "غير معروف")
                    embed.add_field(name="المركز", value=position, inline=True)
            
            logger.info(f"تم تحديد سعر اللاعب {player} بنجاح إلى {price} بلو باك")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"حدث خطأ أثناء استخدام أمر تحديد_سعر: {e}")
            await interaction.response.send_message(f"حدث خطأ أثناء تنفيذ الأمر: {e}", ephemeral=True)
    
    @commands.command(name="اضافة_كوينز")
    async def add_coins_cmd(self, ctx, user: discord.Member, amount: int):
        """إضافة عملات لمستخدم"""
        # Check if user is the admin
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("ليس لديك صلاحيات لاستخدام هذا الأمر.")
            return
        
        # Check amount
        if amount <= 0:
            await ctx.send("يجب أن يكون المبلغ أكبر من صفر.")
            return
        
        # Add currency to player
        db.update_player_balance(ctx.guild.id, user.id, amount)
        
        # Get updated balance
        player = db.get_player(ctx.guild.id, user.id)
        current_balance = player["balance"] if player else amount
        
        # Create embed response
        embed = discord.Embed(
            title="💰 إضافة عملات",
            description=f"تم إضافة {amount:,} بلو باك إلى رصيد {user.mention}",
            color=SUCCESS_COLOR
        )
        
        embed.add_field(
            name="الرصيد الحالي",
            value=f"{current_balance:,} بلو باك",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="اضافة_اسعار")
    async def set_player_price_cmd(self, ctx, user: discord.Member, price: int):
        """تحديد سعر لاعب للتعاقدات"""
        try:
            # سجل محاولة استخدام الأمر
            logger.info(f"تم محاولة استخدام أمر اضافة_اسعار (النصي) بواسطة {ctx.author} (ID: {ctx.author.id})")
            
            # Check if user is the admin
            if ctx.author.id != ADMIN_USER_ID:
                logger.warning(f"محاولة غير مصرح بها لاستخدام أمر اضافة_اسعار من قبل {ctx.author} (ID: {ctx.author.id})")
                await ctx.send("ليس لديك صلاحيات لاستخدام هذا الأمر.")
                return
            
            # Check price
            if price < 0:
                logger.warning(f"سعر غير صالح ({price}) تم إدخاله بواسطة {ctx.author}")
                await ctx.send("يجب أن يكون السعر أكبر من أو يساوي صفر.")
                return
            
            # Update player price
            logger.info(f"تعديل سعر اللاعب {user} (ID: {user.id}) إلى {price} بلو باك")
            db.update_player_price(ctx.guild.id, user.id, price)
            
            # Get player data
            player_data = db.get_player(ctx.guild.id, user.id)
            
            # Get player team if exists
            team_name = "بدون فريق"
            team_emoji = ""
            
            if player_data and player_data["team_id"]:
                team = db.get_team(ctx.guild.id, team_id=player_data["team_id"])
                if team:
                    team_name = team["name"]
                    team_emoji = team["emoji"] if team["emoji"] else ""
            
            # Create embed response
            embed = discord.Embed(
                title="💲 تحديد سعر لاعب",
                description=f"تم تحديد سعر {user.mention} بنجاح",
                color=SUCCESS_COLOR
            )
            
            embed.add_field(name="الفريق", value=f"{team_emoji} {team_name}", inline=False)
            embed.add_field(name="السعر الجديد", value=f"{price:,} بلو باك", inline=True)
            
            if player_data:
                # Add position if in a team
                if player_data["position"]:
                    position_names = {
                        "cf": "⚔️ مهاجم (CF)",
                        "rw": "🏹 جناح أيمن (RW)",
                        "lw": "🏹 جناح أيسر (LW)",
                        "cm": "🛡️ لاعب وسط (CM)",
                        "gk": "🧤 حارس مرمى (GK)",
                        "cap": "🎖️ كابتن",
                        "vc": "🥈 نائب كابتن",
                        "player": "🎽 لاعب"
                    }
                    
                    position = position_names.get(player_data["position"], "غير معروف")
                    embed.add_field(name="المركز", value=position, inline=True)
            
            logger.info(f"تم تحديد سعر اللاعب {user} بنجاح إلى {price} بلو باك")
            await ctx.send(embed=embed)
        
        except Exception as e:
            logger.error(f"حدث خطأ أثناء استخدام أمر اضافة_اسعار (النصي): {e}")
            await ctx.send(f"حدث خطأ أثناء تنفيذ الأمر: {e}")
    
    @commands.command(name="تحديد_سعر")
    async def set_price_cmd(self, ctx, user: discord.Member, price: int):
        """تحديد سعر لاعب للتعاقدات (بديل)"""
        await self.set_player_price_cmd(ctx, user, price)

async def setup(bot):
    await bot.add_cog(Admin(bot))
