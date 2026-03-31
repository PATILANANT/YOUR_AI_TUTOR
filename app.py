# import streamlit as st
# from config import model, COHERE_API_KEY
# from utils.translator import translate_text
# from rag.rag_pipeline import process_pdf

# from langchain_classic.chains import RetrievalQA
# from langchain_google_genai import ChatGoogleGenerativeAI

# from typing import TypedDict
# from langgraph.graph import StateGraph, END


# # ========= SESSION INIT (MOVE TO TOP) =========
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "profile" not in st.session_state:
#     st.session_state.profile = {
#         "goal": None,
#         "syllabus": [],
#         "progress": {},
#         "weak_topics": []
#     }

# # ========= TYPED DICT FOR AGENT MODE =========
# class TutorState(TypedDict):
#     topic: str
#     plan: str
#     teaching: str
#     quiz: str
#     evaluation: str
#     target: str
#     style: str
#     user_answer: str   

# def decide_flow(prompt, target):
#     prompt_lower = prompt.lower()

#     if len(prompt.split()) < 5:
#         return "simple"

#     if target in ["JEE", "NEET", "GATE"]:
#         return "exam"

#     if "explain" in prompt_lower or "what is" in prompt_lower:
#         return "concept"

#     return "full"


# def planner_agent(state):
#     prompt = f"Break topic into steps:\n{state['topic']}"
#     return {"plan": model.generate_content(prompt).text}


# def teacher_agent(state):
#     prompt = f"""
# Teach this topic for {state['target']} exam.
# Style: {state['style']}

# Topic:
# {state['topic']}
# """
#     return {"teaching": model.generate_content(prompt).text}

# def evaluator_agent(state):
#     prompt = f"Suggest improvement:\n{state['topic']}"
#     return {"evaluation": model.generate_content(prompt).text}

# def examiner_agent(state):
#     prompt = f"""
# Generate EXACTLY 3 MCQs.

# STRICT RULES:
# - Each question MUST be on NEW LINE
# - Use this format ONLY:

# Q1|Question|a) option|b) option|c) option|d) option|c
# Q2|Question|a) option|b) option|c) option|d) option|b
# Q3|Question|a) option|b) option|c) option|d) option|a

# DO NOT ADD ANY EXTRA TEXT.

# Topic:
# {state['topic']}
# """
#     return {"quiz": model.generate_content(prompt).text}

# def parse_quiz(quiz_text):
#     questions = []

#     lines = quiz_text.strip().split("\n")

#     for line in lines:
#         if "|" in line:
#             parts = line.split("|")

#             if len(parts) >= 7:
#                 questions.append({
#                     "question": parts[1].strip(),
#                     "options": [opt.strip() for opt in parts[2:6]],
#                     "answer": parts[6].strip().lower()[0]  # only 'a','b','c','d'
#                 })

#     return questions

# @st.cache_resource
# def build_multi_agent():
#     graph = StateGraph(TutorState)

#     graph.add_node("planner", planner_agent)
#     graph.add_node("teacher", teacher_agent)
#     graph.add_node("examiner", examiner_agent)
#     graph.add_node("evaluator", evaluator_agent)

#     graph.set_entry_point("planner")

#     graph.add_edge("planner", "teacher")
#     graph.add_edge("teacher", "examiner")
#     graph.add_edge("examiner", "evaluator")
#     graph.add_edge("evaluator", END)

#     return graph.compile()

# # ========= LANGUAGES =========
# INDIAN_LANGUAGES = [
#     "English", "Hindi", "Marathi", "Gujarati", "Punjabi", "Bengali",
#     "Tamil", "Telugu", "Kannada", "Malayalam", "Odia", "Assamese",
#     "Urdu", "Sanskrit", "Konkani", "Maithili", "Dogri", "Bodo",
#     "Santhali", "Kashmiri", "Manipuri (Meitei)", "Nepali", "Sindhi",
#     "Tulu", "Bhojpuri", "Rajasthani", "Chhattisgarhi", "Haryanvi"
# ]

# # ========= PAGE =========
# st.set_page_config(page_title="Your AI Tutor", layout="wide")

# # ========= SIDEBAR =========
# with st.sidebar:
#     st.markdown("## 🌈 Your AI Tutor")

#     interest = st.selectbox(
#         "❤️ Learning Context:",
#         [
#             "Normal (Direct Explanation)",
#             "Relatable (Real-life Examples)",
#             "Others (Use Analogy)"
#         ]
#     )

