import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_cohere import CohereEmbeddings

def get_embeddings(cohere_api_key):
    return CohereEmbeddings(
        cohere_api_key=cohere_api_key,
        model="embed-multilingual-v3.0"
    )

def process_pdf(file_path, cohere_api_key, persist_path=None):
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(pages)

    embeddings = get_embeddings(cohere_api_key)

    vector_db = FAISS.from_documents(chunks, embeddings)
    
    if persist_path:
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)
        vector_db.save_local(persist_path)
        
    return vector_db

def load_vector_db(persist_path, cohere_api_key):
    if not os.path.exists(persist_path):
        return None
    
    embeddings = get_embeddings(cohere_api_key)
    # allow_dangerous_deserialization is required for FAISS local loading
    return FAISS.load_local(persist_path, embeddings, allow_dangerous_deserialization=True)