from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ai_core import run_agent, evaluate_quiz, suggest_next, build_context_prompt, _generate
from schemas import AgentRequest, EvaluateRequest, SuggestRequest, ChatRequest
from database import (
    get_connection, create_tables, save_profile, load_profile,
    create_conversation, get_conversations, rename_conversation,
    delete_conversation, add_message, get_messages,
    save_conversation_profile, load_conversation_profile,
    delete_conversation_profile, get_user_conversation_profiles
)
from mastery import (
    create_mastery_tables, get_user_mastery, get_mastery_summary,
    get_weak_concepts, get_stale_concepts, generate_proactive_message,
    batch_update_mastery, extract_concepts_from_quiz,
    get_conversation_mastery, get_conversation_mastery_summary
)
import os, sys

# Add parent dir so we can import utils/rag
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

create_tables()
create_mastery_tables()

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
    # Also save to conversation if conv_id is provided
    conv_id = data.get("conversation_id")
    if conv_id:
        save_conversation_profile(int(conv_id), data["user_id"], data["profile"])
    return {"message": "Profile saved"}

@app.get("/load_profile/{user_id}")
def load_profile_api(user_id: int):

    profile = load_profile(user_id)

    return {"profile": profile}

# ===============================
# CONVERSATION HISTORY ENDPOINTS
# ===============================

@app.post("/conversations")
def create_conversation_api(data: dict):
    """Create a new conversation for the user."""
    user_id = data.get("user_id")
    title = data.get("title", "New Chat")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    conv_id = create_conversation(user_id, title)
    return {"conversation_id": conv_id, "title": title}


@app.get("/conversations/{user_id}")
def list_conversations_api(user_id: int):
    """List all conversations for a user, newest first."""
    convs = get_conversations(user_id)
    return {"conversations": convs}


@app.get("/messages/{conv_id}")
def get_messages_api(conv_id: int):
    """Get all messages in a conversation."""
    print(f"Fetching messages for conversation: {conv_id}")
    msgs = get_messages(conv_id)
    return {"messages": msgs}


@app.post("/conversations/{conv_id}/message")
def save_message_api(conv_id: int, data: dict):
    """Save a single message to a conversation."""
    role = data.get("role")
    content = data.get("content")
    user_id = data.get("user_id")
    if not role or not content:
        raise HTTPException(status_code=400, detail="role and content required")
    add_message(conv_id, role, content)

    # Auto-title: if this is the first user message, set title from it
    if role == "user" and user_id:
        msgs = get_messages(conv_id)
        user_msgs = [m for m in msgs if m["role"] == "user"]
        if len(user_msgs) == 1:
            # Use first 50 chars of the message as title
            auto_title = content[:50] + ("..." if len(content) > 50 else "")
            rename_conversation(conv_id, user_id, auto_title)
            return {"message": "saved", "auto_title": auto_title}

    return {"message": "saved"}


@app.put("/conversations/{conv_id}/rename")
def rename_conversation_api(conv_id: int, data: dict):
    """Rename a conversation."""
    user_id = data.get("user_id")
    new_title = data.get("title")
    if not user_id or not new_title:
        raise HTTPException(status_code=400, detail="user_id and title required")
    rename_conversation(conv_id, user_id, new_title)
    return {"message": "renamed"}


@app.delete("/conversations/{conv_id}")
def delete_conversation_api(conv_id: int, user_id: int):
    """Delete a conversation, its messages, profile, and mastery data."""
    delete_conversation_profile(conv_id)
    # Also clean up conversation mastery
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversation_mastery WHERE conversation_id=?", (conv_id,))
    conn.commit()
    conn.close()
    delete_conversation(conv_id, user_id)
    return {"message": "deleted"}


# ===============================
# CONVERSATION PROFILE ENDPOINTS (NEW)
# ===============================

@app.get("/conversations/{conv_id}/profile")
def get_conversation_profile_api(conv_id: int):
    """Get the profile for a specific conversation."""
    profile = load_conversation_profile(conv_id)
    return {"profile": profile, "conversation_id": conv_id}


@app.post("/conversations/{conv_id}/profile")
def save_conversation_profile_api(conv_id: int, data: dict):
    """Save or update the profile for a specific conversation."""
    user_id = data.get("user_id")
    profile = data.get("profile", {})
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    save_conversation_profile(conv_id, user_id, profile)
    return {"message": "Conversation profile saved"}


