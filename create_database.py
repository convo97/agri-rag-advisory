# create_database.py
import os
from glob import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# Ensure OPENAI_API_KEY is set in env, or use python-dotenv to load from .env

PDF_FOLDER = "data"
CHROMA_DIR = "chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def ingest_all_pdfs(pdf_folder=PDF_FOLDER, chroma_dir=CHROMA_DIR):
    pdf_paths = glob(os.path.join(pdf_folder, "*.pdf"))
    if not pdf_paths:
        print("No PDFs found in", pdf_folder)
        return

    # load all docs
    docs = []
    for p in pdf_paths:
        print("Loading", p)
        loader = PyPDFLoader(p)
        docs.extend(loader.load())

    print(f"Loaded {len(docs)} pages/chunks from {len(pdf_paths)} PDFs")

    # split
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    documents = splitter.split_documents(docs)
    print(f"Split into {len(documents)} documents/chunks")

    # embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))

    # persist to Chroma
    db = Chroma.from_documents(documents, embeddings, persist_directory=chroma_dir)
    db.persist()
    print("✅ Ingested to Chroma at", chroma_dir)

if __name__ == "__main__":
    ingest_all_pdfs()
