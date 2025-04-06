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
            command_prefix="!",  # Changed to a simple prefix for direct commands
            intents=intents,
            application_id=os.getenv("APPLICATION_ID")
        )
        self.synced = False
        
    async def on_message(self, message):
        # Don't respond to self
        if message.author == self.user:
            return
            
        # Process commands
        await self.process_commands(message)
        
        # Help message for mentioning the bot
        if self.user.mentioned_in(message) and not message.mention_everyone:
            help_text = (
                "مرحبًا! أنا بوت **Blue Lock Rivals**.\n\n"
                "يمكنك استخدام أوامر السلاش (/) للتفاعل معي. بعض الأوامر المتاحة:\n"
                "• `/اضافة_فريق` - إنشاء فريق جديد\n"
                "• `/فريق` - عرض معلومات فريق\n"
                "• `/الفرق` - عرض قائمة الفرق\n"
                "• `/لاعب` - عرض إحصائيات لاعب\n"
                "• `/يومي` - الحصول على مكافأة يومية\n"
                "• `/رصيدي` - عرض رصيدك\n"
                "• `/تقديم` - تقديم طلب للانضمام إلى فريق\n\n"
                "إذا لم تظهر أوامر السلاش، فقد يستغرق الأمر بعض الوقت لمزامنتها مع خوادم ديسكورد."
            )
            
            embed = discord.Embed(
                title="🔒 مساعدة Blue Lock Rivals",
                description=help_text,
                color=0x3498db
            )
            
            await message.channel.send(embed=embed)

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
            logger.info("جاري مزامنة أوامر سلاش...")
            
            # Sync globally
            await self.tree.sync()
            
            # Sync to all guilds
            for guild in self.guilds:
                try:
                    await self.tree.sync(guild=guild)
                    logger.info(f"تم مزامنة الأوامر مع سيرفر: {guild.name}")
                except Exception as e:
                    logger.error(f"خطأ في مزامنة الأوامر مع سيرفر {guild.name}: {e}")
            
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

# Add some regular text commands
@bot.command(name="ping")
async def ping(ctx):
    """Check the bot's response time"""
    await ctx.send(f"🏓 بونج! {round(bot.latency * 1000)}ms")

@bot.command(name="مساعدة", aliases=["blhelp"])
async def blhelp_command(ctx):
    """Show help message"""
    help_text = (
        "مرحبًا! أنا بوت **Blue Lock Rivals**.\n\n"
        "يمكنك استخدام أوامر السلاش (/) للتفاعل معي. بعض الأوامر المتاحة:\n"
        "• `/اضافة_فريق` - إنشاء فريق جديد\n"
        "• `/فريق` - عرض معلومات فريق\n"
        "• `/الفرق` - عرض قائمة الفرق\n"
        "• `/لاعب` - عرض إحصائيات لاعب\n"
        "• `/يومي` - الحصول على مكافأة يومية\n"
        "• `/رصيدي` - عرض رصيدك\n"
        "• `/تقديم` - تقديم طلب للانضمام إلى فريق\n\n"
        "إذا لم تظهر أوامر السلاش، فقد يستغرق الأمر بعض الوقت لمزامنتها مع خوادم ديسكورد."
    )
    
    embed = discord.Embed(
        title="🔒 مساعدة Blue Lock Rivals",
        description=help_text,
        color=0x3498db
    )
    
    await ctx.send(embed=embed)

@bot.command(name="status")
async def status_command(ctx):
    """Show bot status"""
    embed = discord.Embed(
        title="📊 حالة البوت",
        description="معلومات عن حالة البوت الحالية",
        color=0x3498db
    )
    
    # Get stats
    guilds_count = len(bot.guilds)
    users_count = sum(guild.member_count for guild in bot.guilds)
    commands_count = len(bot.tree.get_commands())
    
    embed.add_field(name="👥 عدد السيرفرات", value=str(guilds_count), inline=True)
    embed.add_field(name="👤 عدد المستخدمين", value=str(users_count), inline=True)
    embed.add_field(name="📝 عدد الأوامر", value=str(commands_count), inline=True)
    embed.add_field(name="⏱️ زمن الاستجابة", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    await ctx.send(embed=embed)

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
