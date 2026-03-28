from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_cohere import CohereEmbeddings

def process_pdf(file_path, cohere_api_key):
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(pages)

    embeddings = CohereEmbeddings(
        cohere_api_key=cohere_api_key,
        model="embed-multilingual-v3.0"
    )

    vector_db = FAISS.from_documents(chunks, embeddings)
    return vector_db