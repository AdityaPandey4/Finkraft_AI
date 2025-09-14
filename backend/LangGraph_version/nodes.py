import os
import re
import json
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
from .profiler import get_profile_as_dict

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
logger = logging.getLogger(__name__)

def classify_query(state):
    """Classifies the user's query.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        AgentState: The updated state of the agent.
    """
    query = state["query"]
    chat_history = state["chat_history"][-2:]

    prompt = f"""You are a master at understanding user queries.
    Your task is to classify the user's query into one of the following categories:
    - "code_generation": The user is asking to perform some operation on the data (If the query is clear and actionable with all the required metrics to perform that task).
    - "suggestion": The user's query is vague or ambiguous (e.g., "top products" without specifying a metric).
    - "greeting": The user is just greeting.

    Here is the user's query: "{query}" 

    Here is the chat history:
    {chat_history}

    Please respond with one of the following categories:
    - code_generation
    - suggestion
    - greeting
    """

    response = llm.invoke(prompt)
    classification = response.content.strip()
    state["classification"] = classification
    return state

def code_generation(state):
    """Generates pandas code to transform the dataframe.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        AgentState: The updated state of the agent.
    """
    query = state["query"]
    df = state["dataframe"]
    profile = get_profile_as_dict(df)
    chat_history = state["chat_history"][-2:]

    prompt = f"""You are a Python pandas expert and a helpful data analyst.
    A user has provided a dataframe named 'df' and a query in natural language.
    Here is the data profile of the dataframe:
    {profile}

    User query: "{query}" 

    Chat History:
    {chat_history}

    Your task is to generate pandas code to transform the dataframe.
    The final result MUST be assigned to a variable named 'result_df'.
    After the main transformation, analyze the 'result_df' and generate a list of all suitable chart specifications in a 'charts' array.
    Provide a detailed but easy-to-understand explanation for a non-technical user.
    Return a single, valid JSON object.

    **JSON Output Specification:**
    - The JSON output must always have a 'type' field ('code').
    - For 'code' type, it must include a 'code' field with the pandas code.
    - It must also include a 'charts' array. For each suitable visualization, add a chart object to this array.
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
    
    """

    response = llm.invoke(prompt)
    # Use regex to extract the JSON string from the markdown
    json_match = re.search(r'```json\n(.*?)\n```', response.content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response.content

    try:
        response_dict = json.loads(json_str)
        if "code" not in response_dict:
            raise KeyError("The 'code' key is missing from the LLM response.")
        state["code"] = response_dict["code"]
        state["explanation"] = response_dict.get("explanation", "")
        state["charts"] = response_dict.get("charts", [])
        state["error"] = None
    except (json.JSONDecodeError, KeyError) as e:
        state["error"] = f"Invalid response from LLM: {e}"

    return state

def code_execution(state):
    """Executes the generated code.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        AgentState: The updated state of the agent.
    """
    if state.get("error"):
        return state
        
    code = state["code"]
    df = state["dataframe"]

    local_scope = {'df': df.copy(), 'pd': pd}
    try:
        exec(code, {}, local_scope)
        result_df = local_scope.get('result_df')
        if result_df is None:
            raise ValueError("Code did not produce a 'result_df' dataframe.")
        state["dataframe"] = result_df
        state["error"] = None
    except Exception as e:
        state["error"] = str(e)

    return state

def suggestion(state):
    """Generates suggestions for ambiguous queries.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        AgentState: The updated state of the agent.
    """
    query = state["query"]
    df = state["dataframe"]
    profile = get_profile_as_dict(df)
    chat_history = state["chat_history"][-2:]

    prompt = f"""You are a helpful data analyst. A user has provided a query that is ambiguous.
    Your task is to generate 2-3 specific, alternative query suggestions in **natural language** that are relevant to the user's query and the available data.
    For each suggestion, provide the refined **natural language query** and a short explanation of what it does.
    Return a single, valid JSON object.

    Here is the data profile of the dataframe:
    {profile}

    User's ambiguous query: "{query}"

    Here is the conversation history so far:
    {chat_history}

    **IMPORTANT**: The 'query' field in your response MUST be a question in plain English that the user could ask next. Do NOT generate SQL or Python code.

    **Example of an ambiguous query response (JSON):**
    {{
        "type": "suggestions",
        "suggestions": [
            {{"query": "Show top 5 products by units_sold", "explanation": "This will show the 5 products with the highest number of units sold."}},
            {{"query": "Show top 5 products by net_revenue", "explanation": "This will show the 5 products that generated the most net revenue."}}
        ]
    }}
    """

    response = llm.invoke(prompt)
    # Use regex to extract the JSON string from the markdown
    json_match = re.search(r'```json\n(.*?)\n```', response.content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response.content

    try:
        response_dict = json.loads(json_str)
        state["suggestions"] = response_dict["suggestions"]
        state["error"] = None
    except (json.JSONDecodeError, KeyError) as e:
        state["error"] = f"Invalid JSON response: {e}"

    return state


def insight_generation(state):
    """Generates a proactive insight based on the result.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        AgentState: The updated state of the agent.
    """
    if state.get("error"):
        return state
        
    query = state["query"]
    result_df = state["dataframe"]
    result_head = result_df.head().to_string()

    prompt = f"""You are a proactive data analyst. A user has just run a query and obtained a result.
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

    response = llm.invoke(prompt)
    # Use regex to extract the JSON string from the markdown
    json_match = re.search(r'```json\n(.*?)\n```', response.content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response.content

    try:
        response_dict = json.loads(json_str)
        state["insight"] = response_dict
        state["error"] = None
    except (json.JSONDecodeError, KeyError) as e:
        state["error"] = f"Invalid JSON response: {e}"

    return state

def generate_chat_summary(history: list) -> str:
    """
    Generates a summary of the chat history.
    """
    
    # Create a simplified history for the prompt
    simplified_history = []
    for event in history:
        simplified_history.append(f"User: {event['query']}")
        simplified_history.append(f"Assistant: {event['response'].get('explanation', '')}")
    
    conversation = "\n".join(simplified_history)

    prompt = f"""You are a helpful assistant. A user has had a conversation with a data analyst bot. 
    Your task is to provide a concise summary of the entire conversation.

    The conversation was as follows:
    {conversation}

    Please provide a summary of the key findings and the flow of the analysis.
    """
    response = llm.invoke(prompt)
    summary = response.content.strip()
    return summary
