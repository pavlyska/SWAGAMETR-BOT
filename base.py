import sqlite3
import string
import random

def init_db():
    conn = sqlite3.connect('swag_boti.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        swag INTEGER DEFAULT 0,
        total_swag INTEGER DEFAULT 0,
        rank TEXT DEFAULT 'Нуб 👶',
        league TEXT DEFAULT 'Лига Нормисов 🏅',
        registration_date TEXT,
        multiplier INTEGER DEFAULT 1,
        is_premium INTEGER DEFAULT 0,
        premium_end_date TEXT,
        gif_id TEXT,
        selected_badge TEXT,
        hide_top INTEGER DEFAULT 0,
        manual_farm_collection INTEGER DEFAULT 0,
        disable_farm_notifications INTEGER DEFAULT 0,
        use_clan_multiplier INTEGER DEFAULT 0,
        wallet_id TEXT  -- Без UNIQUE при создании
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS roulette_bets (
       bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
       user_id INTEGER NOT NULL,
       chat_id INTEGER NOT NULL,
       amount INTEGER NOT NULL,
       result TEXT NOT NULL,  -- "loss", "x1", "x2", "x5"
       bet_date TEXT NOT NULL,
       FOREIGN KEY(user_id) REFERENCES users(user_id)
   )
   ''')
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        gift_name TEXT NOT NULL,
        received_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')
    conn.commit()

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "wallet_id" not in columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN wallet_id TEXT")  
            conn.commit()
            print("Столбец wallet_id успешно добавлен в таблицу users.")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при добавлении столбца wallet_id: {e}")

    cursor.execute("SELECT user_id, wallet_id FROM users WHERE wallet_id IS NULL")
    users_without_wallet = cursor.fetchall()
    for user_id, _ in users_without_wallet:
        wallet_id = generate_wallet_id()
        cursor.execute("UPDATE users SET wallet_id = ? WHERE user_id = ?", (wallet_id, user_id))
    conn.commit()

    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_id ON users(wallet_id)")
        conn.commit()
        print("Уникальный индекс для wallet_id успешно создан.")
    except sqlite3.OperationalError as e:
        print(f"Ошибка при создании уникального индекса для wallet_id: {e}")

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "manual_farm_collection" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN manual_farm_collection INTEGER DEFAULT 0")
    if "disable_farm_notifications" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN disable_farm_notifications INTEGER DEFAULT 0")
    if "use_clan_multiplier" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN use_clan_multiplier INTEGER DEFAULT 0")
    if "first_name" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    if "is_premium" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
    if "premium_end_date" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN premium_end_date TEXT")
    if "gif_id" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN gif_id TEXT")
    if "selected_badge" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN selected_badge TEXT")
    if "hide_top" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN hide_top INTEGER DEFAULT 0")

    if "duel_wins" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN duel_wins INTEGER DEFAULT 0")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS farms (
        user_id INTEGER,
        farm_type TEXT,
        quantity INTEGER,
        clan_connected INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS multipliers (
        user_id INTEGER,
        multiplier INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_tokens (
        user_id INTEGER PRIMARY KEY,
        token TEXT UNIQUE,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dg_burn (
        burn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        burn_date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clans (
        clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_name TEXT UNIQUE NOT NULL,
        balance INTEGER DEFAULT 0,
        multiplier INTEGER DEFAULT 1,
        owner_id INTEGER,
        FOREIGN KEY(owner_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS swag_towers (
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        height REAL DEFAULT 0.0,
        last_used TEXT DEFAULT NULL,  -- Время последнего использования команды
        PRIMARY KEY (user_id, chat_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS premium_api_keys (
        key TEXT PRIMARY KEY,
        created_by INTEGER,  -- ID админа, который создал ключ
        created_at TEXT,     -- Дата создания
        used_by INTEGER DEFAULT NULL,  -- ID пользователя, который использовал ключ
        used_at TEXT DEFAULT NULL,     -- Дата использования
        days INTEGER DEFAULT 30        -- Срок действия премиума в днях
    )
    ''')
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dg_burn_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_burned REAL DEFAULT 0.0
    )
    ''')

    cursor.execute("SELECT * FROM dg_burn_stats")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO dg_burn_stats (total_burned) VALUES (0.0)")
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS crypto_emission (
        crypto_type TEXT PRIMARY KEY,
        total_amount REAL DEFAULT 0.0
    )
    ''')

    cursor.execute('SELECT COUNT(*) FROM crypto_emission')
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute('INSERT INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("BL", 0.0))
        cursor.execute('INSERT INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("DP", 0.0))
        cursor.execute('INSERT INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("DG", 0.0))
        cursor.execute('INSERT INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("LK", 21000000000.0))  
        conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS crypto_rates (
        crypto_type TEXT PRIMARY KEY,
        rate REAL DEFAULT 0.0
    )
    ''')
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM crypto_rates')
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute('INSERT INTO crypto_rates (crypto_type, rate) VALUES (:bl, :bl_rate)', {'bl': "BL", 'bl_rate': 88000})
        cursor.execute('INSERT INTO crypto_rates (crypto_type, rate) VALUES (:dp, :dp_rate)', {'dp': "DP", 'dp_rate': 3610})
        cursor.execute('INSERT INTO crypto_rates (crypto_type, rate) VALUES (:dg, :dg_rate)', {'dg': "DG", 'dg_rate': 0.1})
        cursor.execute('INSERT INTO crypto_rates (crypto_type, rate) VALUES (:lk, :lk_rate)', {'lk': "LK", 'lk_rate': 1000})  
        conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_badges (
        user_id INTEGER,
        badge TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        PRIMARY KEY(user_id, badge)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clan_members (
        user_id INTEGER,
        clan_id INTEGER,
        FOREIGN KEY (clan_id) REFERENCES clans(clan_id),
        PRIMARY KEY (user_id, clan_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS premium_payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        status TEXT DEFAULT 'pending',
        payment_date TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS premium_subscriptions (
        user_id INTEGER PRIMARY KEY,
        start_date TEXT,
        end_date TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS duel_searches (
        user_id INTEGER PRIMARY KEY,
        bet INTEGER,
        search_start_time TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_duels (
        duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER,
        player2_id INTEGER,
        bet INTEGER,
        status TEXT DEFAULT 'active',
        winner_id INTEGER,
        FOREIGN KEY(player1_id) REFERENCES users(user_id),
        FOREIGN KEY(player2_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lk_trading (
        trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        trade_type TEXT,  -- "buy" или "sell"
        amount REAL,
        swag_amount REAL,
        trade_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('SELECT COUNT(*) FROM crypto_emission WHERE crypto_type = "LK"')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("LK", 21000000000.0))

    cursor.execute('SELECT COUNT(*) FROM crypto_rates WHERE crypto_type = "LK"')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO crypto_rates (crypto_type, rate) VALUES (?, ?)', ("LK", 1000))

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS crypto_wallets (
        user_id INTEGER,
        crypto_type TEXT,
        amount REAL DEFAULT 0.0,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        PRIMARY KEY(user_id, crypto_type)
    )
    ''')

    conn.commit()
    return conn, cursor

conn, cursor = init_db()

cursor.execute("PRAGMA table_info(farms)")
columns = [col[1] for col in cursor.fetchall()]
if "last_income" not in columns:
    cursor.execute("ALTER TABLE farms ADD COLUMN last_income TEXT DEFAULT '2024-01-01 00:00:00'")
    conn.commit()
    print("[INFO] Столбец 'last_income' добавлен в таблицу farms.")

def init_crypto_emission():
    cursor.execute('INSERT OR IGNORE INTO crypto_emission (crypto_type, total_amount) VALUES (?, ?)', ("DG", 0.0))
    conn.commit()

init_crypto_emission()  

cursor.execute("PRAGMA table_info(clans)")
columns = [col[1] for col in cursor.fetchall()]
if "clan_description" not in columns:
    cursor.execute("ALTER TABLE clans ADD COLUMN clan_description TEXT DEFAULT NULL")
    conn.commit()
    print("Столбец clan_description успешно добавлен в таблицу clans.")

def generate_wallet_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(24))