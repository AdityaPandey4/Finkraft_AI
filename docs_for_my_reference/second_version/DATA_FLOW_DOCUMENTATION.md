# Data Flow Documentation: Finkraft Agent Framework

## 1. Introduction

This document provides a detailed, step-by-step description of the data flow within the Finkraft Data Explorer. It traces the journey of data from the moment a user uploads a file to the final rendering of a query's result, focusing on how state is managed across the frontend, backend, and the LangGraph agent.

---

## 2. High-Level Architecture

The system consists of four primary components:

1.  **Frontend (Streamlit):** The user interface for file uploads, chat interaction, and displaying results.
2.  **Backend API (FastAPI):** Handles HTTP requests, manages data, and orchestrates the agent.
3.  **Data Caching Layer:** An in-memory dictionary on the backend that stores the original user data and chat history, mapped by a unique session ID.
4.  **LangGraph Agent:** The core engine that interprets queries, performs operations, and generates results. It is a state machine that processes data within a well-defined graph.

---

## 3. Step-by-Step Data Flow

Here is the end-to-end process for a typical user interaction.

### Step 1: Initial Data Upload

1.  **User Action (Frontend):** The user selects a CSV file in the Streamlit UI.
2.  **API Request (Frontend -> Backend):** The frontend sends a `POST` request with the file data to the `/upload` endpoint on the FastAPI backend.
3.  **Data Caching (Backend):**
    *   The `/upload` endpoint receives the file.
    *   A unique session ID (`data_id`) is generated.
    *   The CSV is read into a pandas DataFrame.
    *   This original, pristine DataFrame is stored in an in-memory dictionary (`data_cache`) with the `data_id` as its key.
    *   An empty list is created in a separate `history_cache` for the same `data_id` to store the upcoming conversation.
4.  **API Response (Backend -> Frontend):** The backend returns a JSON object to the frontend containing the `data_id`, a profile of the data (column names, types, stats), and a preview of the first few rows.
5.  **UI Update (Frontend):** The frontend stores the `data_id` in its session state and displays the data profile to the user.

### Step 2: User Query

1.  **User Action (Frontend):** The user types a natural language query (e.g., "*Show total revenue by region*") into the chat input.
2.  **API Request (Frontend -> Backend):** The frontend sends a `POST` request to the `/process_query` endpoint, containing a JSON payload with the `query` string and the session `data_id`.
3.  **Agent State Preparation (Backend):**
    *   The `/process_query` function is invoked.
    *   It uses the `data_id` to retrieve the **original DataFrame** from the `data_cache`.
    *   It retrieves the entire chat history for that session from the `history_cache`.
    *   It constructs the initial **`AgentState`** dictionary. This object is the single source of truth for the agent's execution for this query. It is populated with the original dataframe, the user's query, and the chat history. Fields for results (like `code`, `explanation`, `charts`, `error`) are initialized to `None`.

### Step 3: Agent Execution (Inside LangGraph)

The `initial_state` object is passed to the compiled LangGraph application (`graph_app.invoke()`), which begins its execution.

1.  **Node 1: `classify_query` (Entry Point):**
    *   **Input:** The `AgentState`.
    *   **Process:** It creates a simplified string summary of the `chat_history` and uses an LLM to classify the user's `query` as either `code_generation`, `suggestion`, or `greeting`.
    *   **Output:** It updates the `classification` field in the `AgentState`.

2.  **Edge 1: Conditional Routing:** The graph inspects the `classification` field in the state and directs the flow to the next node. For this example, it moves to `code_generation`.

3.  **Node 2: `code_generation`:**
    *   **Input:** The `AgentState`.
    *   **Process:** It constructs a detailed prompt containing the data profile (from the original dataframe), the simplified chat history, and the current user query. It asks the LLM to generate a JSON object containing the `code` (pandas), an `explanation`, and `charts` specifications.
    *   **Output:** It updates the `code`, `explanation`, and `charts` fields in the `AgentState`.

4.  **Edge 2: Direct Flow:** The graph proceeds to the `code_execution` node.

5.  **Node 3: `code_execution`:**
    *   **Input:** The `AgentState`, which now contains the Python code to be run.
    *   **Process:** It executes the code string in a sandboxed environment where the original dataframe is available as `df`. The operation's result is assigned to a `result_df`.
    *   **Output:** It replaces the `dataframe` field in the `AgentState` with the `result_df`. If an error occurs, it populates the `error` field instead.

6.  **Edge 3: Conditional Flow:** The graph checks if an error occurred. Assuming success, it proceeds to the final node.

7.  **Node 4: `insight_generation` (Final Node):**
    *   **Input:** The `AgentState`, containing the newly generated `result_df`.
    *   **Process:** It sends the query and a preview of the result to the LLM and asks for a proactive insight and a suggested follow-up question.
    *   **Output:** It updates the `insight` field in the `AgentState`.

8.  **End of Graph:** The agent's execution is complete. It returns the final, fully populated `AgentState` object to the backend API function.

### Step 4: Response Processing and History Logging

1.  **Data Transformation (Backend):** The `process_query` function receives the final `AgentState` from the graph. It converts the pandas DataFrame object within the state into a JSON-serializable list of records.
2.  **History Logging (Backend):** A new `history_event` dictionary is created. This event contains the user's original query and a `response` object holding all the results from the agent: the explanation, charts, suggestions, insight, and the JSON-formatted dataframe with its columns. This complete event is appended to the `history_cache` for the current `data_id`.
3.  **API Response (Backend -> Frontend):** The backend function is now finished with its work. *Note: The frontend does not directly use the response from this API call for rendering.*

### Step 5: Rendering the Result

1.  **Fetch History (Frontend):** As soon as the `/process_query` call from Step 2 completes, the frontend immediately makes a new `POST` request to the `/history` endpoint.
2.  **Full History Retrieval (Backend -> Frontend):** The `/history` endpoint retrieves the complete, updated list of chat events from the `history_cache` and returns it as a JSON response.
3.  **UI Rerun (Frontend):** The frontend updates its session state with the new chat history. This action triggers a full page rerun in Streamlit.
4.  **Render from History (Frontend):** The `render_chat()` function is called. It iterates through the list of history events. For the most recent event, it accesses the `response` dictionary and uses the data within it (`explanation`, `charts`, `dataframe`, `columns`, etc.) to render the appropriate UI components—displaying the text, drawing the Plotly charts, and showing the resulting data table.
