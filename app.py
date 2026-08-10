import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8001"

st.set_page_config(page_title="AI Data Analyst", layout="wide")
st.title("AI Data Analyst")
st.caption("Upload a CSV, ask questions in plain English, get charts and insights.")

# Persist session_id and schema across reruns
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "columns" not in st.session_state:
    st.session_state.columns = None

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    if st.button("Upload & Analyze"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
        response = requests.post(f"{API_URL}/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.columns = data["columns"]
            st.success(f"Uploaded! {data['num_rows']} rows, columns: {', '.join(data['columns'])}")
        else:
            st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")

if st.session_state.session_id:
    st.divider()
    question = st.text_input("Ask a question about your data:")

    if st.button("Ask") and question:
        payload = {"session_id": st.session_state.session_id, "question": question}
        response = requests.post(f"{API_URL}/ask", json=payload)

        if response.status_code == 200:
            result = response.json()

            if "answer" in result:
                st.write(result["answer"])
            else:
                if "findings" in result:
                    st.markdown(f"**{result['findings']}**")
                if "chart" in result:
                    chart_dict = json.loads(result["chart"])
                    st.plotly_chart(chart_dict, use_container_width=True)
                elif "result" in result:
                    with st.expander("Show raw stats"):
                        st.json(result["result"])
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")