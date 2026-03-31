import sqlite3

def get_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    goal TEXT,
    progress TEXT,
    weak_topics TEXT
)
""")
    



    conn.commit()
    conn.close()


import json

def save_profile(user_id, profile):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO profiles (user_id, goal, progress, weak_topics)
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        profile.get("goal"),
        json.dumps(profile.get("progress", {})),
        json.dumps(profile.get("weak_topics", {}))
    ))

    conn.commit()
    conn.close()


def load_profile(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM profiles WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "goal": None,
            "progress": {},
            "weak_topics": {}
        }

    return {
        "goal": row["goal"],
        "progress": json.loads(row["progress"] or "{}"),
        "weak_topics": json.loads(row["weak_topics"] or "{}")
    }