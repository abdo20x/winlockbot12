import sqlite3
import logging
import json
from config import DATABASE_PATH

logger = logging.getLogger("blue_lock_bot")

def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Create all necessary database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        guild_id INTEGER PRIMARY KEY,
        roster_cap INTEGER DEFAULT 22,
        notification_channel_id INTEGER DEFAULT NULL,
        application_channel_id INTEGER DEFAULT NULL,
        contract_channel_id INTEGER DEFAULT NULL
    )
    ''')
    
    # Create teams table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        role_id INTEGER NOT NULL,
        emoji TEXT,
        captain_id INTEGER,
        captain_role_id INTEGER,
        UNIQUE(guild_id, name)
    )
    ''')
    
    # Create players table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        guild_id INTEGER NOT NULL,
        team_id INTEGER,
        position TEXT,
        goals INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        saves INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0,
        price INTEGER DEFAULT 0,
        FOREIGN KEY (team_id) REFERENCES teams (id)
    )
    ''')
    
    # تحقق من وجود عمود price في جدول players
    try:
        cursor.execute("SELECT price FROM players LIMIT 1")
    except sqlite3.OperationalError:
        # إذا لم يكن العمود موجوداً، قم بإضافته
        logger.info("إضافة عمود price إلى جدول players")
        cursor.execute("ALTER TABLE players ADD COLUMN price INTEGER DEFAULT 0")
    
    # Create daily rewards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_rewards (
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        last_claimed TIMESTAMP NOT NULL,
        PRIMARY KEY (user_id, guild_id)
    )
    ''')
    
    # Create player offers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        from_captain_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (team_id) REFERENCES teams (id)
    )
    ''')
    
    # Create applications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        position TEXT NOT NULL,
        goals INTEGER,
        assists INTEGER,
        saves INTEGER,
        preferred_team TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("تم إنشاء قواعد البيانات بنجاح")

def add_team(guild_id, name, role_id, emoji, captain_id=None, captain_role_id=None):
    """Add a new team to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO teams (guild_id, name, role_id, emoji, captain_id, captain_role_id) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, name, role_id, emoji, captain_id, captain_role_id)
        )
        team_id = cursor.lastrowid
        conn.commit()
        return team_id
    except sqlite3.IntegrityError:
        # Team name already exists
        return None
    finally:
        conn.close()

def remove_team(guild_id, team_id):
    """Remove a team from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First, update any players in this team to have no team
    cursor.execute(
        "UPDATE players SET team_id = NULL WHERE guild_id = ? AND team_id = ?",
        (guild_id, team_id)
    )
    
    # Then delete the team
    cursor.execute(
        "DELETE FROM teams WHERE guild_id = ? AND id = ?",
        (guild_id, team_id)
    )
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_team(guild_id, team_id=None, team_name=None, role_id=None):
    """Get team information by ID, name, or role ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if team_id:
        cursor.execute(
            "SELECT * FROM teams WHERE guild_id = ? AND id = ?",
            (guild_id, team_id)
        )
    elif team_name:
        cursor.execute(
            "SELECT * FROM teams WHERE guild_id = ? AND name = ?",
            (guild_id, team_name)
        )
    elif role_id:
        cursor.execute(
            "SELECT * FROM teams WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id)
        )
    else:
        conn.close()
        return None
    
    team = cursor.fetchone()
    conn.close()
    
    if team:
        return dict(team)
    return None

def get_all_teams(guild_id):
    """Get all teams in a guild"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM teams WHERE guild_id = ?", (guild_id,))
    teams = cursor.fetchall()
    conn.close()
    
    return [dict(team) for team in teams]

def add_player_to_team(guild_id, user_id, team_id, position):
    """Add a player to a team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if player exists
    cursor.execute(
        "SELECT * FROM players WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    player = cursor.fetchone()
    
    if player:
        # Update existing player
        cursor.execute(
            "UPDATE players SET team_id = ?, position = ? WHERE user_id = ? AND guild_id = ?",
            (team_id, position, user_id, guild_id)
        )
    else:
        # Create new player
        cursor.execute(
            "INSERT INTO players (user_id, guild_id, team_id, position) VALUES (?, ?, ?, ?)",
            (user_id, guild_id, team_id, position)
        )
    
    conn.commit()
    conn.close()
    return True

def remove_player_from_team(guild_id, user_id):
    """Remove a player from their team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE players SET team_id = NULL WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_team_players(guild_id, team_id):
    """Get all players in a team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM players WHERE guild_id = ? AND team_id = ?",
        (guild_id, team_id)
    )
    players = cursor.fetchall()
    conn.close()
    
    return [dict(player) for player in players]

def get_player(guild_id, user_id):
    """Get player information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM players WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    player = cursor.fetchone()
    conn.close()
    
    if player:
        return dict(player)
    return None

def update_player_stats(guild_id, user_id, goals=None, assists=None, saves=None):
    """Update player statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current player data
    cursor.execute(
        "SELECT * FROM players WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    player = cursor.fetchone()
    
    if not player:
        # Player doesn't exist, create them
        cursor.execute(
            "INSERT INTO players (user_id, guild_id, goals, assists, saves) VALUES (?, ?, ?, ?, ?)",
            (user_id, guild_id, goals or 0, assists or 0, saves or 0)
        )
    else:
        # Update existing player
        updates = []
        params = []
        
        if goals is not None:
            updates.append("goals = ?")
            params.append(goals)
        
        if assists is not None:
            updates.append("assists = ?")
            params.append(assists)
        
        if saves is not None:
            updates.append("saves = ?")
            params.append(saves)
        
        if updates:
            query = f"UPDATE players SET {', '.join(updates)} WHERE user_id = ? AND guild_id = ?"
            params.extend([user_id, guild_id])
            cursor.execute(query, params)
    
    conn.commit()
    conn.close()
    return True

def get_top_players(guild_id, limit=10):
    """Get top players based on goals + assists + saves"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT p.*, t.name as team_name, t.emoji as team_emoji
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.guild_id = ?
        ORDER BY (p.goals + p.assists + p.saves) DESC
        LIMIT ?
        """,
        (guild_id, limit)
    )
    
    players = cursor.fetchall()
    conn.close()
    
    return [dict(player) for player in players]

def update_player_balance(guild_id, user_id, amount):
    """Update player balance (add or subtract)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if player exists
    cursor.execute(
        "SELECT * FROM players WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    player = cursor.fetchone()
    
    if player:
        current_balance = player["balance"]
        new_balance = current_balance + amount
        
        # Ensure balance doesn't go negative
        if new_balance < 0:
            new_balance = 0
        
        cursor.execute(
            "UPDATE players SET balance = ? WHERE user_id = ? AND guild_id = ?",
            (new_balance, user_id, guild_id)
        )
    else:
        # Create new player with this balance
        cursor.execute(
            "INSERT INTO players (user_id, guild_id, balance) VALUES (?, ?, ?)",
            (user_id, guild_id, max(0, amount))
        )
    
    conn.commit()
    conn.close()
    return True

def update_daily_reward(guild_id, user_id):
    """Record daily reward claim"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT OR REPLACE INTO daily_rewards (user_id, guild_id, last_claimed)
        VALUES (?, ?, datetime('now'))
        """,
        (user_id, guild_id)
    )
    
    conn.commit()
    conn.close()
    return True

def get_last_daily_claim(guild_id, user_id):
    """Get the last time user claimed daily reward"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT last_claimed FROM daily_rewards WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result["last_claimed"]
    return None

def save_application(guild_id, user_id, position, goals, assists, saves, preferred_team):
    """Save a player application"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT INTO applications 
        (user_id, guild_id, position, goals, assists, saves, preferred_team)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, guild_id, position, goals, assists, saves, preferred_team)
    )
    
    application_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return application_id

def get_guild_settings(guild_id):
    """Get guild settings or create default ones"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    
    if not settings:
        # Create default settings
        cursor.execute(
            "INSERT INTO settings (guild_id, roster_cap) VALUES (?, ?)",
            (guild_id, 22)
        )
        conn.commit()
        
        cursor.execute("SELECT * FROM settings WHERE guild_id = ?", (guild_id,))
        settings = cursor.fetchone()
    
    conn.close()
    return dict(settings)

def update_guild_settings(guild_id, roster_cap=None, notification_channel_id=None, application_channel_id=None, contract_channel_id=None):
    """Update guild settings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if roster_cap is not None:
        updates.append("roster_cap = ?")
        params.append(roster_cap)
    
    if notification_channel_id is not None:
        updates.append("notification_channel_id = ?")
        params.append(notification_channel_id)
        
    if application_channel_id is not None:
        updates.append("application_channel_id = ?")
        params.append(application_channel_id)
        
    if contract_channel_id is not None:
        updates.append("contract_channel_id = ?")
        params.append(contract_channel_id)
    
    if updates:
        query = f"UPDATE settings SET {', '.join(updates)} WHERE guild_id = ?"
        params.append(guild_id)
        
        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            # Settings don't exist yet, create them
            if roster_cap is None:
                roster_cap = 22
            
            cursor.execute(
                "INSERT INTO settings (guild_id, roster_cap, notification_channel_id, application_channel_id, contract_channel_id) VALUES (?, ?, ?, ?, ?)",
                (guild_id, roster_cap, notification_channel_id, application_channel_id, contract_channel_id)
            )
    
    conn.commit()
    conn.close()
    return True

def is_team_captain(guild_id, user_id):
    """Check if a user is a captain of any team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM teams WHERE guild_id = ? AND captain_id = ?",
        (guild_id, user_id)
    )
    
    team = cursor.fetchone()
    conn.close()
    
    return team is not None

def get_team_by_captain(guild_id, user_id):
    """Get team information for a captain"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM teams WHERE guild_id = ? AND captain_id = ?",
        (guild_id, user_id)
    )
    
    team = cursor.fetchone()
    conn.close()
    
    if team:
        return dict(team)
    return None

def update_captain_role(guild_id, team_id, captain_role_id):
    """Update the captain role ID for a team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE teams SET captain_role_id = ? WHERE id = ? AND guild_id = ?",
        (captain_role_id, team_id, guild_id)
    )
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    return rows_affected > 0

def update_player_price(guild_id, user_id, price):
    """Update player price"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if player exists
    cursor.execute(
        "SELECT * FROM players WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    player = cursor.fetchone()
    
    if player:
        # Update existing player
        cursor.execute(
            "UPDATE players SET price = ? WHERE user_id = ? AND guild_id = ?",
            (price, user_id, guild_id)
        )
    else:
        # Create new player with this price
        cursor.execute(
            "INSERT INTO players (user_id, guild_id, price) VALUES (?, ?, ?)",
            (user_id, guild_id, price)
        )
    
    conn.commit()
    conn.close()
    return True

def create_player_offer(guild_id, player_id, team_id, from_captain_id, amount):
    """Create a new offer for a player"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO player_offers 
            (guild_id, player_id, team_id, from_captain_id, amount)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, player_id, team_id, from_captain_id, amount)
        )
        
        offer_id = cursor.lastrowid
        conn.commit()
        return offer_id
    except Exception as e:
        logger.error(f"Error creating player offer: {e}")
        return None
    finally:
        conn.close()

def get_player_offers(guild_id, player_id=None, team_id=None, status='pending'):
    """Get offers for a player or from a team"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM player_offers WHERE guild_id = ? AND status = ?"
    params = [guild_id, status]
    
    if player_id:
        query += " AND player_id = ?"
        params.append(player_id)
    
    if team_id:
        query += " AND team_id = ?"
        params.append(team_id)
    
    cursor.execute(query, params)
    offers = cursor.fetchall()
    conn.close()
    
    return [dict(offer) for offer in offers]

def get_offer_by_id(offer_id):
    """Get an offer by its ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM player_offers WHERE id = ?", (offer_id,))
    offer = cursor.fetchone()
    conn.close()
    
    if offer:
        return dict(offer)
    return None

def update_offer_status(offer_id, status):
    """Update status of an offer (accepted/rejected)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE player_offers SET status = ? WHERE id = ?",
        (status, offer_id)
    )
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    return rows_affected > 0
