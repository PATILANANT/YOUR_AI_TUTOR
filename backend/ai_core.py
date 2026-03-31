# ========= AI CORE ENGINE =========

from config import model

# -------------------------------
# 1. STANDARD RESPONSE SCHEMA
# -------------------------------

def format_response(plan, teaching, quiz, topic, difficulty, target):
    return {
        "plan": plan,
        "teaching": teaching,
        "quiz": quiz,
        "metadata": {
            "topic": topic,
            "difficulty": difficulty,
            "target": target
        }
    }


# -------------------------------
# 2. DIFFICULTY ENGINE
# -------------------------------

def get_difficulty(profile, topic):
    progress = profile.get("progress", {})

    if topic not in progress:
        return "Beginner"

    score = progress[topic]

    if score <= 1:
        return "Beginner"
    elif score == 2:
        return "Intermediate"
    else:
        return "Advanced"


# -------------------------------
# 3. WEAK TOPIC TRACKING
# -------------------------------

def update_weak_topics(profile, topic, score, total):
    if "weak_topics" not in profile:
        profile["weak_topics"] = {}

    if score < total:
        profile["weak_topics"][topic] = profile["weak_topics"].get(topic, 0) + 1


# -------------------------------
# 4. DECISION ENGINE (BRAIN)
# -------------------------------

def decision_engine(profile, topic):
    weak = profile.get("weak_topics", {})
    syllabus = profile.get("syllabus", [])
    progress = profile.get("progress", {})

    # Priority 1 → Weak topic
    if topic in weak:
        return "revise"

    # Priority 2 → New topic
    remaining = [t for t in syllabus if t not in progress]
    if remaining:
        return "learn"

    # Priority 3 → Advanced
    return "advance"


# -------------------------------
# 5. AGENT SYSTEM (REUSABLE)
# -------------------------------

def run_agent(topic, profile, target, style):
    difficulty = get_difficulty(profile, topic)

    # PLAN
    plan = model.generate_content(
        f"Break topic into steps ({difficulty} level):\n{topic}"
    ).text

    # TEACH
    teaching = model.generate_content(
        f"""
Teach this topic for {target} exam.
Style: {style}
Difficulty: {difficulty}

Topic:
{topic}
"""
    ).text

    # QUIZ
    quiz = model.generate_content(
        f"""
Generate 8 to 12 MCQs as per the topic and target exam.

STRICT RULES:
- Each question MUST be on NEW LINE
- Use this format ONLY:

Q1|Question|a) option|b) option|c) option|d) option|c
Q2|Question|a) option|b) option|c) option|d) option|b
Q3|Question|a) option|b) option|c) option|d) option|a

DO NOT ADD ANY EXTRA TEXT.




Difficulty: {difficulty}

Topic:
{topic}
"""
    ).text

    return format_response(plan, teaching, quiz, topic, difficulty, target)


# -------------------------------
# 6. QUIZ EVALUATION
# -------------------------------

def evaluate_quiz(questions, answers, profile, topic):
    score = 0

    for i, q in enumerate(questions):
        if answers[i] and answers[i][0].lower() == q["answer"]:
            score += 1

    # Update progress
    profile["progress"][topic] = score

    # Update weak topics
    update_weak_topics(profile, topic, score, len(questions))

    return score


# -------------------------------
# 7. SMART SUGGESTION ENGINE
# -------------------------------

def suggest_next(profile):
    progress = profile.get("progress", {})
    weak = profile.get("weak_topics", {})
    syllabus = profile.get("syllabus", [])

    if not progress:
        return "Start learning by asking a topic."

    # Weak topic priority
    if weak:
        weakest = max(weak, key=weak.get)
        return f"🔁 Revise weak topic: {weakest}"

    # Next topic
    remaining = [t for t in syllabus if t not in progress]
    if remaining:
        return f"📘 Next topic: {remaining[0]}"

    return "🚀 Try advanced questions!"