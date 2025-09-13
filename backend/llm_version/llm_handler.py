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
        - After the main transformation, analyze the 'result_df'. If the result is suitable for a chart, include a 'chart' object in your response. The chart should be a format compatible with Plotly Express.
        - Provide a detailed but easy-to-understand explanation for a non-technical user.
        - Return a single, valid JSON object.

    2.  **If the query is ambiguous** (e.g., "top products" without specifying a metric):
        - DO NOT generate code.
        - Generate 2-3 specific, alternative query suggestions. For each suggestion, provide the refined query and a short explanation of what it does.
        - Return a single, valid JSON object.

    **JSON Output Specification:**
    - The JSON output must always have a 'type' field ('code' or 'suggestions').
    - For 'code' type, it can optionally include a 'chart' object. 
    - For a bar chart, this should include 'type': 'bar', 'x_column', and 'y_column'.
    - For a pie chart, it should include 'type': 'pie', 'names_column' (for labels), and 'values_column'.
    - You can also optionally include a 'color_column' if it makes sense for the data (e.g., for continuous colors on a bar chart).

    **Example of a clear query response with a bar chart (JSON):**
    {{
        "type": "code",
        "code": "result_df = df.groupby('region')['net_revenue'].sum().reset_index()",
        "explanation": "I have calculated the total net revenue for each region.",
        "chart": {{
            "type": "bar",
            "x_column": "region",
            "y_column": "net_revenue",
            "color_column": "net_revenue"
        }}
    }}

    **Example of a clear query response with a pie chart (JSON):**
    {{
        "type": "code",
        "code": "result_df = df[df['segment'] == 'Consumer'].groupby('product_category')['units_sold'].sum().reset_index()",
        "explanation": "I have calculated the total units sold for each product category within the Consumer segment.",
        "chart": {{
            "type": "pie",
            "names_column": "product_category",
            "values_column": "units_sold"
        }}
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
            chart_spec = response_dict.get("chart")
            logger.info(f"Code to execute:\n{code_to_execute}")

            if not code_to_execute:
                raise ValueError("LLM did not return any code to execute.")

            local_scope = {'df': df.copy(), 'pd': pd}
            exec(code_to_execute, {}, local_scope)
            
            result_df = local_scope.get('result_df')
            if result_df is None:
                raise ValueError("Code did not produce a 'result_df' dataframe.")
            
            logger.info("Code executed successfully. Resulting dataframe preview:\n" + result_df.head().to_string())
            return {"type": "code", "dataframe": result_df, "explanation": explanation, "chart": chart_spec}
        
        elif response_type == 'suggestions':
            suggestions = response_dict.get("suggestions")
            logger.info(f"Returning suggestions: {suggestions}")
            return {"type": "suggestions", "suggestions": suggestions}
        
        else:
            raise ValueError(f"LLM returned an invalid response type: {response_type}")

    except Exception as e:
        logger.info(f"Error in llm_handler: {e}", exc_info=True)
        return {"type": "error", "explanation": f"An error occurred in the LLM handler: {e}"}