@app.get("/conversations/{conv_id}/mastery")
def get_conversation_mastery_api(conv_id: int):
    """Get mastery data for a specific conversation."""
    mastery = get_conversation_mastery(conv_id)
    summary = get_conversation_mastery_summary(conv_id)
    return {"mastery": mastery, "summary": summary, "conversation_id": conv_id}


@app.get("/user/{user_id}/conversations_with_profiles")
def get_user_conversations_profiles_api(user_id: int):
    """Get all conversations with their profiles for a user."""
    data = get_user_conversation_profiles(user_id)
    return {"conversations": data}


# ===============================
# 1. AGENT ENDPOINT (UPGRADED with Mastery)
# ===============================
@app.post("/agent")
def agent_api(data: AgentRequest):

    # Load chat history from DB if conversation_id is provided
    chat_history = data.chat_history or []
    if data.conversation_id and not chat_history:
        try:
            msgs = get_messages(data.conversation_id)
            chat_history = [{"role": m["role"], "content": m["content"]} for m in msgs]
        except Exception as e:
            print(f"[Agent] Failed to load chat history: {e}")

    # Load conversation profile from DB if available
    profile = data.profile
    if data.conversation_id:
        try:
            conv_profile = load_conversation_profile(data.conversation_id)
            # Merge: conv_profile as base, overlay with request profile
            if conv_profile and conv_profile.get("syllabus"):
                if not profile.get("syllabus"):
                    profile["syllabus"] = conv_profile["syllabus"]
                if not profile.get("weak_topics"):
                    profile["weak_topics"] = conv_profile.get("weak_topics", {})
                if not profile.get("progress"):
                    profile["progress"] = conv_profile.get("progress", {})
        except Exception as e:
            print(f"[Agent] Failed to load conv profile: {e}")

    result = run_agent(
        data.topic,
        profile,
        data.target,
        data.style,
        chat_history=chat_history
    )

    return result


# ===============================
# 1b. SIMPLE CHAT ENDPOINT (Normal Mode)
# ===============================
@app.post("/chat")
def chat_api(data: ChatRequest):
    """Context-aware chat — sends full conversation context to the AI."""

    query = data.query
    language = data.language or "English"
    profile = data.profile or {}

    # Load chat history from DB if conversation_id is provided
    chat_history = data.chat_history or []
    if data.conversation_id and not chat_history:
        try:
            msgs = get_messages(data.conversation_id)
            chat_history = [{"role": m["role"], "content": m["content"]} for m in msgs]
        except Exception as e:
            print(f"[Chat] Failed to load chat history: {e}")

    # Load conversation profile from DB if available
    if data.conversation_id:
        try:
            conv_profile = load_conversation_profile(data.conversation_id)
            if conv_profile:
                # Use conv_profile as base, overlay with request profile
                for key in ["syllabus", "weak_topics", "progress", "goal"]:
                    if conv_profile.get(key) and not profile.get(key):
                        profile[key] = conv_profile[key]
        except Exception as e:
            print(f"[Chat] Failed to load conv profile: {e}")

    # Build rich context
    context = build_context_prompt(chat_history, profile)

    prompt = f"""{context}You are a helpful, friendly, and expert AI tutor. Answer the student's question clearly and concisely.
Use markdown formatting for readability. Be thorough but don't overcomplicate things.

IMPORTANT GUIDELINES:
- If the chat history shows previous discussions, reference them naturally (e.g., "As we discussed earlier...").
- If the student has weak topics, gently reinforce those concepts when relevant.
- If the student has a syllabus, relate your answer to their learning path.
- Be encouraging and supportive.

Student's Question: {query}"""

    answer = _generate(prompt)

    # Translate if needed
    if language and language != "English":
        try:
            from utils.translator import translate_text
            answer = translate_text(answer, language)
        except Exception:
            pass

    return {"answer": answer}


