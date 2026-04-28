import sqlite3
import json
from datetime import datetime

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'New Chat',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        goal TEXT,
        syllabus TEXT DEFAULT '[]',
        progress TEXT DEFAULT '{}',
        weak_topics TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


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


# ============================================================
# Conversation CRUD
# ============================================================

def create_conversation(user_id, title="New Chat"):
    """Create a new conversation and return its id."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, title, now, now)
    )
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conv_id


def get_conversations(user_id):
    """Return all conversations for a user, newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id=? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def rename_conversation(conv_id, user_id, new_title):
    """Rename a conversation (only if owned by user)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title=?, updated_at=? WHERE id=? AND user_id=?",
        (new_title, datetime.utcnow().isoformat(), conv_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_conversation(conv_id, user_id):
    """Delete a conversation and its messages (only if owned by user)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Delete messages first
    cursor.execute(
        "DELETE FROM messages WHERE conversation_id=? AND conversation_id IN (SELECT id FROM conversations WHERE user_id=?)",
        (conv_id, user_id)
    )
    cursor.execute(
        "DELETE FROM conversations WHERE id=? AND user_id=?",
        (conv_id, user_id)
    )
    conn.commit()
    conn.close()


# ============================================================
# Message CRUD
# ============================================================

def add_message(conversation_id, role, content):
    """Add a message to a conversation and touch updated_at."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now)
    )
    # Touch the conversation's updated_at
    cursor.execute(
        "UPDATE conversations SET updated_at=? WHERE id=?",
        (now, conversation_id)
    )
    conn.commit()
    conn.close()


def get_messages(conversation_id):
    """Return all messages in a conversation, oldest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content, created_at FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# Conversation Profile CRUD
# ============================================================

def save_conversation_profile(conversation_id, user_id, profile):
    """Save or update a profile scoped to a conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "SELECT id FROM conversation_profiles WHERE conversation_id=?",
        (conversation_id,)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE conversation_profiles
            SET goal=?, syllabus=?, progress=?, weak_topics=?, updated_at=?
            WHERE conversation_id=?
        """, (
            profile.get("goal"),
            json.dumps(profile.get("syllabus", [])),
            json.dumps(profile.get("progress", {})),
            json.dumps(profile.get("weak_topics", {})),
            now,
            conversation_id
        ))
    else:
        cursor.execute("""
            INSERT INTO conversation_profiles
            (conversation_id, user_id, goal, syllabus, progress, weak_topics, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            user_id,
            profile.get("goal"),
            json.dumps(profile.get("syllabus", [])),
            json.dumps(profile.get("progress", {})),
            json.dumps(profile.get("weak_topics", {})),
            now, now
        ))

    conn.commit()
    conn.close()


def load_conversation_profile(conversation_id):
    """Load the profile for a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM conversation_profiles WHERE conversation_id=?",
        (conversation_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "goal": None,
            "syllabus": [],
            "progress": {},
            "weak_topics": {}
        }

    return {
        "goal": row["goal"],
        "syllabus": json.loads(row["syllabus"] or "[]"),
        "progress": json.loads(row["progress"] or "{}"),
        "weak_topics": json.loads(row["weak_topics"] or "{}")
    }


def delete_conversation_profile(conversation_id):
    """Delete the profile for a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM conversation_profiles WHERE conversation_id=?",
        (conversation_id,)
    )
    conn.commit()
    conn.close()


def get_user_conversation_profiles(user_id):
    """Get all conversations with their profiles for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.title, c.created_at, c.updated_at,
               cp.goal, cp.syllabus, cp.progress, cp.weak_topics
        FROM conversations c
        LEFT JOIN conversation_profiles cp ON c.id = cp.conversation_id
        WHERE c.user_id = ?
        ORDER BY c.updated_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "profile": {
                "goal": r["goal"],
                "syllabus": json.loads(r["syllabus"] or "[]") if r["syllabus"] else [],
                "progress": json.loads(r["progress"] or "{}") if r["progress"] else {},
                "weak_topics": json.loads(r["weak_topics"] or "{}") if r["weak_topics"] else {}
            }
        })
    return result