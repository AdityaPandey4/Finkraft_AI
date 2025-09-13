# Data Explorer Application: Features & Technical Documentation

## 1. Introduction

This document provides a detailed overview of the features and technical implementation of the Data Explorer application. The application is designed to be an intuitive, conversational data analysis tool that allows non-technical users to upload a CSV dataset and explore it using natural language commands.

## 2. High-Level Architecture

The application follows a decoupled frontend-backend architecture:

-   **Frontend:** A [Streamlit](https://streamlit.io/) application (`frontend/app.py`) that provides the user interface. It is responsible for all UI rendering, user interaction, and communication with the backend.
-   **Backend:** A [FastAPI](https://fastapi.tiangolo.com/) server (`backend/llm_version/main.py`) that exposes a REST API. It handles all the heavy lifting, including data storage, query processing, and all interactions with the Large Language Model (LLM).

---

## 3. Feature Deep Dive

### 3.1. Automated Data Profiling

-   **What it is:** When a user uploads a new CSV file, the application automatically performs a quality check and displays a high-level summary of the dataset. This includes metrics like the number of rows and columns, duplicate row count, and memory usage, as well as a detailed breakdown of each column (data type, missing values, etc.).
-   **How it works:**
    1.  **Frontend:** The user uploads a CSV file via the `st.file_uploader` in the sidebar.
    2.  **Backend (`/upload`):** The frontend sends the file to the `/upload` endpoint. The backend creates a unique `data_id` for the session, reads the CSV into a pandas DataFrame, and stores it in an in-memory cache (`data_cache`).
    3.  **Profiling:** A profiling function (`profiler.py`) is called, which analyzes the DataFrame to calculate all the metrics (row count, column details, numeric stats, etc.).
    4.  **Response:** The backend returns the `data_id` and the generated profile data to the frontend.
    5.  **Frontend Display:** The frontend stores the `data_id` and profile in its session state and displays the profile information within an expandable section titled "📊 Data Profile & Quality Check".

### 3.2. Proactive "Insight" Suggestions

-   **What it is:** After a user's query is successfully executed, the application doesn't just wait for the next command. It proactively analyzes the result and suggests a relevant follow-up question or points out an interesting pattern as a clickable "insight."
-   **How it works:**
    1.  **Initial Query:** The user submits a query, which is processed by the backend's `/process_query` endpoint as usual.
    2.  **Backend (`llm_handler.py`):** After the LLM generates the pandas code and it is executed to produce a `result_df`, a second call is made to the LLM via the `generate_insights` function.
    3.  **Insight Generation:** This function provides the LLM with the original query and the head of the `result_df`. It prompts the LLM to act as a proactive analyst, find one interesting pattern, and formulate a follow-up question.
    4.  **Response:** The `/process_query` endpoint returns the main result (data, explanation, charts) and now also includes the generated `insight` object (containing the insight text and the follow-up query).
    5.  **Frontend Display:** The frontend checks for this `insight` object. If present, it displays the insight in an info box with a clickable button for the follow-up query, inviting the user to dig deeper with a single click.

### 3.3. Multi-Chart Tabbed Visualizations

-   **What it is:** Instead of showing only the single "best" chart for a query, the application now generates all suitable visualizations (Bar, Pie, Line, Scatter) and presents them in a clean, tabbed interface.
-   **How it works:**
    1.  **Backend (`llm_handler.py`):** The prompt sent to the LLM has been updated. It now instructs the model to return a `charts` array in its JSON response, containing specifications for *all* chart types that are appropriate for the resulting data.
    2.  **Backend (`main.py`):** The `/process_query` endpoint passes this `charts` array to the frontend.
    3.  **Frontend (`app.py`):**
        -   The frontend checks for the `charts_spec` list in the session state.
        -   It uses `st.tabs()` to dynamically create a tab for each chart specification in the list. The tab title is the chart type (e.g., "Bar", "Pie").
        -   Inside each tab, the corresponding Plotly Express function (`px.bar`, `px.pie`, etc.) is called to render the chart based on the spec for that tab.

### 3.4. Chat History and Enhanced Export

-   **What it is:** The application now functions as a chat, maintaining a complete history of the user's analysis session. This entire conversation, including data profiles, Q&A, insights, and charts, can be exported as a JSON, CSV, or a comprehensive Markdown file.
-   **How it works:**
    1.  **History Caching (Backend):**
        -   A new `history_cache` has been added to `data_tools.py`. For each `data_id`, it stores a list of all conversational events.
        -   After each call to `/process_query`, the user's query and the full response from the LLM are appended to this history list.
    2.  **Chat Interface (Frontend):**
        -   The frontend has been refactored to be a chat interface. It maintains a `chat_history` in its session state.
        -   After each query, it re-fetches the entire history from the new `/history` backend endpoint.
        -   The `render_chat` function iterates through the history and displays each user query and assistant response in a `st.chat_message` container, creating a familiar conversational flow.
    3.  **Export Functionality:**
        -   **JSON:** The "Export Chat as JSON" button in the sidebar uses `st.download_button` to directly serve the `chat_history` from the frontend's session state as a JSON file.
        -   **CSV & Markdown (Backend `/export`):**
            -   A new `/export/{data_id}/{format}` endpoint was created in `main.py`.
            -   The "Export Final Data as CSV" and "Export Summary as Markdown" buttons are links that point to this endpoint.
            -   If the format is `csv`, the backend retrieves the latest version of the DataFrame from the `data_cache` and returns it as a CSV file.
            -   If the format is `md`, the backend performs several steps: it retrieves the full chat history and the data profile, calls the LLM to generate a summary of the conversation (`generate_chat_summary`), and then uses the `markdown_generator.py` module to assemble the final Markdown file with the requested structure (Profile, Summary, and full Q&A with chart images).
