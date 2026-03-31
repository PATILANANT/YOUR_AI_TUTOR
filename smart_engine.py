def analyze_performance(profile):
    progress = profile.get("progress", {})
    weak_topics = profile.get("weak_topics", {})

    if not progress:
        return {
            "status": "start",
            "message": "Start learning by asking a topic."
        }

    scores = list(progress.values())
    avg_score = sum(scores) / len(scores)

    return {
        "avg_score": avg_score,
        "weak_topics": list(set(weak_topics)),
        "total_topics": len(progress)
    }


def suggest_next_action(profile):
    analysis = analyze_performance(profile)

    if analysis.get("status") == "start":
        return "Ask your first question to begin learning."

    weak = analysis["weak_topics"]
    syllabus = profile.get("syllabus", [])
    progress = profile.get("progress", {})

    # 🔥 PRIORITY 1: Weak Topic Revision
    if weak:
        return f"🔁 Revise weak topic: {weak[-1]}"

    # 🔥 PRIORITY 2: Next Topic from Syllabus
    remaining = [t for t in syllabus if t not in progress]

    if remaining:
        return f"📘 Next topic to learn: {remaining[0]}"

    # 🔥 PRIORITY 3: Advanced Suggestion
    return "🚀 You completed syllabus! Try advanced questions."