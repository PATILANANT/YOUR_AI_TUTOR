import sqlite3
import json
from datetime import datetime
import os

# Database Path
DB_PATH = "users.db"

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Seeding Dummy Test Data ---")

    # 1. Create Dummy User
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("test_user", "password123"))
        user_id = cursor.lastrowid
        print(f"Created User: test_user (ID: {user_id})")
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM users WHERE username='test_user'")
        user_id = cursor.fetchone()[0]
        print(f"User 'test_user' already exists (ID: {user_id})")

    # 2. Create Dummy Profile with a Weak Topic
    # We will pretend the user failed "Photosynthesis"
    profile_data = {
        "user_id": user_id,
        "goal": "UPSC",
        "progress": json.dumps({"Biology": 4, "Physics": 8}),
        "weak_topics": json.dumps({"Photosynthesis": 3}) # High error count
    }

    cursor.execute("""
        INSERT OR REPLACE INTO profiles (user_id, goal, progress, weak_topics)
        VALUES (?, ?, ?, ?)
    """, (user_id, profile_data["goal"], profile_data["progress"], profile_data["weak_topics"]))
    print("Created Profile with Weak Topic: 'Photosynthesis'")

    # 3. Create a Dummy Conversation
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO conversations (user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, "Testing Mastery System", now, now))
    conv_id = cursor.lastrowid
    print(f"Created Conversation: 'Testing Mastery System' (ID: {conv_id})")

    # 4. Add Dummy Messages
    messages = [
        ("user", "Can you explain how plants make food?"),
        ("assistant", "Sure! Plants use a process called Photosynthesis... [Long explanation]"),
        ("user", "I didn't quite get the Chlorophyll part."),
        ("assistant", "No problem! Chlorophyll is the green pigment that absorbs light..."),
    ]

    for role, content in messages:
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (conv_id, role, content, datetime.utcnow().isoformat()))
    
    print(f"Added {len(messages)} dummy messages to the chat history.")

    conn.commit()
    conn.close()
    print("\n--- Seeding Complete! ---")
    print("Login with: \nUsername: test_user \nPassword: password123")

if __name__ == "__main__":
    seed_data()
