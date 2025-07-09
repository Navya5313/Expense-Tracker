import sqlite3
import pandas as pd
import os
from datetime import date, datetime, timedelta

# -------------- Currency Conversion (Mock) --------------
def convert_to_base(amount, from_currency, to_currency):
    rates = {"INR": 1, "USD": 83, "EUR": 90, "GBP": 100}
    if from_currency == to_currency:
        return amount
    # Convert amount from from_currency to base currency
    try:
        converted_amount = amount * rates[from_currency] / rates[to_currency]
    except KeyError:
        # If currency not found, just return amount as fallback
        converted_amount = amount
    return converted_amount

# -------------- Init DBs per User --------------
def create_user_db(username):
    db_path = f"data/{username}.db"
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Core Tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            type TEXT,
            description TEXT,
            currency TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS recurring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            amount REAL,
            type TEXT,
            description TEXT,
            frequency TEXT,
            start_date TEXT,
            next_due TEXT,
            currency TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            goal REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            streak INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # Set default base currency
    c.execute("INSERT OR IGNORE INTO user_settings (key, value) VALUES ('base_currency', 'INR')")
    conn.commit()
    conn.close()

def get_connection(username):
    return sqlite3.connect(f"data/{username}.db", check_same_thread=False)

# -------------- Records --------------
def add_record(username, category, amount, record_type, description, currency):
    create_user_db(username)
    conn = get_connection(username)
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("""
        INSERT INTO records (date, category, amount, type, description, currency)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (today, category, amount, record_type, description, currency))
    conn.commit()
    conn.close()

def get_records(username):
    create_user_db(username)
    conn = get_connection(username)
    df = pd.read_sql("SELECT * FROM records ORDER BY date DESC", conn)
    conn.close()
    return df

# -------------- Recurring --------------
def add_recurring_transaction(username, category, amount, record_type, description, frequency, start_date, currency):
    conn = get_connection(username)
    c = conn.cursor()
    c.execute("""
        INSERT INTO recurring (category, amount, type, description, frequency, start_date, next_due, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (category, amount, record_type, description, frequency, start_date, start_date, currency))
    conn.commit()
    conn.close()

def process_due_recurring_transactions(username):
    conn = get_connection(username)
    c = conn.cursor()
    today = date.today()

    c.execute("SELECT * FROM recurring")
    for row in c.fetchall():
        id_, category, amount, rtype, desc, freq, start, next_due, currency = row
        next_due_date = datetime.strptime(next_due, "%Y-%m-%d").date()

        if today >= next_due_date:
            c.execute("""
                INSERT INTO records (date, category, amount, type, description, currency)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (today.isoformat(), category, amount, rtype, f"[Recurring] {desc}", currency))

            # Schedule next
            if freq == "daily":
                new_due = next_due_date + timedelta(days=1)
            elif freq == "weekly":
                new_due = next_due_date + timedelta(weeks=1)
            else:
                new_month = next_due_date.month % 12 + 1
                new_year = next_due_date.year + (next_due_date.month // 12)
                new_day = min(next_due_date.day, 28)
                new_due = date(new_year, new_month, new_day)

            c.execute("UPDATE recurring SET next_due=? WHERE id=?", (new_due.isoformat(), id_))
    conn.commit()
    conn.close()

def get_recurring_transactions(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT * FROM recurring ORDER BY next_due", conn)
    conn.close()
    return df

# -------------- Goals + Streaks --------------
def set_goal(username, goal):
    conn = get_connection(username)
    today = date.today().isoformat()
    c = conn.cursor()
    c.execute("DELETE FROM goals")
    c.execute("INSERT INTO goals (date, goal) VALUES (?, ?)", (today, goal))
    conn.commit()
    conn.close()

def get_goal(username):
    conn = get_connection(username)
    c = conn.cursor()
    c.execute("SELECT goal FROM goals ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def log_goal_history(username, goal):
    conn = get_connection(username)
    today = date.today().isoformat()
    c = conn.cursor()
    c.execute("INSERT INTO goals (date, goal) VALUES (?, ?)", (today, goal))
    conn.commit()
    conn.close()

def get_goal_history(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT date, goal FROM goals ORDER BY date", conn)
    conn.close()
    return df

def get_streak(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT date FROM goals ORDER BY date DESC", conn)
    conn.close()
    streak = 0
    today = date.today()
    for i in range(len(df)):
        d = datetime.strptime(df.iloc[i]["date"], "%Y-%m-%d").date()
        if d == today - timedelta(days=streak):
            streak += 1
        else:
            break
    return streak

def get_best_streak(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT date FROM goals ORDER BY date", conn)
    conn.close()
    best, current = 0, 0
    prev = None
    for i in range(len(df)):
        d = datetime.strptime(df.iloc[i]["date"], "%Y-%m-%d").date()
        if prev is None or d == prev + timedelta(days=1):
            current += 1
        else:
            best = max(best, current)
            current = 1
        prev = d
    return max(best, current)

def get_streak_growth(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT date FROM goals ORDER BY date", conn)
    conn.close()
    streaks, current, prev = [], 0, None
    for i in range(len(df)):
        d = datetime.strptime(df.iloc[i]["date"], "%Y-%m-%d").date()
        current = current + 1 if prev and d == prev + timedelta(days=1) else 1
        streaks.append({"Date": d, "Streak": current})
        prev = d
    return pd.DataFrame(streaks)

# -------------- Income/Expense Totals (converted) --------------
def get_base_currency(username):
    conn = get_connection(username)
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE key='base_currency'")
    val = c.fetchone()
    conn.close()
    return val[0] if val else "INR"

def get_total_income(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT amount, currency FROM records WHERE type='Income'", conn)
    conn.close()
    base = get_base_currency(username)
    return round(sum(convert_to_base(r["amount"], r["currency"], base) for _, r in df.iterrows()), 2)

def get_total_expenses(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT amount, currency FROM records WHERE type='Expense'", conn)
    conn.close()
    base = get_base_currency(username)
    return round(sum(convert_to_base(r["amount"], r["currency"], base) for _, r in df.iterrows()), 2)

# -------------- Achievements --------------
def unlock_achievement(username, name):
    conn = get_connection(username)
    c = conn.cursor()
    c.execute("SELECT * FROM achievements WHERE name=?", (name,))
    if not c.fetchone():
        c.execute("INSERT INTO achievements (name, date) VALUES (?, ?)", (name, date.today().isoformat()))
    conn.commit()
    conn.close()

def get_achievements(username):
    conn = get_connection(username)
    df = pd.read_sql("SELECT name, date FROM achievements ORDER BY date", conn)
    conn.close()
    return df

# -------------- Budget Prediction --------------
def get_monthly_spending_by_category(username):
    conn = get_connection(username)
    df = pd.read_sql("""
        SELECT strftime('%Y-%m', date) AS month, category, amount, currency
        FROM records
        WHERE type='Expense'
    """, conn)
    base = get_base_currency(username)
    df["converted"] = df.apply(lambda r: float(convert_to_base(float(r["amount"]), r["currency"], base)), axis=1)
    pivot = df.groupby(["month", "category"])["converted"].sum().unstack(fill_value=0)
    conn.close()
    return pivot.tail(6)  # Last 6 months

def set_base_currency(username, currency):
    conn = get_connection(username)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_settings (key, value) 
        VALUES ('base_currency', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (currency,))
    conn.commit()
    conn.close()

