# AI Data Analyst

Upload a CSV, ask questions about it in plain English, get back a chart and a
plain-English summary of the findings.

Built as a portfolio project to explore LLM tool-calling: instead of letting
an AI model generate and execute arbitrary code against user data, this app
gives Claude a small, fixed set of vetted analysis tools to choose from. The
model decides *what* to run and *with what parameters* — the actual
computation always happens in real Python code, never inside the model.

## How it works

```
Upload a CSV
      │
      ▼
Ask a question in plain English
      │
      ▼
Claude picks the right analysis tool
(trend chart / category comparison / distribution / column summary)
      │
      ▼
The real computation runs in pandas — Claude never executes code
      │
      ▼
Claude writes a plain-English summary of the actual computed results
      │
      ▼
You get a chart + an insight, not just numbers
```

## Example

> **Q: "Which neighborhood was the best at math?"**
>
> *Eastside had the highest average math score at 83.95, notably ahead of all
> other neighborhoods. Downtown came in second at 69.7, while Southpark had
> the lowest average math score at 56.6 — about 27 points behind Eastside.*
>
> *(interactive bar chart rendered below)*

## Tech stack

- **Backend:** FastAPI, pandas, Plotly
- **AI:** Claude (Anthropic API) — tool-calling for analysis selection, a
  second call for the plain-English findings summary
- **Frontend:** Streamlit

## Architecture

- `POST /upload` — parses the CSV, returns a schema (columns, dtypes, sample
  rows), stores the dataset in memory against a session ID
- `POST /ask` — takes a question + session ID:
  1. Sends the dataset schema + question + tool definitions to Claude
  2. Claude chooses one of four tools and generates its arguments
  3. The corresponding Python function actually runs the analysis
  4. The real computed result is sent back to Claude to generate a short,
     plain-English summary
  5. Returns the chart (or stats) and the summary together

**Four analysis tools**, each mapped to a different kind of question:
| Tool | Use for |
|---|---|
| `plot_trend` | "How did X change over time?" |
| `compare_categories` | "Compare X across groups" / "Which Y is highest?" |
| `distribution` | "What's the spread of X?" |
| `summarize_column` | "What's the average/max/min of X?" |

If a question doesn't match any of the four (e.g. "what's the capital of
France?"), Claude answers directly instead of forcing an irrelevant tool.

## Running it locally

**1. Clone the repo and set up a virtual environment**
```bash
git clone https://github.com/Varun203420/AI-Data-Analyst.git
cd AI-Data-Analyst
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your Anthropic API key**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-key-here
```
Get a key at [console.anthropic.com](https://console.anthropic.com).

**4. Run the backend**
```bash
uvicorn main:app --reload --port 8001
```

**5. In a separate terminal, run the frontend**
```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. Upload a CSV and start asking
questions.

## Known limitations (MVP scope)

This is intentionally scoped as an MVP to prove the core architecture works
end to end. Not yet included:
- Sessions are stored in memory and reset when the server restarts
- No authentication or rate limiting
- No multi-turn conversation — each question is independent
- Fixed set of 4 analysis tools rather than open-ended code generation

## Roadmap

- [ ] Sandboxed code-generation mode for questions outside the 4 fixed tools
- [ ] Multi-turn follow-up questions ("now break that down by region")
- [ ] Outlier/anomaly flagging in the data before analysis
- [ ] Multi-file support with joins across datasets
- [ ] Persistent session storage (Redis)
- [ ] Export findings + chart as a PDF report
