# api_server.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from rag_utils import save_sensor_reading, get_latest_sensor_reading, get_retrieval_qa, compose_query_with_sensor

app = FastAPI(title="Agri-RAG Advisory API")

class SensorPayload(BaseModel):
    device_id: str
    payload: dict  # e.g., {"temperature": 27.4, "humidity": 55.2, "soil_moisture": 42, ...}

class AskRequest(BaseModel):
    device_id: str = None  # optional; if provided, include sensor context
    question: str

@app.post("/sensor")
async def receive_sensor(data: SensorPayload):
    try:
        save_sensor_reading(data.device_id, data.payload)
        return {"status": "ok", "message": "sensor saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask(request: AskRequest = Body(...)):
    if not request.question:
        raise HTTPException(status_code=400, detail="question required")

    # Build the query (include sensor context if device_id provided)
    sensor_payload = None
    if request.device_id:
        sensor_payload = get_latest_sensor_reading(request.device_id)

    augmented_query = compose_query_with_sensor(request.question, sensor_payload)

    # Run retrieval QA
    try:
        qa = get_retrieval_qa()
        # RetrievalQA expects a plain question; we pass augmented text as question - that causes retriever to use
        # embeddings of the augmented query; that's okay for combining. Alternatively, you can retrieve then call LLM with prompt.
        answer = qa.run(augmented_query)
        return {"answer": answer, "sensor_payload": sensor_payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # for dev
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
