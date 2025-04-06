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
    
    @app_commands.command(name="تقديم", description="تقديم طلب انضمام واختيار المركز الذي تجيده")
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
                description="ما هو المركز الذي تعرف أن تلعب فيه بشكل أفضل؟\n\nاكتب رقم المركز:",
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
                
                # Parse position - تحسين لمعالجة إدخال متعدد المراكز
                position_text = position_response.content.strip()
                
                # تحويل الأرقام العربية إلى إنجليزية
                arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                position_text = position_text.translate(arabic_to_english)
                
                # تقسيم النص لمعرفة إذا كان يحتوي على مراكز متعددة مفصولة بمسافات
                position_parts = position_text.lower().split()
                
                # في حالة وجود مراكز متعددة، نأخذ الأول فقط
                user_input = position_parts[0] if position_parts else ""
                
                # نفحص أيضًا كامل النص الأصلي للتأكد
                full_input = position_text.lower()
                
                position_map = {
                    # أرقام
                    "1": "cf", "١": "cf", "واحد": "cf",
                    "2": "rw", "٢": "rw", "اثنين": "rw",
                    "3": "lw", "٣": "lw", "ثلاثة": "lw",
                    "4": "cm", "٤": "cm", "أربعة": "cm", "اربعة": "cm",
                    "5": "gk", "٥": "gk", "خمسة": "gk",
                    
                    # مصطلحات عربية
                    "مهاجم": "cf", "هجوم": "cf",
                    "جناح أيمن": "rw", "جناح ايمن": "rw", "يمين": "rw",
                    "جناح أيسر": "lw", "جناح ايسر": "lw", "يسار": "lw",
                    "وسط": "cm", "لاعب وسط": "cm", "وسط الملعب": "cm",
                    "حارس": "gk", "حارس مرمى": "gk", "جول كيبر": "gk",
                    
                    # اختصارات إنجليزية
                    "cf": "cf", "striker": "cf", "st": "cf", "9": "cf",
                    "rw": "rw", "right": "rw", "7": "rw",
                    "lw": "lw", "left": "lw", "11": "lw",
                    "cm": "cm", "mid": "cm", "midfielder": "cm", "8": "cm",
                    "gk": "gk", "goal": "gk", "goalkeeper": "gk", "keeper": "gk",
                }
                
                position = None
                
                # خطوة 1: تحقق من المدخل المجزأ الأول (الجزء الأول أو الرقم الأول)
                if user_input in position_map:
                    position = position_map[user_input]
                
                # خطوة 2: إذا لم يتم العثور على تطابق، ابحث في كل جزء من الأجزاء المنفصلة
                if not position and len(position_parts) > 1:
                    for part in position_parts:
                        if part in position_map:
                            position = position_map[part]
                            break
                
                # خطوة 3: إذا لم يتم العثور على تطابق، ابحث عن أجزاء من الكلمات
                if not position:
                    for key in position_map:
                        # نتحقق من وجود الكلمة المفتاحية في الإدخال الكامل
                        if key in full_input:
                            position = position_map[key]
                            break
                
                # خطوة 4: تحقق من وجود أي أرقام في المدخل
                if not position:
                    import re
                    number_match = re.search(r'\d+', position_text)
                    if number_match:
                        num = number_match.group(0)
                        if num in ["1", "١"]:
                            position = "cf"  # مهاجم
                        elif num in ["2", "٢"]:
                            position = "rw"  # جناح أيمن
                        elif num in ["3", "٣"]:
                            position = "lw"  # جناح أيسر
                        elif num in ["4", "٤"]:
                            position = "cm"  # وسط
                        elif num in ["5", "٥"]:
                            position = "gk"  # حارس مرمى
                
                if not position:
                    # إرسال رسالة أكثر توضيحًا للمستخدم
                    await interaction.user.send("لم أتمكن من فهم اختيارك للمركز. يرجى استخدام رقم من 1 إلى 5 أو كتابة اسم المركز بشكل واضح (مثل: مهاجم، جناح أيمن، وسط، حارس). حاول مرة أخرى باستخدام أمر /تقديم.")
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
                    
                    # معالجة إدخال التصديات بشكل أكثر مرونة
                    saves_text = saves_response.content.strip()
                    
                    # تحويل الأرقام العربية إلى إنجليزية
                    arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    saves_text = saves_text.translate(arabic_to_english)
                    
                    # استخراج الأرقام من النص
                    import re
                    numbers = re.findall(r'\d+', saves_text)
                    
                    if numbers:
                        # استخدام أول رقم تم العثور عليه
                        saves = int(numbers[0])
                        if saves < 0:
                            saves = 0
                        self.active_applications[interaction.user.id]["saves"] = saves
                        self.active_applications[interaction.user.id]["goals"] = 0
                        self.active_applications[interaction.user.id]["assists"] = 0
                    else:
                        # محاولة معالجة النص كوصف (مثل "كثير" أو "قليل")
                        text_lower = saves_text.lower()
                        
                        if any(word in text_lower for word in ["كثير", "عديد", "كبير"]):
                            saves = 50  # قيمة افتراضية عالية
                        elif any(word in text_lower for word in ["متوسط", "عادي", "وسط"]):
                            saves = 25  # قيمة متوسطة
                        elif any(word in text_lower for word in ["قليل", "بسيط", "صغير"]):
                            saves = 10  # قيمة منخفضة
                        elif any(word in text_lower for word in ["لا", "صفر", "ما فيه", "مافي"]):
                            saves = 0  # صفر
                        else:
                            # إذا لم نستطع فهم المدخل، نستخدم قيمة افتراضية
                            saves = 15
                            
                        self.active_applications[interaction.user.id]["saves"] = saves
                        self.active_applications[interaction.user.id]["goals"] = 0
                        self.active_applications[interaction.user.id]["assists"] = 0
                        
                        # لا نرسل إشعارًا منفصلًا هنا لتجنب تأخير تسلسل الأسئلة
                    
                    # تأكيد استلام الإدخال - لا نرسل تأكيدًا منفصلًا هنا لتجنب تداخل الرسائل
                    
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
                    
                    # معالجة إدخال الأهداف بشكل أكثر مرونة
                    goals_text = goals_response.content.strip()
                    
                    # تحويل الأرقام العربية إلى إنجليزية
                    arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    goals_text = goals_text.translate(arabic_to_english)
                    
                    # استخراج الأرقام من النص
                    import re
                    numbers = re.findall(r'\d+', goals_text)
                    
                    if numbers:
                        # استخدام أول رقم تم العثور عليه
                        goals = int(numbers[0])
                        if goals < 0:
                            goals = 0
                        self.active_applications[interaction.user.id]["goals"] = goals
                    else:
                        # محاولة معالجة النص كوصف
                        text_lower = goals_text.lower()
                        
                        if any(word in text_lower for word in ["كثير", "عديد", "كبير"]):
                            goals = 40  # قيمة افتراضية عالية
                        elif any(word in text_lower for word in ["متوسط", "عادي", "وسط"]):
                            goals = 20  # قيمة متوسطة
                        elif any(word in text_lower for word in ["قليل", "بسيط", "صغير"]):
                            goals = 10  # قيمة منخفضة
                        elif any(word in text_lower for word in ["لا", "صفر", "ما فيه", "مافي"]):
                            goals = 0  # صفر
                        else:
                            # إذا لم نستطع فهم المدخل، نستخدم قيمة افتراضية
                            goals = 15
                            
                        self.active_applications[interaction.user.id]["goals"] = goals
                        
                        # لا نرسل إشعارًا منفصلًا هنا لتجنب تأخير تسلسل الأسئلة
                    
                    # لا نرسل تأكيدًا منفصلًا هنا لتجنب تداخل الرسائل
                    
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
                    
                    # معالجة إدخال التمريرات الحاسمة بشكل أكثر مرونة
                    assists_text = assists_response.content.strip()
                    
                    # تحويل الأرقام العربية إلى إنجليزية
                    arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    assists_text = assists_text.translate(arabic_to_english)
                    
                    # استخراج الأرقام من النص
                    import re
                    numbers = re.findall(r'\d+', assists_text)
                    
                    if numbers:
                        # استخدام أول رقم تم العثور عليه
                        assists = int(numbers[0])
                        if assists < 0:
                            assists = 0
                        self.active_applications[interaction.user.id]["assists"] = assists
                        self.active_applications[interaction.user.id]["saves"] = 0
                    else:
                        # محاولة معالجة النص كوصف
                        text_lower = assists_text.lower()
                        
                        if any(word in text_lower for word in ["كثير", "عديد", "كبير"]):
                            assists = 30  # قيمة افتراضية عالية
                        elif any(word in text_lower for word in ["متوسط", "عادي", "وسط"]):
                            assists = 15  # قيمة متوسطة
                        elif any(word in text_lower for word in ["قليل", "بسيط", "صغير"]):
                            assists = 5  # قيمة منخفضة
                        elif any(word in text_lower for word in ["لا", "صفر", "ما فيه", "مافي"]):
                            assists = 0  # صفر
                        else:
                            # إذا لم نستطع فهم المدخل، نستخدم قيمة افتراضية
                            assists = 10
                            
                        self.active_applications[interaction.user.id]["assists"] = assists
                        self.active_applications[interaction.user.id]["saves"] = 0
                        
                        # لا نرسل إشعارًا منفصلًا هنا لتجنب تأخير تسلسل الأسئلة
                    
                    # لا نرسل تأكيدًا منفصلًا هنا لتجنب تداخل الرسائل مع السؤال التالي
                
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
                
                # معالجة اختيار الفريق بشكل أكثر مرونة
                user_team_input = team_response.content.strip().lower()
                preferred_team = None
                
                # محاولة تحويل إلى رقم أولاً
                try:
                    # قبول الأرقام العربية أيضًا
                    arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    user_team_input = user_team_input.translate(arabic_to_english)
                    
                    # تحويل أي شيء يبدو كرقم إلى رقم
                    # تجاهل أي نص آخر في المدخل مثل "فريق 1" أو "رقم 2"
                    team_index = -1
                    for char in user_team_input:
                        if char.isdigit():
                            team_index = int(char) - 1
                            break
                            
                    if 0 <= team_index < len(teams):
                        preferred_team = teams[team_index]["name"]
                    
                except ValueError:
                    # لا نفعل شيئًا، سننتقل للمحاولة التالية
                    pass
                    
                # إذا لم يتم العثور على مطابقة بالأرقام، نبحث عن اسم الفريق
                if not preferred_team:
                    for team in teams:
                        team_name = team["name"].lower()
                        # تحقق من وجود اسم الفريق في المدخل
                        if team_name in user_team_input or user_team_input in team_name:
                            preferred_team = team["name"]
                            break
                
                # إذا لم نتمكن من العثور على الفريق، نطلب من المستخدم المحاولة مرة أخرى
                if not preferred_team:
                    teams_names = ", ".join([team["name"] for team in teams])
                    await interaction.user.send(f"لم أتمكن من فهم الفريق الذي تريده. يرجى اختيار رقم الفريق من القائمة أو كتابة اسم الفريق بشكل واضح. الفرق المتاحة هي: {teams_names}. تم إلغاء التقديم، يرجى استخدام أمر /تقديم مرة أخرى.")
                    del self.active_applications[interaction.user.id]
                    return
                    
                # حفظ الفريق المفضل
                self.active_applications[interaction.user.id]["preferred_team"] = preferred_team
                
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
