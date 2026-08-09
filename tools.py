import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ---------- Tool schemas (what we send to Claude) ----------

TOOLS = [
    {
        "name": "plot_trend",
        "description": "Plot a line chart showing how a numeric value changes across another column, typically over time or an ordered sequence. Use for questions about trends, changes over time, or 'how X changed'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x_col": {"type": "string", "description": "Column for the x-axis, usually a date/time or ordered column"},
                "y_col": {"type": "string", "description": "Numeric column for the y-axis"},
            },
            "required": ["x_col", "y_col"],
        },
    },
    {
        "name": "compare_categories",
        "description": "Plot a bar chart comparing an aggregated numeric value across categories. Use for questions comparing groups, e.g. 'compare X by Y', 'which category has the highest Z'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cat_col": {"type": "string", "description": "Categorical column to group by"},
                "value_col": {"type": "string", "description": "Numeric column to aggregate"},
                "agg": {
                    "type": "string",
                    "enum": ["mean", "sum", "count", "max", "min"],
                    "description": "Aggregation to apply per category",
                },
            },
            "required": ["cat_col", "value_col", "agg"],
        },
    },
    {
        "name": "distribution",
        "description": "Plot a histogram showing the distribution/spread of a single numeric column. Use for questions like 'what's the spread of X', 'show me the distribution of Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "col": {"type": "string", "description": "Numeric column to show the distribution of"},
            },
            "required": ["col"],
        },
    },
    {
        "name": "summarize_column",
        "description": "Return plain summary statistics (mean, median, min, max, etc.) for a column, with no chart. Use for direct factual questions like 'what's the average X', 'what's the max Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "col": {"type": "string", "description": "Column to summarize"},
            },
            "required": ["col"],
        },
    },
]


# ---------- Tool implementations (what actually runs) ----------

def plot_trend(df: pd.DataFrame, x_col: str, y_col: str):
    _validate_columns(df, [x_col, y_col])
    fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
    return fig


def compare_categories(df: pd.DataFrame, cat_col: str, value_col: str, agg: str):
    _validate_columns(df, [cat_col, value_col])
    grouped = df.groupby(cat_col)[value_col].agg(agg).reset_index()
    fig = px.bar(grouped, x=cat_col, y=value_col, title=f"{agg} of {value_col} by {cat_col}")
    return fig


def distribution(df: pd.DataFrame, col: str):
    _validate_columns(df, [col])
    fig = px.histogram(df, x=col, title=f"Distribution of {col}")
    return fig


def summarize_column(df: pd.DataFrame, col: str):
    _validate_columns(df, [col])
    series = df[col]
    if pd.api.types.is_numeric_dtype(series):
        return {
            "column": col,
            "mean": float(series.mean()),
            "median": float(series.median()),
            "min": float(series.min()),
            "max": float(series.max()),
            "std": float(series.std()),
            "count": int(series.count()),
        }
    else:
        return {
            "column": col,
            "unique_values": int(series.nunique()),
            "most_common": series.value_counts().head(3).to_dict(),
            "count": int(series.count()),
        }


def _validate_columns(df: pd.DataFrame, cols: list[str]):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Column(s) not found in dataset: {missing}")


# Dispatch table: maps tool name -> function
TOOL_FUNCTIONS = {
    "plot_trend": plot_trend,
    "compare_categories": compare_categories,
    "distribution": distribution,
    "summarize_column": summarize_column,
}