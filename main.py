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

    # Chart tools now return (figure, data_summary); summarize_column returns a dict directly
    if tool_name == "summarize_column":
        chart_fig = None
        data_summary = result
    else:
        chart_fig, data_summary = result

    # Generate a plain-English findings summary using REAL computed data
    findings_context = json.dumps(data_summary)

    findings_response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                f"You just ran a data analysis. The question was: '{request.question}'. "
                f"Here is the computed result:\n{findings_context}\n\n"
                f"Write a 1-3 sentence plain-English summary of what this shows, "
                f"like a data analyst explaining findings to a colleague. Be direct and specific with numbers."
            )
        }]
    )
    findings_text = findings_response.content[0].text

    if tool_name == "summarize_column":
        return {"tool_used": tool_name, "tool_input": tool_input, "result": data_summary, "findings": findings_text}

    return {"tool_used": tool_name, "tool_input": tool_input, "chart": chart_fig.to_json(), "findings": findings_text}


@app.get("/")
async def root():
    return {"message": "AI Data Analyst API is running."}   