import discord
from discord import app_commands
from discord.ext import commands
import database as db
from config import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, ADMIN_USER_ID

"""
سكربت عرض - Blue Lock Rivals Bot
يحتوي على أمر عرض بسيط
"""

class نظام(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="نظام", description="عرض معلومات النظام")
    async def display_command(
        self, 
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="🔒 معلومات النظام",
            description="تم تطوير أمر سلاش جديد: `/عرض_تفاصيل`",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="✨ الأمر الجديد",
            value="استخدم الأمر `/عرض_تفاصيل` لعرض معلومات الفرق واللاعبين بشكل جميل ومفصل",
            inline=False
        )
        
        embed.add_field(
            name="📋 خيارات الأمر",
            value="- عرض تفاصيل فريق معين بتحديد اسم الفريق\n- عرض إحصائيات لاعب معين بتحديد اللاعب\n- عرض قائمة جميع الفرق بدون تحديد أي خيار",
            inline=False
        )
        
        embed.set_footer(text="Blue Lock Rivals | تم التطوير بواسطة Replit")
        
        await interaction.response.send_message(embed=embed)
        
    @commands.command(name="نظام")
    async def display_cmd(self, ctx):
        """عرض معلومات النظام (الأمر النصي)"""
        embed = discord.Embed(
            title="🔒 معلومات النظام",
            description="تم تطوير أمر سلاش جديد: `/عرض_تفاصيل`",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="✨ الأمر الجديد",
            value="استخدم الأمر `/عرض_تفاصيل` لعرض معلومات الفرق واللاعبين بشكل جميل ومفصل",
            inline=False
        )
        
        embed.add_field(
            name="📋 خيارات الأمر",
            value="- عرض تفاصيل فريق معين بتحديد اسم الفريق\n- عرض إحصائيات لاعب معين بتحديد اللاعب\n- عرض قائمة جميع الفرق بدون تحديد أي خيار",
            inline=False
        )
        
        embed.set_footer(text="Blue Lock Rivals | تم التطوير بواسطة Replit")
        
        await ctx.send(embed=embed)
            
async def setup(bot):
    await bot.add_cog(نظام(bot))