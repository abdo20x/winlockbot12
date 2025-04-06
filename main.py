import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

from database import create_tables
from config import INITIAL_EXTENSIONS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blue_lock_bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot initialization
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class BlueLocKBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=os.getenv("APPLICATION_ID")
        )
        self.synced = False

    async def setup_hook(self):
        # Create database tables
        create_tables()
        
        # Load all extensions
        for extension in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info(f"تم تحميل الملحق {extension}")
            except Exception as e:
                logger.error(f"فشل في تحميل الملحق {extension}: {e}")
    
    async def on_ready(self):
        if not self.synced:
            # Sync slash commands with Discord
            await self.tree.sync()
            self.synced = True
            
        logger.info(f"تم تسجيل الدخول كـ {self.user} (ID: {self.user.id})")
        logger.info(f"البوت متصل في {len(self.guilds)} سيرفر")
        logger.info("البوت جاهز للاستخدام!")
        
        # Set bot activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Blue Lock Rivals 🔒"
            )
        )

bot = BlueLocKBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"هذا الأمر تحت فترة انتظار. يرجى المحاولة بعد {error.retry_after:.2f} ثانية.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "ليس لديك الصلاحيات المطلوبة لاستخدام هذا الأمر.",
            ephemeral=True
        )
    else:
        # Log all other errors
        logger.error(f"حدث خطأ: {error}")
        await interaction.response.send_message(
            f"حدث خطأ أثناء تنفيذ الأمر: {error}",
            ephemeral=True
        )

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("لم يتم العثور على رمز البوت (DISCORD_TOKEN). يرجى التحقق من ملف .env")
        exit(1)
    
    # Run the bot
    asyncio.run(bot.start(TOKEN))
