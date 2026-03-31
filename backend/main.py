from fastapi import FastAPI
# from ai_core import run_agent, evaluate_quiz, suggest_next
from ai_core import run_agent, evaluate_quiz, suggest_next

from schemas import AgentRequest, EvaluateRequest, SuggestRequest

app = FastAPI()

# ===============================
# 1. AGENT ENDPOINT
# ===============================
@app.post("/agent")
def agent_api(data: AgentRequest):

    result = run_agent(
        data.topic,
        data.profile,
        data.target,
        data.style
    )

    return result


# ===============================
# 2. EVALUATION ENDPOINT
# ===============================
@app.post("/evaluate")
def evaluate_api(data: EvaluateRequest):

    score = evaluate_quiz(
        data.questions,
        data.answers,
        data.profile,
        data.topic
    )

    return {
        "score": score,
        "profile": data.profile
    }


# ===============================
# 3. SUGGESTION ENDPOINT
# ===============================
@app.post("/suggest")
def suggest_api(data: SuggestRequest):

    suggestion = suggest_next(data.profile)

    return {
        "suggestion": suggestion
    }