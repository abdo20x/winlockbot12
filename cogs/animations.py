import discord
from discord.ext import commands
import asyncio
import random
from typing import List, Optional, Union, Callable

# ألوان للتأثيرات المتحركة
ANIMATION_COLORS = [
    0x3498db,  # أزرق
    0x2ecc71,  # أخضر
    0xe74c3c,  # أحمر
    0xf39c12,  # برتقالي
    0x9b59b6,  # بنفسجي
    0x1abc9c,  # تركواز
    0xe67e22,  # برتقالي داكن
    0x34495e   # كحلي
]

# أشكال للرسوم المتحركة
ANIMATION_SHAPES = [
    "◈", "◇", "◆", "❖", "✧", "✦", "❈", "✷", "✸", "✹", 
    "✺", "✻", "★", "☆", "✪", "✫", "✬", "✭", "✮", "✯"
]

class TeamLogoAnimator:
    """فئة للتعامل مع رسوم متحركة لشعارات الفرق"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def animate_logo_reveal(
        self, 
        channel: discord.TextChannel, 
        team_name: str, 
        logo_url: str,
        emoji: str = "⚽", 
        description: str = None,
        fields: List[dict] = None,
        color: int = None
    ) -> discord.Message:
        """
        إنشاء رسم متحرك للكشف عن شعار فريق
        
        المعلمات:
        - channel: قناة لإرسال الرسالة فيها
        - team_name: اسم الفريق
        - logo_url: رابط شعار الفريق
        - emoji: إيموجي الفريق
        - description: وصف اختياري للرسالة
        - fields: حقول إضافية للإمبد [{'name': 'اسم', 'value': 'قيمة', 'inline': True}]
        - color: لون الإمبد

        يعيد:
        - الرسالة النهائية بعد انتهاء الرسم المتحرك
        """
        # تهيئة الإمبد الأولي (غلاف مغلق)
        if not color:
            color = random.choice(ANIMATION_COLORS)
        
        # المرحلة 1: غلاف مغلق
        embed = discord.Embed(
            title="جاري تحميل شعار الفريق...",
            description="⌛ يرجى الانتظار...",
            color=color
        )
        embed.set_footer(text="شعار الفريق قيد التحميل")
        message = await channel.send(embed=embed)
        await asyncio.sleep(1.5)
        
        # المرحلة 2: أشكال متحركة
        frames = ["Loading"] + [f"Loading {shape}" for shape in ANIMATION_SHAPES[:8]]
        for frame in frames:
            embed = discord.Embed(
                title=frame,
                description="⌛ يرجى الانتظار...",
                color=random.choice(ANIMATION_COLORS)
            )
            embed.set_footer(text="شعار الفريق قيد التحميل")
            await message.edit(embed=embed)
            await asyncio.sleep(0.5)
        
        # المرحلة 3: تدرج ظهور الشعار
        reveal_frames = [
            "▒▒▒▒▒▒▒▒▒▒", 
            "█▒▒▒▒▒▒▒▒▒", 
            "██▒▒▒▒▒▒▒▒", 
            "███▒▒▒▒▒▒▒", 
            "████▒▒▒▒▒▒", 
            "█████▒▒▒▒▒", 
            "██████▒▒▒▒", 
            "███████▒▒▒", 
            "████████▒▒", 
            "█████████▒", 
            "██████████"
        ]
        
        for i, frame in enumerate(reveal_frames):
            progress = i / len(reveal_frames)
            embed = discord.Embed(
                title=f"تحميل الشعار... {int(progress * 100)}%",
                description=f"[{frame}] {int(progress * 100)}%",
                color=color
            )
            if progress > 0.7:  # بدء إظهار الصورة المصغرة تدريجياً
                embed.set_thumbnail(url=logo_url)
            embed.set_footer(text="شعار الفريق قيد التحميل")
            await message.edit(embed=embed)
            await asyncio.sleep(0.3)
        
        # المرحلة 4: العرض النهائي بتأثير الظهور
        final_embed = discord.Embed(
            title=f"✨ {team_name} {emoji} ✨",
            description=description or f"تم عرض شعار فريق {team_name}",
            color=color
        )
        final_embed.set_image(url=logo_url)
        
        # إضافة الحقول
        if fields:
            for field in fields:
                final_embed.add_field(
                    name=field.get('name', ''),
                    value=field.get('value', ''),
                    inline=field.get('inline', True)
                )
                
        final_embed.set_footer(text=f"فريق {team_name}")
        await message.edit(embed=final_embed)
        return message
    
    async def animate_player_transfer(
        self,
        channel: discord.TextChannel,
        player_name: str,
        player_avatar: str,
        from_team: str,
        to_team: str,
        from_logo: str = None,
        to_logo: str = None,
        transfer_fee: int = 0,
        color: int = None
    ) -> discord.Message:
        """
        إنشاء رسم متحرك لانتقال لاعب بين فريقين
        
        المعلمات:
        - channel: قناة لإرسال الرسالة فيها
        - player_name: اسم اللاعب
        - player_avatar: صورة اللاعب
        - from_team: اسم الفريق السابق
        - to_team: اسم الفريق الجديد
        - from_logo: شعار الفريق السابق
        - to_logo: شعار الفريق الجديد
        - transfer_fee: قيمة الانتقال
        - color: لون الإمبد

        يعيد:
        - الرسالة النهائية بعد انتهاء الرسم المتحرك
        """
        if not color:
            color = random.choice(ANIMATION_COLORS)
            
        # المرحلة 1: إعلان انتقال جديد
        embed = discord.Embed(
            title="🚨 انتقال جديد! 🚨",
            description="يتم الآن الإعلان عن صفقة انتقال جديدة...",
            color=color
        )
        embed.set_footer(text="جاري تجهيز تفاصيل الانتقال")
        message = await channel.send(embed=embed)
        await asyncio.sleep(1.5)
        
        # المرحلة 2: تعتيم الشاشة مع نقاط متحركة
        dots = [".", "..", "...", "...."]
        for _ in range(2):
            for dot in dots:
                embed = discord.Embed(
                    title="🚨 عاجل 🚨",
                    description=f"صفقة انتقال وشيكة{dot}",
                    color=random.choice(ANIMATION_COLORS)
                )
                embed.set_footer(text="ترقبوا الإعلان بعد قليل!")
                await message.edit(embed=embed)
                await asyncio.sleep(0.5)
        
        # المرحلة 3: تشويق
        teaser_texts = [
            "⏱️ لحظات وسيتم الإعلان...",
            "👀 من سيكون اللاعب المنتقل؟",
            "💰 قريباً... الكشف عن تفاصيل الصفقة",
            "🔄 انتقال مثير على وشك أن يُكشف!"
        ]
        
        for text in teaser_texts:
            embed = discord.Embed(
                title="📣 استعدوا! 📣",
                description=text,
                color=random.choice(ANIMATION_COLORS)
            )
            embed.set_footer(text="الإعلان وشيك...")
            await message.edit(embed=embed)
            await asyncio.sleep(1)
        
        # المرحلة 4: إظهار الفريق السابق
        if from_logo:
            embed = discord.Embed(
                title=f"🏆 انتقال من: {from_team}",
                description="الفريق السابق للاعب",
                color=color
            )
            embed.set_thumbnail(url=from_logo)
            embed.set_footer(text="شاهد الوجهة التالية...")
            await message.edit(embed=embed)
            await asyncio.sleep(2)
        
        # المرحلة 5: إظهار الفريق الجديد
        if to_logo:
            embed = discord.Embed(
                title=f"✨ انتقال إلى: {to_team} ✨",
                description="الفريق الجديد للاعب",
                color=color
            )
            embed.set_thumbnail(url=to_logo)
            embed.set_footer(text="من هو اللاعب؟")
            await message.edit(embed=embed)
            await asyncio.sleep(2)
        
        # المرحلة 6: العرض النهائي
        final_embed = discord.Embed(
            title=f"🔄 صفقة رسمية: {player_name} ينتقل إلى {to_team}!",
            description=f"انتقال رسمي من {from_team} إلى {to_team}",
            color=color
        )
        
        if player_avatar:
            final_embed.set_thumbnail(url=player_avatar)
        
        # إضافة حقول لتفاصيل الصفقة
        if from_logo and to_logo:
            from_team_field = f"[​]({from_logo}) {from_team}"
            to_team_field = f"{to_team} [​]({to_logo})"
        else:
            from_team_field = from_team
            to_team_field = to_team
            
        final_embed.add_field(name="من", value=from_team_field, inline=True)
        final_embed.add_field(name="إلى", value=to_team_field, inline=True)
        
        if transfer_fee > 0:
            final_embed.add_field(
                name="💰 قيمة الصفقة",
                value=f"{transfer_fee:,} بلو باك",
                inline=False
            )
        
        final_embed.set_footer(text=f"تم الانتقال بنجاح! 🎉")
        await message.edit(embed=final_embed)
        return message


class Animations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logo_animator = TeamLogoAnimator(bot)
    
    @commands.command(name="تجريب_رسم_متحرك")
    async def test_animation(self, ctx, *, team_name="Blue Lock Rivals"):
        """اختبار للرسم المتحرك لشعار الفريق (مؤقت)"""
        # هذا الأمر للاختبار فقط
        # استخدم شعاراً اختبارياً
        logo_url = "https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
        
        await ctx.send("جاري بدء اختبار الرسم المتحرك، انتظر قليلاً...")
        await self.logo_animator.animate_logo_reveal(
            channel=ctx.channel,
            team_name=team_name,
            logo_url=logo_url,
            emoji="⚽",
            description=f"عرض تجريبي لشعار فريق {team_name}",
            fields=[
                {'name': 'نوع الرسم', 'value': 'تأثير متحرك', 'inline': True},
                {'name': 'الغرض', 'value': 'اختبار', 'inline': True}
            ]
        )
    
    @commands.command(name="تجريب_انتقال")
    async def test_transfer(self, ctx, player_name="لاعب تجريبي"):
        """اختبار للرسم المتحرك لانتقال اللاعبين (مؤقت)"""
        # هذا الأمر للاختبار فقط
        # استخدم شعارات اختبارية
        logo1 = "https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
        logo2 = "https://cdn.discordapp.com/emojis/1116216403602010112.webp?size=96&quality=lossless"
        
        await ctx.send("جاري بدء اختبار تأثير الانتقال، انتظر قليلاً...")
        await self.logo_animator.animate_player_transfer(
            channel=ctx.channel,
            player_name=player_name,
            player_avatar=ctx.author.display_avatar.url,
            from_team="فريق الاختبار أ",
            to_team="فريق الاختبار ب",
            from_logo=logo1,
            to_logo=logo2,
            transfer_fee=50000000
        )


async def setup(bot):
    await bot.add_cog(Animations(bot))