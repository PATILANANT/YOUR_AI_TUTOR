from fastapi import FastAPI
from ai_core import run_agent, evaluate_quiz, suggest_next
from schemas import AgentRequest, EvaluateRequest, SuggestRequest
from database import get_connection
from fastapi import HTTPException
from database import create_tables
from database import save_profile, load_profile


create_tables()

app = FastAPI()

@app.post("/register")
def register(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (data["username"], data["password"])
        )
        conn.commit()
    except:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"message": "User registered"}


@app.post("/login")
def login(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (data["username"], data["password"])
    )

    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login success", "user_id": user["id"]}

@app.post("/save_profile")
def save_profile_api(data: dict):

    save_profile(data["user_id"], data["profile"])

    return {"message": "Profile saved"}

@app.get("/load_profile/{user_id}")
def load_profile_api(user_id: int):

    profile = load_profile(user_id)

    return {"profile": profile}

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