from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import uuid
import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

from tools import TOOLS, TOOL_FUNCTIONS

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

app = FastAPI(title="AI Data Analyst")

# In-memory session store: {session_id: DataFrame}
sessions: dict[str, pd.DataFrame] = {}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty.")

    session_id = str(uuid.uuid4())
    sessions[session_id] = df

    schema = {
        "session_id": session_id,
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "num_rows": len(df),
        "sample_rows": df.head(5).where(pd.notnull(df.head(5)), None).to_dict(orient="records"), 
    }

    return schema


class AskRequest(BaseModel):
    session_id: str
    question: str


@app.post("/ask")
async def ask_question(request: AskRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a CSV first.")

    df = sessions[request.session_id]

    schema_summary = {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample_rows": df.head(3).where(pd.notnull(df.head(3)), None).to_dict(orient="records"),
    }

    system_prompt = (
        "You are a data analyst assistant. You will be given a dataset's schema "
        "and a user's question. Choose the single best tool to answer it, using "
        "exact column names from the schema provided."
    )

    user_message = (
        f"Dataset schema:\n{json.dumps(schema_summary, indent=2)}\n\n"
        f"Question: {request.question}"
    )

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)

    if tool_use_block is None:
        text_block = next((b for b in response.content if b.type == "text"), None)
        return {"answer": text_block.text if text_block else "I couldn't determine how to answer that."}

    tool_name = tool_use_block.name
    tool_input = tool_use_block.input

    if tool_name not in TOOL_FUNCTIONS:
        raise HTTPException(status_code=500, detail=f"Unknown tool selected: {tool_name}")

    try:
        result = TOOL_FUNCTIONS[tool_name](df, **tool_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if tool_name == "summarize_column":
        return {"tool_used": tool_name, "tool_input": tool_input, "result": result}

    return {"tool_used": tool_name, "tool_input": tool_input, "chart": result.to_json()}


@app.get("/")
async def root():
    return {"message": "AI Data Analyst API is running."}