# ========= TOPIC MASTERY & ADAPTIVE LEARNING ENGINE =========
# Tracks per-concept mastery scores, generates personalized quiz feedback,
# and provides proactive learning suggestions.

import json
from datetime import datetime, timedelta
from database import get_connection


# ---------------------------------------------------
# 1. DATABASE SETUP
# ---------------------------------------------------

def create_mastery_tables():
    """Create the topic_mastery table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topic_mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        concept TEXT NOT NULL,
        score REAL DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        last_tested TEXT,
        last_failed TEXT,
        mastery_level TEXT DEFAULT 'unlearned',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, concept)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        concept TEXT NOT NULL,
        score REAL DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        last_tested TEXT,
        last_failed TEXT,
        mastery_level TEXT DEFAULT 'unlearned',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(conversation_id, concept)
    )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------
# 2. MASTERY CRUD OPERATIONS
# ---------------------------------------------------

def get_user_mastery(user_id: int) -> list:
    """Get all mastery records for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM topic_mastery WHERE user_id=? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_concept_mastery(user_id: int, concept: str) -> dict:
    """Get mastery data for a specific concept."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM topic_mastery WHERE user_id=? AND concept=? COLLATE NOCASE",
        (user_id, concept.lower())
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_mastery(user_id: int, concept: str, is_correct: bool):
    """
    Update mastery score for a concept based on quiz performance.
    Uses an exponential moving average for smooth scoring.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    concept_lower = concept.lower().strip()

    # Check if record exists
    cursor.execute(
        "SELECT * FROM topic_mastery WHERE user_id=? AND concept=?",
        (user_id, concept_lower)
    )
    existing = cursor.fetchone()

    if existing:
        existing = dict(existing)
        attempts = existing["attempts"] + 1
        correct = existing["correct_count"] + (1 if is_correct else 0)
        # Exponential moving average: recent performance weighted more
        old_score = existing["score"]
        new_score = old_score * 0.7 + (100 if is_correct else 0) * 0.3
        new_score = min(100, max(0, new_score))

        # Determine mastery level
        level = _calculate_level(new_score, attempts)

        if not is_correct:
            cursor.execute("""
                UPDATE topic_mastery 
                SET score=?, attempts=?, correct_count=?, last_tested=?,
                    mastery_level=?, updated_at=?, last_failed=?
                WHERE user_id=? AND concept=?
            """, (new_score, attempts, correct, now, level, now, now,
                  user_id, concept_lower))
        else:
            cursor.execute("""
                UPDATE topic_mastery 
                SET score=?, attempts=?, correct_count=?, last_tested=?,
                    mastery_level=?, updated_at=?
                WHERE user_id=? AND concept=?
            """, (new_score, attempts, correct, now, level, now,
                  user_id, concept_lower))
    else:
        score = 100 if is_correct else 0
        level = _calculate_level(score, 1)
        cursor.execute("""
            INSERT INTO topic_mastery 
            (user_id, concept, score, attempts, correct_count, last_tested,
             last_failed, mastery_level, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, concept_lower, score,
            1 if is_correct else 0,
            now,
            None if is_correct else now,
            level, now, now
        ))

    conn.commit()
    conn.close()


def batch_update_mastery(user_id: int, results: list, conversation_id: int = None):
    """
    Update mastery for multiple concepts at once.
    results: list of {"concept": str, "is_correct": bool}
    If conversation_id is provided, also updates per-conversation mastery.
    """
    for item in results:
        update_mastery(user_id, item["concept"], item["is_correct"])
        if conversation_id:
            update_conversation_mastery(conversation_id, user_id, item["concept"], item["is_correct"])


def _calculate_level(score: float, attempts: int) -> str:
    """Determine mastery level from score and attempts."""
    if attempts == 0:
        return "unlearned"
    if score >= 85:
        return "mastered"
    elif score >= 60:
        return "proficient"
    elif score >= 35:
        return "developing"
    else:
        return "struggling"


# ---------------------------------------------------
# 3. WEAK TOPICS & PROACTIVE SUGGESTIONS
# ---------------------------------------------------

def get_weak_concepts(user_id: int, limit: int = 5) -> list:
    """Get the weakest concepts for a user (lowest scores with attempts)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT concept, score, attempts, last_tested, last_failed, mastery_level
        FROM topic_mastery 
        WHERE user_id=? AND attempts > 0 AND score < 60
        ORDER BY score ASC
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stale_concepts(user_id: int, days: int = 3, limit: int = 5) -> list:
    """
    Get concepts that haven't been reviewed recently (Spaced Repetition hint).
    Returns concepts mastered more than `days` ago that might need review.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cursor.execute("""
        SELECT concept, score, attempts, last_tested, mastery_level
        FROM topic_mastery
        WHERE user_id=? AND score >= 60 AND last_tested < ?
        ORDER BY last_tested ASC
        LIMIT ?
    """, (user_id, cutoff, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_proactive_message(user_id: int, current_topic: str) -> str:
    """
    Generate a proactive message about weak/stale concepts.
    Called before the AI teaches a new topic.
    """
    weak = get_weak_concepts(user_id, limit=3)
    stale = get_stale_concepts(user_id, days=3, limit=2)

    messages = []

    if weak:
        weak_names = [w["concept"].title() for w in weak[:2]]
        weak_str = " and ".join(weak_names)
        messages.append(
            f"📌 I noticed you had some trouble with **{weak_str}** recently. "
            f"Would you like to clear that up before we dive into '{current_topic}'?"
        )

    if stale:
        stale_names = [s["concept"].title() for s in stale[:2]]
        stale_str = ", ".join(stale_names)
        messages.append(
            f"🔄 It's been a while since you reviewed **{stale_str}**. "
            f"A quick refresher might help reinforce your understanding!"
        )

    return "\n\n".join(messages) if messages else ""


# ---------------------------------------------------
# 4. MASTERY STATISTICS
# ---------------------------------------------------

def get_mastery_summary(user_id: int) -> dict:
    """Get a summary of the user's overall mastery stats."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_concepts,
            AVG(score) as avg_score,
            SUM(CASE WHEN mastery_level = 'mastered' THEN 1 ELSE 0 END) as mastered_count,
            SUM(CASE WHEN mastery_level = 'proficient' THEN 1 ELSE 0 END) as proficient_count,
            SUM(CASE WHEN mastery_level = 'developing' THEN 1 ELSE 0 END) as developing_count,
            SUM(CASE WHEN mastery_level = 'struggling' THEN 1 ELSE 0 END) as struggling_count,
            SUM(attempts) as total_attempts
        FROM topic_mastery
        WHERE user_id=? AND attempts > 0
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row or row["total_concepts"] == 0:
        return {
            "total_concepts": 0,
            "avg_score": 0,
            "mastered": 0,
            "proficient": 0,
            "developing": 0,
            "struggling": 0,
            "total_attempts": 0
        }

    return {
        "total_concepts": row["total_concepts"],
        "avg_score": round(row["avg_score"] or 0, 1),
        "mastered": row["mastered_count"] or 0,
        "proficient": row["proficient_count"] or 0,
        "developing": row["developing_count"] or 0,
        "struggling": row["struggling_count"] or 0,
        "total_attempts": row["total_attempts"] or 0
    }


def extract_concepts_from_quiz(questions: list, topic: str) -> list:
    """
    Extract concept names from quiz questions for mastery tracking.
    Uses the topic + individual question keywords.
    """
    concepts = [topic.lower().strip()]

    # Also try to extract sub-concepts from question text
    from config import client, MODEL_NAME

    try:
        q_texts = [q.get("question", "") for q in questions[:5]]
        prompt = f"""From these quiz questions about "{topic}", extract the specific sub-concepts being tested.
Return ONLY a JSON array of concept strings (max 8 concepts).

Questions:
{chr(10).join(q_texts)}

Example output: ["photosynthesis", "chlorophyll", "light reaction"]"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        if raw.startswith("json"):
            raw = raw[4:]

        sub_concepts = json.loads(raw.strip())
        if isinstance(sub_concepts, list):
            concepts.extend([c.lower().strip() for c in sub_concepts if isinstance(c, str)])
    except Exception:
        pass

    return list(set(concepts))


# ---------------------------------------------------
# 5. PER-CONVERSATION MASTERY
# ---------------------------------------------------

def update_conversation_mastery(conversation_id: int, user_id: int, concept: str, is_correct: bool):
    """Update mastery score for a concept within a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    concept_lower = concept.lower().strip()

    cursor.execute(
        "SELECT * FROM conversation_mastery WHERE conversation_id=? AND concept=?",
        (conversation_id, concept_lower)
    )
    existing = cursor.fetchone()

    if existing:
        existing = dict(existing)
        attempts = existing["attempts"] + 1
        correct = existing["correct_count"] + (1 if is_correct else 0)
        old_score = existing["score"]
        new_score = old_score * 0.7 + (100 if is_correct else 0) * 0.3
        new_score = min(100, max(0, new_score))
        level = _calculate_level(new_score, attempts)

        if not is_correct:
            cursor.execute("""
                UPDATE conversation_mastery
                SET score=?, attempts=?, correct_count=?, last_tested=?,
                    mastery_level=?, updated_at=?, last_failed=?
                WHERE conversation_id=? AND concept=?
            """, (new_score, attempts, correct, now, level, now, now,
                  conversation_id, concept_lower))
        else:
            cursor.execute("""
                UPDATE conversation_mastery
                SET score=?, attempts=?, correct_count=?, last_tested=?,
                    mastery_level=?, updated_at=?
                WHERE conversation_id=? AND concept=?
            """, (new_score, attempts, correct, now, level, now,
                  conversation_id, concept_lower))
    else:
        score = 100 if is_correct else 0
        level = _calculate_level(score, 1)
        cursor.execute("""
            INSERT INTO conversation_mastery
            (conversation_id, user_id, concept, score, attempts, correct_count,
             last_tested, last_failed, mastery_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id, user_id, concept_lower, score,
            1 if is_correct else 0,
            now,
            None if is_correct else now,
            level, now, now
        ))

    conn.commit()
    conn.close()


def get_conversation_mastery(conversation_id: int) -> list:
    """Get all mastery records for a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM conversation_mastery WHERE conversation_id=? ORDER BY updated_at DESC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_conversation_mastery_summary(conversation_id: int) -> dict:
    """Get mastery summary for a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total_concepts,
            AVG(score) as avg_score,
            SUM(CASE WHEN mastery_level = 'mastered' THEN 1 ELSE 0 END) as mastered_count,
            SUM(CASE WHEN mastery_level = 'proficient' THEN 1 ELSE 0 END) as proficient_count,
            SUM(CASE WHEN mastery_level = 'developing' THEN 1 ELSE 0 END) as developing_count,
            SUM(CASE WHEN mastery_level = 'struggling' THEN 1 ELSE 0 END) as struggling_count,
            SUM(attempts) as total_attempts
        FROM conversation_mastery
        WHERE conversation_id=? AND attempts > 0
    """, (conversation_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row["total_concepts"] == 0:
        return {
            "total_concepts": 0,
            "avg_score": 0,
            "mastered": 0,
            "proficient": 0,
            "developing": 0,
            "struggling": 0,
            "total_attempts": 0
        }

    return {
        "total_concepts": row["total_concepts"],
        "avg_score": round(row["avg_score"] or 0, 1),
        "mastered": row["mastered_count"] or 0,
        "proficient": row["proficient_count"] or 0,
        "developing": row["developing_count"] or 0,
        "struggling": row["struggling_count"] or 0,
        "total_attempts": row["total_attempts"] or 0
    }
