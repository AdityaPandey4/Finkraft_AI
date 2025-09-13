import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
import logging

# Setup logging
logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv()

# Configure the generative AI model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')

def generate_chat_summary(history: list) -> str:
    """
    Generates a summary of the chat history.
    """
    logger.info("Generating chat summary...")
    
    # Create a simplified history for the prompt
    simplified_history = []
    for event in history:
        simplified_history.append(f"User: {event['query']}")
        simplified_history.append(f"Assistant: {event['response'].get('explanation', '')}")
    
    conversation = "\n".join(simplified_history)

    prompt = f"""
    You are a helpful assistant. A user has had a conversation with a data analyst bot. 
    Your task is to provide a concise summary of the entire conversation.

    The conversation was as follows:
    {conversation}

    Please provide a summary of the key findings and the flow of the analysis.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error generating chat summary: {e}", exc_info=True)
        return "Could not generate summary."

def generate_insights(query: str, result_df: pd.DataFrame) -> dict:
    """
    Analyzes the result of a query and generates a proactive insight.
    """
    logger.info("Generating insights for the query result...")
    result_head = result_df.head().to_string()

    prompt = f"""
    You are a proactive data analyst. A user has just run a query and obtained a result.
    Original user query: "{query}"
    
    The first 5 rows of the result dataframe ('result_df') are:
    {result_head}

    Your task is to find one interesting insight from this result and suggest a logical next question a user might want to ask.
    - The insight should be a short, interesting observation about the data.
    - The follow-up query must be a clear, specific, and actionable question in natural language.

    Return a single, valid JSON object with two keys: "insight" and "follow_up_query".

    Example Response (JSON):
    {{
        "insight": "Sales in the 'North' region are 50% higher than the average. Would you like to see a breakdown of product categories for this region?",
        "follow_up_query": "Show a breakdown of product categories for the North region"
    }}
    """
    try:
        logger.info("Sending insight prompt to LLM...")
        response = model.generate_content(prompt)
        raw_response_text = response.text
        logger.info(f"Raw insight response from LLM:\n{raw_response_text}")

        json_match = re.search(r'```json\n(.*?)\n```', raw_response_text, re.DOTALL)
        if not json_match:
            json_str = raw_response_text
        else:
            json_str = json_match.group(1)

        insight_dict = json.loads(json_str)
        logger.info(f"Parsed insight dictionary: {insight_dict}")
        
        if "insight" in insight_dict and "follow_up_query" in insight_dict:
            return insight_dict
        else:
            return None

    except Exception as e:
        logger.error(f"Error generating insight: {e}", exc_info=True)
        return None

def process_query_with_llm(query: str, df: pd.DataFrame) -> dict:
    """
    Processes the user query by generating and executing pandas code using an LLM.
    """
    logger.info(f"Processing query: '{query}'")
    df_head = df.head().to_string()
    
    prompt = f"""
    You are a Python pandas expert and a helpful data analyst. A user has provided a dataframe named 'df' and a query in natural language.
    The first 5 rows of the dataframe are:
    {df_head}

    User query: "{query}"

    Your task is to first determine if the query is ambiguous.
    
    1.  **If the query is clear and actionable:**
        - Generate pandas code to transform the dataframe. The final result MUST be assigned to a variable named 'result_df'.
        - After the main transformation, analyze the 'result_df' and generate a list of all suitable chart specifications in a 'charts' array. 
        - Provide a detailed but easy-to-understand explanation for a non-technical user.
        - Return a single, valid JSON object.

    2.  **If the query is ambiguous** (e.g., "top products" without specifying a metric):
        - DO NOT generate code.
        - Generate 2-3 specific, alternative query suggestions. For each suggestion, provide the refined query and a short explanation of what it does.
        - Return a single, valid JSON object.

    **JSON Output Specification:**
    - The JSON output must always have a 'type' field ('code' or 'suggestions').
    - For 'code' type, it must include a 'charts' array. For each suitable visualization, add a chart object to this array.
    - **Bar Chart**: Use for categorical comparisons. Include 'type': 'bar', 'x_column', and 'y_column'.
    - **Pie Chart**: Use for showing parts of a whole (if categories are less than 6). Include 'type': 'pie', 'names_column' (for labels), and 'values_column'.
    - **Line Chart**: Use for time-series data. If the x-axis is a date/time, use a line chart. Include 'type': 'line', 'x_column', and 'y_column'.
    - **Scatter Plot**: Use to show the relationship between two numerical variables. Include 'type': 'scatter', 'x_column', and 'y_column'.
    - You can also optionally include a 'color_column' if it makes sense for the data.

    **Example of a response with multiple charts (JSON):**
    {{
        "type": "code",
        "code": "result_df = df.groupby('region')['net_revenue'].sum().reset_index()",
        "explanation": "I have calculated the total net revenue for each region.",
        "charts": [
            {{
                "type": "bar",
                "x_column": "region",
                "y_column": "net_revenue"
            }},
            {{
                "type": "pie",
                "names_column": "region",
                "values_column": "net_revenue"
            }}
        ]
    }}

    **Example of an ambiguous query response (JSON):**
    {{
        "type": "suggestions",
        "suggestions": [
            {{"query": "Show top 5 products by units_sold", "explanation": "This will show the 5 products with the highest number of units sold."}},
            {{"query": "Show top 5 products by net_revenue", "explanation": "This will show the 5 products that generated the most net revenue."}}
        ]
    }}
    """

    try:
        logger.info("Sending prompt to LLM...")
        response = model.generate_content(prompt)
        raw_response_text = response.text
        logger.info(f"Raw response from LLM:\n{raw_response_text}")
        
        json_match = re.search(r'```json\n(.*?)\n```', raw_response_text, re.DOTALL)
        if not json_match:
            json_str = raw_response_text
        else:
            json_str = json_match.group(1)
        
        logger.info(f"Cleaned JSON string:\n{json_str}")
        response_dict = json.loads(json_str)
        logger.info(f"Parsed response dictionary: {response_dict}")

        response_type = response_dict.get("type")

        if response_type == 'code':
            code_to_execute = response_dict.get("code")
            explanation = response_dict.get("explanation", "No explanation provided.")
            charts_spec = response_dict.get("charts")
            logger.info(f"Code to execute:\n{code_to_execute}")

            if not code_to_execute:
                raise ValueError("LLM did not return any code to execute.")

            local_scope = {'df': df.copy(), 'pd': pd}
            exec(code_to_execute, {}, local_scope)
            
            result_df = local_scope.get('result_df')
            if result_df is None:
                raise ValueError("Code did not produce a 'result_df' dataframe.")
            
            logger.info("Code executed successfully. Resulting dataframe preview:\n" + result_df.head().to_string())
            
            # Generate proactive insight
            insight = generate_insights(query, result_df)

            return {"type": "code", "dataframe": result_df, "explanation": explanation, "charts": charts_spec, "insight": insight}
        
        elif response_type == 'suggestions':
            suggestions = response_dict.get("suggestions")
            logger.info(f"Returning suggestions: {suggestions}")
            return {"type": "suggestions", "suggestions": suggestions}
        
        else:
            raise ValueError(f"LLM returned an invalid response type: {response_type}")

    except Exception as e:
        logger.info(f"Error in llm_handler: {e}", exc_info=True)
        return {"type": "error", "explanation": f"An error occurred in the LLM handler: {e}"}