# ===============================
# 2. EVALUATION ENDPOINT (UPGRADED with Mastery Tracking)
# ===============================
@app.post("/evaluate")
def evaluate_api(data: EvaluateRequest):

    score, updated_profile = evaluate_quiz(
        data.questions,
        data.answers,
        data.profile,
        data.topic
    )

    # Track per-concept mastery if user_id is provided in the profile
    user_id = data.profile.get("user_id")
    conversation_id = data.profile.get("conversation_id")
    concepts_data = []
    if user_id:
        try:
            concepts = extract_concepts_from_quiz(data.questions, data.topic)
            # For each concept, track based on overall quiz performance
            total = len(data.questions)
            passed = (score / total) >= 0.7 if total > 0 else False

            for concept in concepts:
                concepts_data.append({
                    "concept": concept,
                    "is_correct": passed
                })
            batch_update_mastery(user_id, concepts_data, conversation_id=conversation_id)
        except Exception as e:
            print(f"[Mastery] Tracking error: {e}")

    return {
        "score": score,
        "profile": updated_profile,
        "concepts_tracked": [c["concept"] for c in concepts_data]
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
# 5. RAG ENDPOINTS
# ===============================

# In-memory store for vector DBs per user
_vector_stores = {}
# In-memory store for knowledge graphs per user
_knowledge_graphs = {}

@app.post("/rag_upload")
async def rag_upload(user_id: str = Form(...), file: UploadFile = File(...)):
    from rag.rag_pipeline import process_pdf
    from config import COHERE_API_KEY

    temp_path = f"temp_{user_id}.pdf"
    persist_path = os.path.join("vector_stores", user_id)
    
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)

        # Save to disk as well
        vector_db = process_pdf(temp_path, COHERE_API_KEY, persist_path=persist_path)
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
    from config import GOOGLE_API_KEY, COHERE_API_KEY
    from rag.rag_pipeline import load_vector_db

    user_id = str(data.get("user_id", ""))
    query = data.get("query", "")

    if user_id not in _vector_stores:
        # Try loading from disk
        persist_path = os.path.join("vector_stores", user_id)
        vector_db = load_vector_db(persist_path, COHERE_API_KEY)
        
        if not vector_db:
            raise HTTPException(status_code=404, detail="No PDF uploaded. Upload a PDF first.")
        
        _vector_stores[user_id] = vector_db

    vector_db = _vector_stores[user_id]
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY)

    rag = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vector_db.as_retriever()
    )

    response = rag.invoke({"query": query})
    return {"answer": response.get("result", "")}


# ===============================
# 6. KNOWLEDGE GRAPH ENDPOINTS (NEW)
# ===============================

@app.post("/knowledge_graph/extract")
async def extract_knowledge_graph(data: dict):
    """Extract a knowledge graph from the user's uploaded PDF chunks."""
    from knowledge_graph import (
        build_knowledge_graph, graph_to_vis_data,
        save_graph, load_graph, merge_graphs
    )
    from config import COHERE_API_KEY
    from rag.rag_pipeline import load_vector_db

    user_id = str(data.get("user_id", ""))
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # Get vector store to extract chunks
    if user_id not in _vector_stores:
        persist_path = os.path.join("vector_stores", user_id)
        vector_db = load_vector_db(persist_path, COHERE_API_KEY)
        if not vector_db:
            raise HTTPException(status_code=404, detail="No PDF uploaded. Upload a PDF first.")
        _vector_stores[user_id] = vector_db

    vector_db = _vector_stores[user_id]

    # Get all documents from the vector store
    try:
        # FAISS doesn't have a direct "get all docs" method,
        # so we do a broad similarity search
        chunks = vector_db.similarity_search("main topics concepts summary", k=20)
    except Exception:
        chunks = []

    if not chunks:
        raise HTTPException(status_code=404, detail="No content found in PDF.")

    # Build the knowledge graph (limit chunks to avoid rate limits)
    chunk_texts = [c.page_content for c in chunks[:10]]
    new_graph = build_knowledge_graph(chunk_texts)

    # Merge with existing graph if any
    graph_path = os.path.join("knowledge_graphs", f"{user_id}.json")
    existing = load_graph(graph_path)

    if existing:
        merged = merge_graphs(existing, new_graph)
    else:
        merged = new_graph

    # Save to disk
    save_graph(merged, graph_path)
    _knowledge_graphs[user_id] = merged

    # Get mastery data for coloring
    mastery_data = {}
    try:
        mastery_records = get_user_mastery(int(user_id))
        mastery_data = {r["concept"]: r["score"] for r in mastery_records}
    except Exception:
        pass

    vis_data = graph_to_vis_data(merged, mastery_data)
    return {
        "message": "Knowledge graph built",
        "graph": vis_data,
        "node_count": len(vis_data["nodes"]),
        "edge_count": len(vis_data["edges"])
    }


