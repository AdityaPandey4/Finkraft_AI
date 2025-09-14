
# Application Workflow Documentation

This document explains the end-to-end workflow of the Data Explorer application, from uploading a file to receiving an answer.

## Overall Architecture

The application consists of two main parts:

1.  **Frontend:** A **Streamlit** web application that the user interacts with.
2.  **Backend:** A **FastAPI** web server that handles all the data processing and AI-powered logic.

---

## Step 1: File Upload and Initialization

1.  **User Action:** The user visits the Streamlit application and is greeted by a file uploader in the sidebar.
2.  **File Upload (Frontend):** The user selects a CSV file. The frontend shows a spinner while it processes the upload.
3.  **Backend Request (Frontend -> Backend):** The frontend sends the raw CSV file to the `/upload` endpoint on the FastAPI backend.
4.  **Data Caching (Backend):**
    *   The `/upload` endpoint in `main.py` receives the file.
    *   It calls the `load_csv_from_upload` function in `data_tools.py`.
    *   This function reads the CSV into a pandas DataFrame, stores it in an in-memory dictionary (`data_cache`), and generates a unique `data_id` for this session.
    *   The backend returns this `data_id` to the frontend.
5.  **UI Update (Frontend):**
    *   The frontend receives the `data_id` and stores it in the session state (`st.session_state`).
    *   To provide an immediate preview, the frontend also reads the CSV file (after rewinding it with `.seek(0)`) into its own session state.
    *   The main application area appears, showing the full uploaded dataset in a table and a text input box for queries.

---

## Step 2: Query Processing

This step describes the main interactive loop of the application and has two primary paths depending on the user's query.

### Path A: The Query is Clear

1.  **User Action:** The user types a clear, specific query (e.g., "show total sales by region") and clicks "Ask".
2.  **Backend Request (Frontend -> Backend):** The frontend sends a JSON object containing the `data_id` and the query string to the `/process_query` endpoint.
3.  **Data Retrieval (Backend):** The backend retrieves the correct DataFrame from the `data_cache` using the `data_id`.
4.  **LLM Prompting (Backend):**
    *   The `llm_handler.py` module constructs a detailed prompt for the AI model.
    *   This prompt includes the user's query, the first few rows of the DataFrame (to give the model context), and specific instructions to return a JSON object containing executable `pandas` code, a detailed explanation, and an optional chart specification.
5.  **LLM Response (AI -> Backend):** The LLM processes the prompt and returns a JSON object, for example:
    ```json
    {
        "type": "code",
        "code": "result_df = df.groupby('region')['net_revenue'].sum().reset_index()",
        "explanation": "I have calculated the total net revenue for each region.",
        "chart": {
            "type": "bar",
            "x_column": "region",
            "y_column": "net_revenue"
        }
    }
    ```
6.  **Code Execution (Backend):**
    *   `llm_handler.py` parses the JSON.
    *   It executes the `pandas` code from the `code` field. The result is expected to be saved in a `result_df` variable.
7.  **Backend Response (Backend -> Frontend):** The `main.py` endpoint sends a final JSON payload to the frontend, containing the new data (as a list of records), the column names, the detailed explanation, and the chart specification.
8.  **UI Update (Frontend):**
    *   The frontend receives the response.
    *   It displays the detailed explanation in the main area.
    *   It renders a new **Plotly** chart using the provided chart specification.
    *   It displays the new data in an interactive table below the chart.

### Path B: The Query is Vague

1.  **User Action:** The user types a vague query (e.g., "show top products") and clicks "Ask".
2.  **Backend & LLM Interaction:** The process is the same as steps 2-4 above.
3.  **LLM Response (AI -> Backend):** Because the query is ambiguous, the LLM follows its instructions and returns a different JSON structure:
    ```json
    {
        "type": "suggestions",
        "suggestions": [
            {"query": "Show top 5 products by units_sold", "explanation": "This will show the 5 products with the highest number of units sold."},
            {"query": "Show top 5 products by net_revenue", "explanation": "This will show the 5 products that generated the most net revenue."}
        ]
    }
    ```
4.  **Backend Response (Backend -> Frontend):** The backend simply forwards this suggestion structure to the frontend.
5.  **UI Update (Frontend):**
    *   The frontend detects the `suggestions` type.
    *   It displays a warning message (💡 "Your query is a bit vague...").
    *   It then iterates through the list of suggestions, displaying each one's `explanation` and a clickable button containing the refined `query`.
6.  **User Clarification:** The user reads the explanations and clicks the button that matches their intent.
7.  **New Request:** Clicking the button immediately triggers a new request to the `/process_query` endpoint, this time with the clear, specific query from the button.
8.  **Resolution:** The workflow now continues from **Path A, Step 2**, leading to a final result with a chart and data table.
