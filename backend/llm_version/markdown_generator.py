import pandas as pd
import plotly.express as px
import io
import os

def create_chat_summary_markdown(profile: dict, summary: str, history: list, data_id: str) -> str:
    """
    Generates a Markdown summary of the chat history.
    """
    
    col_details_list = []
    for d in profile['column_details']:
        col_details_list.append(f"| {d['Column']} | {d['Non-Null Count']} | {d['Null Count']} | {d['Data Type']} |")
    col_details = "\n".join(col_details_list)

    md = f"""
# Chat History Summary

## Data Profile & Quality Check

### Dataset Summary

| Metric | Value |
|---|---|
| Number of Rows | {profile['dataset_summary']['Number of Rows']} |
| Number of Columns | {profile['dataset_summary']['Number of Columns']} |
| Duplicate Rows | {profile['dataset_summary']['Duplicate Rows']} |
| Memory Usage | {profile['dataset_summary']['Memory Usage']} |

### Column Details

| Column | Non-Null Count | Null Count | Data Type |
|---|---|---|---|
{col_details}

### Numeric Column Statistics

{pd.DataFrame(profile['numeric_summary']).to_markdown()}

## Conversation Summary

{summary}

## Full Chat History

"""

    # Chat history
    for i, event in enumerate(history):
        md += f"### Q: {event['query']}\n\n"

        response = event['response']
        response_type = response.get("type")

        if response_type == "code":
            md += f"**A:** {response.get('explanation', '')}\n\n"

            if response.get("charts"):
                for j, spec in enumerate(response["charts"]):
                    chart_df = pd.DataFrame(response['dataframe'], columns=response['columns'])
                    fig = None
                    try:
                        if spec['type'] == 'bar':
                            fig = px.bar(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                        elif spec['type'] == 'pie':
                            fig = px.pie(chart_df, names=spec['names_column'], values=spec['values_column'])
                        elif spec['type'] == 'line':
                            fig = px.line(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                        elif spec['type'] == 'scatter':
                            fig = px.scatter(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                        
                        if fig:
                            img_path = f"/tmp/chart_{data_id}_{i}_{j}.png"
                            fig.write_image(img_path, format="png")
                            md += f"![{spec['type']} chart]({img_path})\n\n"

                    except Exception as e:
                        md += f"Could not create chart: {e}\n\n"

        elif response_type == "suggestions":
            md += "**A:** Your query was a bit vague. Here are some suggestions:\n\n"
            for suggestion in response['suggestions']:
                md += f"- **{suggestion['query']}:** {suggestion['explanation']}\n"
        
        md += "\n---\n\n"

    return md
