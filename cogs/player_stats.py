import discord
from discord import app_commands
from discord.ext import commands
import logging

import database as db
from config import EMBED_COLOR, ERROR_COLOR, ADMIN_USER_ID

logger = logging.getLogger("blue_lock_bot")

class PlayerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # تم إزالة أمر !لاعب (ستات) حسب طلب المستخدم
    
    # تم إزالة أمر /لاعب (ستات) حسب طلب المستخدم

async def setup(bot):
    await bot.add_cog(PlayerStats(bot))
