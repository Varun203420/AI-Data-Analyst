from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import io
import uuid

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


@app.get("/")
async def root():
    return {"message": "AI Data Analyst API is running."}