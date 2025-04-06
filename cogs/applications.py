import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio

import database as db
from config import PLAYER_POSITIONS, EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR

logger = logging.getLogger("blue_lock_bot")

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store in-progress applications
        self.active_applications = {}
    
    @app_commands.command(name="تقديم", description="تقديم طلب انضمام إلى أحد الفرق")
    async def apply(self, interaction: discord.Interaction):
        # Check if user already has an active application
        if interaction.user.id in self.active_applications:
            await interaction.response.send_message(
                "لديك بالفعل طلب انضمام قيد التقديم. يرجى الانتهاء منه أو الانتظار قليلاً.",
                ephemeral=True
            )
            return
        
        # Check if user is already in a team
        player_data = db.get_player(interaction.guild.id, interaction.user.id)
        if player_data and player_data["team_id"] is not None:
            # Get the team name
            team = db.get_team(interaction.guild.id, team_id=player_data["team_id"])
            if team:
                await interaction.response.send_message(
                    f"أنت بالفعل عضو في فريق **{team['name']}**. إذا كنت تريد تغيير الفريق، يجب على كابتن فريقك الحالي إنهاء تعاقدك أولاً.",
                    ephemeral=True
                )
                return
        
        # Get all teams for later questions
        teams = db.get_all_teams(interaction.guild.id)
        if not teams:
            await interaction.response.send_message(
                "لا توجد فرق مسجلة في السيرفر حالياً. يرجى التواصل مع الإدارة.",
                ephemeral=True
            )
            return
        
        # Initialize application data
        self.active_applications[interaction.user.id] = {
            "guild_id": interaction.guild.id,
            "position": None,
            "goals": None,
            "assists": None,
            "saves": None,
            "preferred_team": None
        }
        
        # Respond to the user
        await interaction.response.send_message(
            "سيتم إرسال استمارة التقديم إليك عبر الرسائل الخاصة. تأكد من أن إعدادات الخصوصية لديك تسمح بذلك.",
            ephemeral=True
        )
        
        try:
            # Send initial DM to start the application process
            intro_embed = discord.Embed(
                title="📝 استمارة تقديم Blue Lock Rivals",
                description="مرحباً بك في استمارة التقديم للانضمام إلى فرق Blue Lock Rivals!\nسيتم طرح بعض الأسئلة، يرجى الإجابة عليها بصدق.",
                color=EMBED_COLOR
            )
            
            intro_embed.add_field(
                name="ملاحظة",
                value="سيتم إلغاء الاستمارة تلقائياً إذا لم يتم الرد خلال 5 دقائق من كل سؤال.",
                inline=False
            )
            
            await interaction.user.send(embed=intro_embed)
            
            # Ask for position
            position_embed = discord.Embed(
                title="🎮 المركز المفضل",
                description="ما هو المركز الذي تفضل اللعب به؟\n\nاكتب رقم المركز:",
                color=EMBED_COLOR
            )
            
            position_embed.add_field(
                name="المراكز المتاحة",
                value="1️⃣ مهاجم (CF)\n2️⃣ جناح أيمن (RW)\n3️⃣ جناح أيسر (LW)\n4️⃣ لاعب وسط (CM)\n5️⃣ حارس مرمى (GK)",
                inline=False
            )
            
            position_msg = await interaction.user.send(embed=position_embed)
            
            # Wait for position response
            try:
                position_response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == interaction.user and m.channel == position_msg.channel,
                    timeout=300.0  # 5 minutes
                )
                
                # Parse position
                position_map = {
                    "1": "cf",
                    "2": "rw",
                    "3": "lw",
                    "4": "cm",
                    "5": "gk",
                }
                
                position = position_map.get(position_response.content.strip())
                
                if not position:
                    await interaction.user.send("خيار غير صالح. يرجى استخدام الأرقام من 1 إلى 5. تم إلغاء التقديم.")
                    del self.active_applications[interaction.user.id]
                    return
                
                self.active_applications[interaction.user.id]["position"] = position
                
                # Ask for stats based on position
                if position == "gk":
                    # Ask for saves
                    saves_embed = discord.Embed(
                        title="🧤 التصديات",
                        description="كم عدد التصديات التي قمت بها؟",
                        color=EMBED_COLOR
                    )
                    
                    saves_msg = await interaction.user.send(embed=saves_embed)
                    
                    # Wait for saves response
                    saves_response = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author == interaction.user and m.channel == saves_msg.channel,
                        timeout=300.0
                    )
                    
                    try:
                        saves = int(saves_response.content.strip())
                        if saves < 0:
                            saves = 0
                        self.active_applications[interaction.user.id]["saves"] = saves
                        self.active_applications[interaction.user.id]["goals"] = 0
                        self.active_applications[interaction.user.id]["assists"] = 0
                    except ValueError:
                        await interaction.user.send("قيمة غير صالحة. يجب أن تكون التصديات رقماً. تم إلغاء التقديم.")
                        del self.active_applications[interaction.user.id]
                        return
                else:
                    # Ask for goals and assists
                    goals_embed = discord.Embed(
                        title="⚽ الأهداف",
                        description="كم عدد الأهداف التي سجلتها؟",
                        color=EMBED_COLOR
                    )
                    
                    goals_msg = await interaction.user.send(embed=goals_embed)
                    
                    # Wait for goals response
                    goals_response = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author == interaction.user and m.channel == goals_msg.channel,
                        timeout=300.0
                    )
                    
                    try:
                        goals = int(goals_response.content.strip())
                        if goals < 0:
                            goals = 0
                        self.active_applications[interaction.user.id]["goals"] = goals
                    except ValueError:
                        await interaction.user.send("قيمة غير صالحة. يجب أن تكون الأهداف رقماً. تم إلغاء التقديم.")
                        del self.active_applications[interaction.user.id]
                        return
                    
                    # Ask for assists
                    assists_embed = discord.Embed(
                        title="👟 التمريرات الحاسمة",
                        description="كم عدد التمريرات الحاسمة التي قدمتها؟",
                        color=EMBED_COLOR
                    )
                    
                    assists_msg = await interaction.user.send(embed=assists_embed)
                    
                    # Wait for assists response
                    assists_response = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author == interaction.user and m.channel == assists_msg.channel,
                        timeout=300.0
                    )
                    
                    try:
                        assists = int(assists_response.content.strip())
                        if assists < 0:
                            assists = 0
                        self.active_applications[interaction.user.id]["assists"] = assists
                        self.active_applications[interaction.user.id]["saves"] = 0
                    except ValueError:
                        await interaction.user.send("قيمة غير صالحة. يجب أن تكون التمريرات رقماً. تم إلغاء التقديم.")
                        del self.active_applications[interaction.user.id]
                        return
                
                # Ask for preferred team
                teams_text = "\n".join([f"{i+1}️⃣ {team['name']}" for i, team in enumerate(teams)])
                
                team_embed = discord.Embed(
                    title="🏆 الفريق المفضل",
                    description="ما هو الفريق الذي تفضل الانضمام إليه؟\n\nاكتب رقم الفريق:",
                    color=EMBED_COLOR
                )
                
                team_embed.add_field(
                    name="الفرق المتاحة",
                    value=teams_text,
                    inline=False
                )
                
                team_msg = await interaction.user.send(embed=team_embed)
                
                # Wait for team response
                team_response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == interaction.user and m.channel == team_msg.channel,
                    timeout=300.0
                )
                
                try:
                    team_index = int(team_response.content.strip()) - 1
                    if 0 <= team_index < len(teams):
                        preferred_team = teams[team_index]["name"]
                        self.active_applications[interaction.user.id]["preferred_team"] = preferred_team
                    else:
                        await interaction.user.send("رقم فريق غير صالح. تم إلغاء التقديم.")
                        del self.active_applications[interaction.user.id]
                        return
                except ValueError:
                    await interaction.user.send("قيمة غير صالحة. يجب أن يكون رقم الفريق رقماً. تم إلغاء التقديم.")
                    del self.active_applications[interaction.user.id]
                    return
                
                # Save application to database
                app_data = self.active_applications[interaction.user.id]
                application_id = db.save_application(
                    app_data["guild_id"],
                    interaction.user.id,
                    app_data["position"],
                    app_data["goals"],
                    app_data["assists"],
                    app_data["saves"],
                    app_data["preferred_team"]
                )
                
                # Send confirmation
                confirm_embed = discord.Embed(
                    title="✅ تم تقديم الطلب",
                    description="تم تقديم طلبك بنجاح! سيتم مراجعته من قبل كابتن الفريق قريباً.",
                    color=SUCCESS_COLOR
                )
                
                position_names = {
                    "cf": "⚔️ مهاجم (CF)",
                    "rw": "🏹 جناح أيمن (RW)",
                    "lw": "🏹 جناح أيسر (LW)",
                    "cm": "🛡️ لاعب وسط (CM)",
                    "gk": "🧤 حارس مرمى (GK)"
                }
                
                confirm_embed.add_field(name="المركز", value=position_names.get(app_data["position"], "غير معروف"), inline=True)
                confirm_embed.add_field(name="الفريق المفضل", value=app_data["preferred_team"], inline=True)
                
                if app_data["position"] == "gk":
                    confirm_embed.add_field(name="التصديات", value=str(app_data["saves"]), inline=True)
                else:
                    confirm_embed.add_field(name="الأهداف", value=str(app_data["goals"]), inline=True)
                    confirm_embed.add_field(name="التمريرات", value=str(app_data["assists"]), inline=True)
                
                await interaction.user.send(embed=confirm_embed)
                
                # Send application to the specific application channel
                try:
                    # Use fixed channel ID as specified (1354950727184683181)
                    application_channel_id = 1354950727184683181
                    channel = self.bot.get_channel(application_channel_id)
                    
                    if channel:
                        app_embed = discord.Embed(
                            title="📝 طلب انضمام جديد",
                            description=f"تقديم جديد من {interaction.user.mention}",
                            color=EMBED_COLOR
                        )
                        
                        app_embed.add_field(name="المركز", value=position_names.get(app_data["position"], "غير معروف"), inline=True)
                        app_embed.add_field(name="الفريق المفضل", value=app_data["preferred_team"], inline=True)
                        
                        if app_data["position"] == "gk":
                            app_embed.add_field(name="التصديات", value=str(app_data["saves"]), inline=True)
                        else:
                            app_embed.add_field(name="الأهداف", value=str(app_data["goals"]), inline=True)
                            app_embed.add_field(name="التمريرات", value=str(app_data["assists"]), inline=True)
                        
                        app_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                        app_embed.set_footer(text=f"معرف التقديم: {application_id}")
                        
                        await channel.send(embed=app_embed)
                    else:
                        logger.error(f"تعذر العثور على قناة التقديمات بالمعرف 1354950727184683181")
                except Exception as e:
                    logger.error(f"خطأ في إرسال التقديم إلى قناة التقديمات: {e}")
                
            except asyncio.TimeoutError:
                await interaction.user.send("انتهت مهلة التقديم. يرجى إعادة استخدام الأمر /تقديم للمحاولة مرة أخرى.")
                
        except discord.Forbidden:
            await interaction.followup.send(
                "لم أتمكن من إرسال رسالة خاصة إليك. يرجى التأكد من أن إعدادات الخصوصية لديك تسمح بالرسائل الخاصة من أعضاء السيرفر.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"خطأ في معالجة التقديم: {e}")
            await interaction.followup.send(
                "حدث خطأ أثناء معالجة طلب التقديم. يرجى المحاولة مرة أخرى لاحقاً.",
                ephemeral=True
            )
        finally:
            # Clean up after completion (successful or not)
            if interaction.user.id in self.active_applications:
                del self.active_applications[interaction.user.id]

async def setup(bot):
    await bot.add_cog(Applications(bot))