@app.get("/knowledge_graph/{user_id}")
def get_knowledge_graph(user_id: str):
    """Return the user's knowledge graph as vis-network JSON."""
    from knowledge_graph import load_graph, graph_to_vis_data

    # Try in-memory first
    if user_id in _knowledge_graphs:
        graph = _knowledge_graphs[user_id]
    else:
        graph_path = os.path.join("knowledge_graphs", f"{user_id}.json")
        graph = load_graph(graph_path)
        if not graph:
            return {"graph": {"nodes": [], "edges": []}, "node_count": 0, "edge_count": 0}
        _knowledge_graphs[user_id] = graph

    # Get mastery data for coloring
    mastery_data = {}
    try:
        mastery_records = get_user_mastery(int(user_id))
        mastery_data = {r["concept"]: r["score"] for r in mastery_records}
    except Exception:
        pass

    vis_data = graph_to_vis_data(graph, mastery_data)
    return {
        "graph": vis_data,
        "node_count": len(vis_data["nodes"]),
        "edge_count": len(vis_data["edges"])
    }


# ===============================
# 7. YOUTUBE INTEGRATION ENDPOINTS (NEW)
# ===============================

@app.post("/youtube_ingest")
async def youtube_ingest(data: dict):
    """Ingest a YouTube video: extract transcript, summarize, add to vector store."""
    from multimodal import extract_youtube_transcript, summarize_transcript
    from rag.rag_pipeline import get_embeddings
    from config import COHERE_API_KEY
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document

    url = data.get("url", "")
    user_id = str(data.get("user_id", ""))

    if not url or not user_id:
        raise HTTPException(status_code=400, detail="url and user_id required")

    try:
        # Extract transcript
        result = extract_youtube_transcript(url)
        transcript = result["transcript"]
        
        # Summarize
        summary = summarize_transcript(transcript)

        # Split into chunks for vector store
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
        docs = [Document(page_content=transcript, metadata={"source": f"youtube:{result['video_id']}"})]
        chunks = splitter.split_documents(docs)

        # Add to user's vector store
        embeddings = get_embeddings(COHERE_API_KEY)

        if user_id in _vector_stores:
            _vector_stores[user_id].add_documents(chunks)
            # Persist
            persist_path = os.path.join("vector_stores", user_id)
            _vector_stores[user_id].save_local(persist_path)
        else:
            persist_path = os.path.join("vector_stores", user_id)
            vector_db = FAISS.from_documents(chunks, embeddings)
            os.makedirs(os.path.dirname(persist_path), exist_ok=True)
            vector_db.save_local(persist_path)
            _vector_stores[user_id] = vector_db

        return {
            "message": "YouTube video processed",
            "video_id": result["video_id"],
            "summary": summary,
            "chunks_added": len(chunks),
            "duration_seconds": result["duration_seconds"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")


# ===============================
# 8. VOICE NOTE ENDPOINT (NEW)
# ===============================

@app.post("/voice_transcribe")
async def voice_transcribe(
    user_id: str = Form(...),
    audio: UploadFile = File(...)
):
    """Transcribe a voice note and return the text."""
    from multimodal import transcribe_voice_note

    temp_path = f"temp_audio_{user_id}.webm"

    try:
        contents = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(contents)

        text = transcribe_voice_note(temp_path)

        if not text:
            raise HTTPException(status_code=400, detail="Could not transcribe audio. Please try again.")

        return {"transcription": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ===============================
# 9. TOPIC MASTERY ENDPOINTS (NEW)
# ===============================

@app.get("/mastery/{user_id}")
def get_mastery_api(user_id: int):
    """Get all topic mastery data for a user."""
    mastery = get_user_mastery(user_id)
    summary = get_mastery_summary(user_id)
    return {"mastery": mastery, "summary": summary}


@app.get("/mastery/{user_id}/weak")
def get_weak_api(user_id: int):
    """Get weak concepts for a user."""
    weak = get_weak_concepts(user_id)
    stale = get_stale_concepts(user_id)
    return {"weak": weak, "stale": stale}


@app.get("/mastery/{user_id}/proactive")
def get_proactive_api(user_id: int, topic: str = ""):
    """Get proactive learning message for a user."""
    message = generate_proactive_message(user_id, topic)
    return {"message": message}


# ===============================
# SERVE FRONTEND STATIC FILES
# ===============================
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")