#     language = st.selectbox("🗣️ Language:", INDIAN_LANGUAGES)

#     style = st.selectbox(
#         "🧠 Learning Style:",
#         ["Regular Way", "Stories & Analogies", "Visual Flowcharts", "Code Examples"]
#     )

#     # ✅ Mode
#     mode = st.selectbox("🤖 Mode", ["Normal Tutor", "AI Tutor"])

#     st.markdown("---")

#     st.subheader("🎯 Target Exam")
#     target = st.selectbox(
#         "Select your goal:",
#         [
#             "General Learning", "School Exam", "University Exam",
#             "JEE", "NEET", "GATE", "UPSC", "CAT", "SSC", "Banking Exams"
#         ]
#     )
#     st.session_state.profile["goal"] = target

#     st.markdown("---")

#     st.subheader("📚 Upload / Add Syllabus")

#     syllabus_input = st.text_area("Enter topics (comma separated)")

#     if st.button("Save Syllabus"):
#         topics = [t.strip() for t in syllabus_input.split(",")]
#         st.session_state.profile["syllabus"] = topics
#         st.success("Syllabus Saved ✅")

#     # PDF Upload
#     st.subheader("📚 Upload PDF")
#     uploaded_file = st.file_uploader("Upload PDF", type="pdf")

#     if uploaded_file:
#         if ("current_file" not in st.session_state or 
#             st.session_state.current_file != uploaded_file.name):

#             with st.spinner("Processing PDF..."):
#                 temp_path = "temp.pdf"
#                 with open(temp_path, "wb") as f:
#                     f.write(uploaded_file.getvalue())

#                 vector_db = process_pdf(temp_path, COHERE_API_KEY)

#                 st.session_state.vector_db = vector_db
#                 st.session_state.current_file = uploaded_file.name

#             st.success("✅ PDF Loaded!")

#     if st.button("Reset Chat"):
#         st.session_state.messages = []
#         st.session_state.pop("vector_db", None)

# # ========= CHAT =========
# # if "messages" not in st.session_state:
# #     st.session_state.messages = []

# # if "profile" not in st.session_state:
# #     st.session_state.profile = {
# #         "goal": None,
# #         "syllabus": [],
# #         "progress": {},
# #         "weak_topics": []
# #     }

# # ========= CHAT =========
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # ✅ MUST BE HERE
# if "profile" not in st.session_state:
#     st.session_state.profile = {
#         "goal": None,
#         "syllabus": [],
#         "progress": {},
#         "weak_topics": []
#     }

# # # ========= SIDEBAR =========
# # target = st.selectbox(...)

# # # ✅ NOW SAFE
# # st.session_state.profile["goal"] = target

# st.title("🌈 Your AI Tutor")

# # ========= DISPLAY =========
# for msg in st.session_state.messages:
#     with st.chat_message(msg["role"]):
#         if "```dot" in msg["content"].lower():
#             try:
#                 parts = msg["content"].split("```dot")
#                 dot_code = parts[1].split("```")[0].strip()
#                 st.markdown(parts[0])
#                 st.graphviz_chart(dot_code, use_container_width=True)
#             except:
#                 st.markdown(msg["content"])
#         else:
#             st.markdown(msg["content"])

# # ========= INPUT =========
# if prompt := st.chat_input("Ask your doubt..."):

#     st.session_state.pop("quiz_data", None)
#     st.session_state.pop("user_answers", None)
#     st.session_state.messages.append({"role": "user", "content": prompt})

#     with st.chat_message("user"):
#         st.markdown(prompt)

#     with st.chat_message("assistant"):
#         with st.spinner("Thinking..."):
#             try:
#                 # ========= SYSTEM PROMPT =========
#                 system_prompt = f"""
# You are Your AI Tutor.

# User Preferences:
# - Context: {interest}
# - Language: {language}
# - Style: {style}
# - Target: {target}

# Rules:
# 1. Respond in {language}
# 2. Adapt explanation
# 3. Follow style
# 4. Make exam-oriented answers

# STYLE RULES:
# - Stories → storytelling
# - Code → examples
# - Visual → ALWAYS return Graphviz DOT format:

# ```dot
# digraph G {{
#     Start -> Process -> End;
# }} """
#                 if target in ["School Exam", "University Exam"]:
#                     system_prompt += "\nAnswer in points."

#                 if target in ["JEE", "NEET", "GATE"]:
#                     system_prompt += "\nInclude formulas."

#             # ========= AGENT MODE =========
#                 if mode == "Learning Agent":

#                     agent = build_multi_agent()

