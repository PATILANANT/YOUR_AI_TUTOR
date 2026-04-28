# ========= AI CORE ENGINE =========

from config import client, MODEL_NAME


# -------------------------------
# 0. CONTEXT BUILDER
# -------------------------------

def build_context_prompt(chat_history=None, profile=None, max_history=20):
    """Build a rich context string from chat history and profile data."""
    parts = []

    # --- Profile context ---
    if profile:
        goal = profile.get("goal")
        syllabus = profile.get("syllabus", [])
        progress = profile.get("progress", {})
        weak_topics = profile.get("weak_topics", {})

        if goal:
            parts.append(f"🎯 Student's Goal: {goal}")

        if syllabus and any(syllabus):
            covered = [t for t in syllabus if t in progress]
            remaining = [t for t in syllabus if t not in progress]
            parts.append(f"📚 Syllabus ({len(syllabus)} topics): {', '.join(syllabus)}")
            if covered:
                parts.append(f"  ✅ Covered: {', '.join(covered)}")
            if remaining:
                parts.append(f"  📋 Remaining: {', '.join(remaining)}")

        if progress:
            prog_str = ', '.join([f"{t}: {s} pts" for t, s in progress.items()])
            parts.append(f"📈 Progress: {prog_str}")

        if weak_topics:
            weak_str = ', '.join([f"{t} ({c} errors)" for t, c in weak_topics.items()])
            parts.append(f"⚠️ Weak Topics: {weak_str}")

    # --- Chat history ---
    if chat_history and len(chat_history) > 0:
        recent = chat_history[-max_history:]  # Keep last N messages
        history_lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Truncate very long messages to keep prompt manageable
            if len(content) > 500:
                content = content[:500] + "...[truncated]"
            label = "Student" if role == "user" else "Tutor"
            history_lines.append(f"{label}: {content}")
        parts.append(f"\n💬 Recent Chat History:\n" + "\n".join(history_lines))

    if not parts:
        return ""

    return "\n".join([
        "="*50,
        "STUDENT CONTEXT (use this to personalize your response)",
        "="*50,
        *parts,
        "="*50,
        ""
    ])

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

def _generate(prompt: str) -> str:
    """Helper: calls the new google.genai client."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text


def run_agent(topic, profile, target, style, chat_history=None):
    difficulty = get_difficulty(profile, topic)
    weak = profile.get("weak_topics", {})
    
    # Build rich context from chat history and profile
    context = build_context_prompt(chat_history, profile)
    
    # PROACTIVE MESSAGE (if user has weak topics)
    proactive_intro = ""
    if weak:
        # Sort by most errors
        sorted_weak = sorted(weak.items(), key=lambda x: x[1], reverse=True)
        top_weak = sorted_weak[0][0]
        proactive_intro = f"\n[AI Note: I noticed you had some trouble with '{top_weak}' recently. Would you like to clear that up before we start with '{topic}'?]\n\n"

    # PLAN
    plan_prompt = f"""{context}You are an expert AI tutor. Break this topic into clear learning steps at {difficulty} level.
If the student has been discussing related topics in chat history, connect the steps to what they already know.

Topic: {topic}"""
    plan = _generate(plan_prompt)

    # TEACH
    teaching_prompt = f"""{context}You are an expert AI tutor. Teach this topic thoroughly.

IMPORTANT:
- Target Exam: {target}
- Teaching Style: {style}
- Difficulty Level: {difficulty}
- If chat history shows the student asked about related topics, reference and connect them.
- If the student has weak topics, briefly reinforce those concepts where relevant.
- If the student has a syllabus, show how this topic fits into their learning path.

Topic: {topic}"""
    
    if proactive_intro:
        teaching_prompt = f"Note about past struggles: {proactive_intro}\n\n" + teaching_prompt

    teaching = _generate(teaching_prompt)

    # Add the intro to the final teaching text so the user sees it
    if proactive_intro:
        teaching = proactive_intro + teaching

    # QUIZ
    quiz = _generate(
        f"""{context}Generate 8 to 12 MCQs as per the topic and target exam.

STRICT RULES:
- Each question MUST be on NEW LINE
- Use this format ONLY:

Q1|Question|a) option|b) option|c) option|d) option|c
Q2|Question|a) option|b) option|c) option|d) option|b
Q3|Question|a) option|b) option|c) option|d) option|a

DO NOT ADD ANY EXTRA TEXT.
- If the student has weak topics, include 2-3 questions that test those weak areas.
- Adjust question difficulty based on the student's progress.

Difficulty: {difficulty}

Topic:
{topic}"""
    )

    return format_response(plan, teaching, quiz, topic, difficulty, target)


# -------------------------------
# 6. QUIZ EVALUATION
# -------------------------------

def evaluate_quiz(questions, answers, profile, topic):

    score = 0
    total = len(questions)

    for i, q in enumerate(questions):
        correct = q["answer"]

        # SAFE CHECK
        if i < len(answers) and answers[i] and answers[i][0].lower() == correct:
            score += 1

    # UPDATE PROGRESS
    if "progress" not in profile:
        profile["progress"] = {}
    profile["progress"][topic] = score

    # UPDATE WEAK TOPICS (If score is less than 70%)
    if total > 0 and (score / total) < 0.7:
        update_weak_topics(profile, topic, score, total)
    else:
        # If they did well, remove it from weak topics if it was there
        if "weak_topics" in profile and topic in profile["weak_topics"]:
            del profile["weak_topics"][topic]

    return score, profile   


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