import pandas as pd
from tools import summarize_column, plot_trend

df = pd.read_csv("student_scores.csv")
print(summarize_column(df, "Math Score"))