#                     if "quiz_data" not in st.session_state:
#                         result = agent.invoke({
#                             "topic": prompt,
#                             "target": target,
#                             "style": style
#                         })

#                         st.session_state.plan = result.get("plan", "")
#                         st.session_state.teaching = result.get("teaching", "")
#                         st.session_state.quiz_data = result.get("quiz", "")

#                     # ✅ ONLY TEXT HERE (NO RADIO BUTTONS)
#                     # st.markdown("### 📌 Learning Plan")
#                     # st.write(st.session_state.plan)

#                     # st.markdown("### 📖 Explanation")
#                     # st.write(st.session_state.teaching)
#                     answer = f"""
#                     Learning Plan:
#                     {st.session_state.plan}

#                     Explanation:
#                     {st.session_state.teaching}
#                     """

                    
#             # ========= NORMAL MODE =========
#                 else:
#                     if "vector_db" in st.session_state:
#                         llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

#                         rag = RetrievalQA.from_chain_type(
#                             llm=llm,
#                             retriever=st.session_state.vector_db.as_retriever()
#                         )

#                         response = rag.invoke({
#                             "query": f"{system_prompt}\n\nQuestion: {prompt}"
#                         })
#                         answer = response.get("result")

#                     else:
#                         response = model.generate_content(
#                         f"{system_prompt}\n\nQuestion: {prompt}"
#                         )
#                         answer = response.text

#                 # Translation
#                     answer = translate_text(answer, language)

#                 # Graphviz render
#                     if "```dot" in answer.lower():
#                         try:
#                             parts = answer.split("```dot")
#                             dot_code = parts[1].split("```")[0].strip()
#                             st.markdown(parts[0])
#                             st.graphviz_chart(dot_code, use_container_width=True)
#                         except:
#                             st.markdown(answer)
#                     else:
#                         st.markdown(answer)

#                 st.session_state.messages.append({
#                     "role": "assistant",
#                     "content": answer
#             })

#             except Exception as e:
#                 st.error(f"Error: {e}")

# # ========= PERSISTENT LEARNING DISPLAY =========
# if mode == "Learning Agent" and "plan" in st.session_state:

#     st.markdown("## 📘 Learning Content")

#     st.markdown("### 📌 Learning Plan")
#     st.write(st.session_state.plan)

#     st.markdown("### 📖 Explanation")
#     st.write(st.session_state.teaching)

# # ========= MCQ SECTION (OUTSIDE CHAT) =========
# if mode == "Learning Agent" and "quiz_data" in st.session_state:

#     st.markdown("## 🧾 Quiz Section")

#     questions = parse_quiz(st.session_state.quiz_data)

#     if not questions:
#         st.error("⚠️ Quiz parsing failed. Try again.")
#     else:
#         if "user_answers" not in st.session_state:
#             st.session_state.user_answers = [None] * len(questions)

#         for i, q in enumerate(questions):
#             st.markdown(f"### Q{i+1}: {q['question']}")

#             choice = st.radio(
#                 f"Select answer for Q{i+1}",
#                 q["options"],
#                 key=f"quiz_q{i}"
#             )

#             st.session_state.user_answers[i] = choice

#         if st.button("Submit Quiz"):

#             score = 0

#             for i, q in enumerate(questions):
#                 correct = q["answer"]
#                 selected = st.session_state.user_answers[i][0].lower()

#                 if selected == correct:
#                     score += 1
#                     st.success(f"Q{i+1}: Correct ✅")
#                 else:
#                     st.error(f"Q{i+1}: Wrong ❌ (Correct: {correct.upper()})")

#             st.markdown(f"## 🎯 Score: {score}/{len(questions)}")

#             topic = prompt

#             st.session_state.profile["progress"][topic] = score

#             if score < len(questions):
#                 st.session_state.profile["weak_topics"].append(topic)


# st.markdown("## 📊 Student Dashboard")

# profile = st.session_state.profile

# st.write("🎯 Goal:", profile["goal"])
# st.write("📚 Syllabus:", profile["syllabus"])
# st.write("📈 Progress:", profile["progress"])
# st.write("⚠️ Weak Topics:", profile["weak_topics"])



import streamlit as st

st.set_page_config(page_title="Your AI Tutor", layout="wide")

st.title("🌈 Your AI Tutor")

st.markdown("""
Welcome to **Your AI Tutor** 🚀  

Use the sidebar to navigate:

📘 Learning  
📊 Dashboard  
📚 Syllabus  
📈 Analysis  
""")