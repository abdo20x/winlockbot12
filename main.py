import os
import logging
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import asyncio
import time
import datetime
from flask import Flask
import threading

from database import create_tables
from config import INITIAL_EXTENSIONS

# إنشاء تطبيق Flask بسيط للحفاظ على نشاط ريبليت
app = Flask(__name__)

@app.route('/')
def home():
    uptime = datetime.timedelta(seconds=int(time.time() - start_time))
    return f'Bot is running! Uptime: {uptime}'

# وقت بدء البوت
start_time = time.time()

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
                
        # تهيئة المؤثرات المتحركة وربطها بفئة الفرق
        try:
            # الحصول على فئة الفرق وفئة المؤثرات
            teams_cog = self.get_cog("Teams")
            animations_cog = self.get_cog("Animations")
            
            # ربط المؤثرات المتحركة بفئة الفرق
            if teams_cog and animations_cog:
                if teams_cog.initialize_animator(animations_cog):
                    logger.info("تم تهيئة المؤثرات المتحركة بنجاح")
                else:
                    logger.warning("فشل في تهيئة المؤثرات المتحركة")
        except Exception as e:
            logger.error(f"خطأ أثناء تهيئة المؤثرات المتحركة: {e}")
    
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

# Function to keep the bot running 24/7 using Flask server
def run_flask_server():
    import socket
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('0.0.0.0', port)) == 0
            
    # Try to find an available port starting from 5001
    port = 5001
    if is_port_in_use(5000):
        while is_port_in_use(port) and port < 6000:
            port += 1
        logger.info(f"Port 5000 is in use. Using port {port} instead.")
    else:
        port = 5000
        
    app.run(host='0.0.0.0', port=port)

async def start_bot():
    try:
        # تأخير أطول قبل بدء تشغيل البوت للتعامل مع مشكلة rate limiting
        logger.info("جاري الانتظار 30 ثانية قبل محاولة الاتصال بـ Discord API...")
        await asyncio.sleep(30)
        
        logger.info("محاولة الاتصال بـ Discord API...")
        await bot.start(TOKEN)
    except discord.errors.HTTPException as e:
        if e.status == 429:  # رمز الخطأ الخاص بتجاوز معدل الطلبات
            # استخراج وقت الانتظار من رسالة الخطأ أو استخدام قيمة افتراضية أكبر (5 دقائق)
            retry_after = getattr(e, 'retry_after', 300)
            logger.warning(f"تم تجاوز معدل الطلبات (429). إعادة المحاولة بعد {retry_after} ثانية")
            
            # انتظار مدة أطول قبل إعادة المحاولة
            await asyncio.sleep(retry_after)
            logger.info("إعادة محاولة الاتصال بعد الانتظار...")
            return await start_bot()
        else:
            # أخطاء HTTP أخرى
            logger.error(f"خطأ HTTP: {e.status} - {str(e)}")
            raise
    except Exception as e:
        logger.error(f"حدث خطأ غير متوقع أثناء تشغيل البوت: {str(e)}")
        # انتظار 60 ثانية قبل إعادة المحاولة في حالة حدوث أي خطأ آخر
        await asyncio.sleep(60)
        logger.info("إعادة محاولة الاتصال بعد حدوث خطأ...")
        return await start_bot()

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("لم يتم العثور على رمز البوت (DISCORD_TOKEN). يرجى التحقق من ملف .env")
        exit(1)
    
    # Start Flask server in a separate thread to keep the bot alive 24/7
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True  # This ensures the thread will close when the main program exits
    flask_thread.start()
    logger.info("بدأ خادم Flask للحفاظ على نشاط البوت 24/7")
    
    # Run the bot with retry logic
    asyncio.run(start_bot())
