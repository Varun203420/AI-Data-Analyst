import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8001"

st.set_page_config(page_title="AI Data Analyst", layout="wide")
st.title("AI Data Analyst")
st.caption("Upload a CSV, ask questions in plain English, get charts and insights.")

# Persist session_id, schema, the current question text, and Q&A history across reruns
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "columns" not in st.session_state:
    st.session_state.columns = None
if "dtypes" not in st.session_state:
    st.session_state.dtypes = None
if "num_rows" not in st.session_state:
    st.session_state.num_rows = None
if "filename" not in st.session_state:
    st.session_state.filename = None
if "question" not in st.session_state:
    st.session_state.question = ""
if "history" not in st.session_state:
    st.session_state.history = []

# Sidebar — persistent dataset info once uploaded
with st.sidebar:
    st.header("Dataset")
    if st.session_state.session_id:
        st.metric("Rows", f"{st.session_state.num_rows:,}")
        st.caption(f"File: {st.session_state.filename}")
        st.divider()
        st.caption("Columns")
        for col in st.session_state.columns:
            dtype = st.session_state.dtypes.get(col, "")
            kind = "🔢" if ("int" in dtype or "float" in dtype) else "🔤"
            st.text(f"{kind} {col}")
    else:
        st.caption("Upload a CSV to see dataset details here.")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    if st.button("Upload & Analyze"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
        response = requests.post(f"{API_URL}/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.columns = data["columns"]
            st.session_state.dtypes = data["dtypes"]
            st.session_state.num_rows = data["num_rows"]
            st.session_state.filename = uploaded_file.name
            st.session_state.history = []  # new dataset = fresh conversation
            st.success(f"Uploaded! {data['num_rows']} rows, {len(data['columns'])} columns.")
        else:
            st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")

if st.session_state.session_id:
    st.divider()

    # Example question buttons — built from REAL numeric/categorical columns
    cols = st.session_state.columns or []
    dtypes = st.session_state.dtypes or {}

    numeric_cols = [c for c in cols if "int" in dtypes.get(c, "") or "float" in dtypes.get(c, "")]
    categorical_cols = [c for c in cols if c not in numeric_cols]

    if numeric_cols and categorical_cols:
        st.caption("Try asking:")
        example_questions = [
            f"What's the average {numeric_cols[0]}?",
            f"Compare {numeric_cols[0]} by {categorical_cols[0]}",
            f"What's the distribution of {numeric_cols[0]}?",
        ]
        btn_cols = st.columns(len(example_questions))
        for btn_col, example in zip(btn_cols, example_questions):
            if btn_col.button(example, key=f"example_{example}"):
                st.session_state.question = example
                st.rerun()
    elif numeric_cols:
        st.caption(f"Try asking: What's the average {numeric_cols[0]}?")

    question = st.text_input("Ask a question about your data:", key="question")

    if st.button("Ask") and question:
        payload = {"session_id": st.session_state.session_id, "question": question}

        with st.spinner("Analyzing your data..."):
            response = requests.post(f"{API_URL}/ask", json=payload)

        if response.status_code == 200:
            result = response.json()
            # Save this Q&A pair to history instead of just rendering it once
            st.session_state.history.insert(0, {"question": question, "result": result})
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

    # Render conversation history, most recent first
    for entry in st.session_state.history:
        st.markdown(f"**Q: {entry['question']}**")
        result = entry["result"]

        if "answer" in result:
            st.write(result["answer"])
        else:
            with st.container(border=True):
                if "findings" in result:
                    st.markdown(result["findings"])
                if "chart" in result:
                    chart_dict = json.loads(result["chart"])
                    st.plotly_chart(chart_dict, use_container_width=True)
                elif "result" in result:
                    with st.expander("Show raw stats"):
                        st.json(result["result"])
        st.divider()