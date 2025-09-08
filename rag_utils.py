# rag_utils.py
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
import json
from tinydb import TinyDB, Query

CHROMA_DIR = "chroma_db"
SENSOR_DB_FILE = "sensors_db.json"

def get_chroma_db():
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))
    db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    return db

def get_retrieval_qa():
    db = get_chroma_db()
    retriever = db.as_retriever(search_kwargs={"k": 6})  # top 6 chunks
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.environ.get("OPENAI_API_KEY"))
    qa = RetrievalQA.from_chain_type(llm, retriever=retriever, return_source_documents=False)
    return qa

# tinydb wrapper to store latest sensor readings per device/location
def save_sensor_reading(device_id: str, sensor_payload: dict):
    db = TinyDB(SENSOR_DB_FILE)
    Sensor = Query()
    # upsert by device_id
    items = db.search(Sensor.device_id == device_id)
    if items:
        db.update({"payload": sensor_payload}, Sensor.device_id == device_id)
    else:
        db.insert({"device_id": device_id, "payload": sensor_payload})

def get_latest_sensor_reading(device_id: str):
    db = TinyDB(SENSOR_DB_FILE)
    Sensor = Query()
    items = db.search(Sensor.device_id == device_id)
    if items:
        return items[-1]["payload"]
    return None

# Compose prompt with sensor context + user query
def compose_query_with_sensor(user_question: str, sensor_payload: dict):
    if not sensor_payload:
        return user_question

    # Create a clean sensor summary
    sensor_lines = []
    for k, v in sensor_payload.items():
        sensor_lines.append(f"{k}: {v}")
    sensor_block = "\n".join(sensor_lines)

    augmented_query = (
        f"You are an agritech assistant. Use the knowledge from the uploaded PDF manuals and the "
        f"field sensor readings below to answer the user's question precisely, give actionable recommendations, "
        f"and provide clear next steps for a small farmer.\n\n"
        f"[Sensor Readings]\n{sensor_block}\n\n"
        f"[User Question]\n{user_question}\n\n"
        f"Important: when giving fertilizer or pesticide recommendations, emphasize safe dosages, test soil first, "
        f"and mention if further lab analysis is recommended. If the PDF provides conflicting instructions mention that "
        f"and favor the most conservative/safe option.\n"
    )
    return augmented_query
