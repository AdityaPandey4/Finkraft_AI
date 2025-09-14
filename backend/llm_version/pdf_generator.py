from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import pandas as pd
import plotly.express as px
import io

def create_chat_summary_pdf(history: list, data_id: str):
    """
    Generates a PDF summary of the chat history.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Chat History Summary", styles['h1']))
    story.append(Spacer(1, 0.2*inch))

    # Chat history
    for event in history:
        story.append(Paragraph(f"<b>User:</b> {event['query']}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))

        response = event['response']
        response_type = response.get("type")

        if response_type == "code":
            story.append(Paragraph(f"<b>Assistant:</b> {response.get('explanation', '')}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

            if response.get("charts"):
                for i, spec in enumerate(response["charts"]):
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
                            img_buffer = io.BytesIO()
                            fig.write_image(img_buffer, format="png")
                            img_buffer.seek(0)
                            story.append(Image(img_buffer, width=6*inch, height=4*inch))
                            story.append(Spacer(1, 0.1*inch))

                    except Exception as e:
                        story.append(Paragraph(f"Could not create chart: {e}", styles['Normal']))

        elif response_type == "suggestions":
            story.append(Paragraph("<b>Assistant:</b> Your query was a bit vague. Here are some suggestions:", styles['Normal']))
            for suggestion in response['suggestions']:
                story.append(Paragraph(f"- {suggestion['query']}: {suggestion['explanation']}", styles['Normal']))
        
        story.append(Spacer(1, 0.2*inch))

    doc.build(story)
    buffer.seek(0)
    return buffer
