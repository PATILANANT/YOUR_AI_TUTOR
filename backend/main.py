from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ai_core import run_agent, evaluate_quiz, suggest_next
from schemas import AgentRequest, EvaluateRequest, SuggestRequest
from database import get_connection
from fastapi import HTTPException
from database import create_tables
from database import save_profile, load_profile
import os, sys

# Add parent dir so we can import utils/rag
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

create_tables()

app = FastAPI()

# ===============================
# CORS MIDDLEWARE
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# AUTH ENDPOINTS (UNCHANGED)
# ===============================
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
# 1. AGENT ENDPOINT (UNCHANGED)
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
# 2. EVALUATION ENDPOINT (UNCHANGED)
# ===============================
@app.post("/evaluate")
def evaluate_api(data: EvaluateRequest):



    score, updated_profile = evaluate_quiz(
        data.questions,
        data.answers,
        data.profile,
        data.topic
    )

    return {
        "score": score,
        "profile": updated_profile
    }




# ===============================
# 3. SUGGESTION ENDPOINT (UNCHANGED)
# ===============================
@app.post("/suggest")
def suggest_api(data: SuggestRequest):

    suggestion = suggest_next(data.profile)

    return {
        "suggestion": suggestion
    }


# ===============================
# 4. TRANSLATE ENDPOINT (NEW)
# ===============================
@app.post("/translate")
def translate_api(data: dict):
    from utils.translator import translate_text

    text = data.get("text", "")
    language = data.get("language", "English")

    if language == "English":
        return {"translated": text}

    translated = translate_text(text, language)
    return {"translated": translated}


# ===============================
# 5. RAG ENDPOINTS (NEW)
# ===============================

# In-memory store for vector DBs per user
_vector_stores = {}

@app.post("/rag_upload")
async def rag_upload(user_id: str = Form(...), file: UploadFile = File(...)):
    from rag.rag_pipeline import process_pdf
    from config import COHERE_API_KEY

    temp_path = f"temp_{user_id}.pdf"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)

        vector_db = process_pdf(temp_path, COHERE_API_KEY)
        _vector_stores[user_id] = vector_db

        return {"message": "PDF processed successfully", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/rag_query")
def rag_query(data: dict):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.chains import RetrievalQA
    from config import GOOGLE_API_KEY

    user_id = str(data.get("user_id", ""))
    query = data.get("query", "")

    if user_id not in _vector_stores:
        raise HTTPException(status_code=404, detail="No PDF uploaded. Upload a PDF first.")

    vector_db = _vector_stores[user_id]
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY)

    rag = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vector_db.as_retriever()
    )

    response = rag.invoke({"query": query})
    return {"answer": response.get("result", "")}


# ===============================
# SERVE FRONTEND STATIC FILES
# ===============================
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")