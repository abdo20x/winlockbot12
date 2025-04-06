# List of cogs to load when the bot starts
INITIAL_EXTENSIONS = [
    "cogs.teams",
    "cogs.economy",
    "cogs.admin",
    "cogs.applications",
    "cogs.player_stats"
]

# Database file path
DATABASE_PATH = "bluelock.db"

# Maximum player number in team (default, can be changed with command)
DEFAULT_ROSTER_CAP = 22

# Admin user ID (for restricted commands)
ADMIN_USER_ID = 1225190102469181542

# Notification channel ID for contract announcements
NOTIFICATION_CHANNEL_ID = 1345407172866998342

# Currency name
CURRENCY_NAME = "بلو باك"

# Daily reward amount
DAILY_REWARD = 1000000

# Cooldown for daily command (in seconds)
DAILY_COOLDOWN = 86400  # 24 hours

# Player positions
PLAYER_POSITIONS = ["cf", "rw", "lw", "cm", "gk"]

# Team colors for embeds
EMBED_COLOR = 0x3498db
ERROR_COLOR = 0xe74c3c
SUCCESS_COLOR = 0x2ecc71
