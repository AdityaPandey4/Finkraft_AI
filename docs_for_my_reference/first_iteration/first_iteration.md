# Project: Data Explorer with Natural Commands - Iteration 1

## 1. Project Understanding

The goal of this project is to build a web application that allows non-technical users to upload a CSV dataset and explore it using natural language commands. The application should be intuitive, providing clear explanations for its actions and offering suggestions when user queries are ambiguous. This avoids the steep learning curve of traditional Business Intelligence (BI) tools.

The final deliverable for this iteration will be a Streamlit application that serves as the frontend, powered by a FastAPI backend that handles all the data processing and AI logic.

### Key Features:
- **Natural Language Querying:** Users can type requests in plain English (e.g., "show me total sales by region").
- **Interactive Clarification:** If a query is vague (e.g., "show top products"), the app will present the user with multiple interpretations to choose from.
- **Transparent Operations:** The app will always explain what action it has performed in simple, human-readable terms.
- **Core Data Operations:** The system must support fundamental operations like filtering, sorting, grouping, pivoting, and aggregation.
- **Visualization:** The application will display results in tables and will also be capable of generating charts when appropriate.
- **Data Export:** Users will be able to download the current view of their data as a CSV file.

## 2. Architecture Decision: LLM vs. AI Agents

We considered two primary architectural approaches:

1.  **Direct LLM Integration:** Using a Large Language Model (LLM) to directly translate natural language into executable Python (`pandas`) code. While powerful, this approach was deemed too risky due to the security vulnerabilities associated with executing dynamically generated code (i.e., using `exec()`). It also poses reliability challenges.

2.  **AI Agent Framework (`crewai`):** Creating a "crew" of specialized AI agents, each with a specific role (e.g., analyzing, executing, explaining). This approach is more secure and robust because the agents' capabilities are restricted to a predefined "toolkit" of safe, developer-written functions. It aligns perfectly with the project hint to use a "configurable operation library."

**Conclusion:** We have chosen to proceed with the **AI Agent Framework**. This provides industrial-level standards for security, modularity, and scalability, which is ideal for this project and makes future iterations much simpler.

## 3. Application Flow

The application is architecturally decoupled into a frontend and a backend.

1.  **File Upload:**
    *   **Frontend (Streamlit):** The user uploads a CSV file. The frontend sends the file content to the backend.
    *   **Backend (FastAPI):** The backend receives the data, stores it in an in-memory cache, and returns a unique `data_id` to the frontend.
    *   **Frontend:** The app stores this `data_id` for the duration of the session.

2.  **User Query:**
    *   **Frontend:** The user types a natural language query (e.g., "show me top 5 products by sales"). The app sends the query and the `data_id` to the `/process_query` endpoint on the backend.

3.  **Backend Processing (AI Crew):**
    *   The backend retrieves the user's DataFrame using the `data_id`.
    *   The **Analyst Agent** analyzes the query.
    *   **If the query is ambiguous:** The agent generates several interpretations (e.g., "Top 5 by units sold?" or "Top 5 by revenue?"). The backend returns these options to the frontend. The frontend displays them as buttons. The user clicks one, which triggers a new, more specific query to the backend.
    *   **If the query is clear:** The Analyst Agent determines the correct tool to use from its toolkit (e.g., `sort_tool`) and the required parameters.

4.  **Execution and Explanation:**
    *   The instruction is passed to the **Executor Agent**, which runs the predefined `sort_tool` function on the data.
    *   The instruction is also passed to the **Explanation Agent**, which generates a human-readable summary (e.g., "I have sorted the data to show the top 5 products by sales.").
    *   The **Analyst Agent** may also determine that a chart is a good way to visualize the new data and will include plotting information in the response.

5.  **Displaying Results:**
    *   **Backend:** The API returns a single JSON object containing the new DataFrame, the explanation text, and optional chart information.
    *   **Frontend:** The Streamlit app receives the response and updates the UI: it displays the new data in an interactive table (`st.dataframe`), shows the explanation in a sidebar (`st.sidebar.info`), and renders any charts (`st.bar_chart`).

6.  **Data Export:**
    *   The user can click an "Export" button (`st.download_button`) at any time. This action is handled entirely by the frontend, which converts the currently displayed DataFrame into a CSV file for download.

## 4. Iteration 1 Plan

1.  **Project Scaffolding:** Create the directory structure (`frontend/`, `backend/`) and files (`app.py`, `main.py`, `crew.py`, `data_tools.py`, `requirements.txt`, `.gitignore`, `first_iteration.md`).
2.  **Environment Setup:** Populate `requirements.txt` with all necessary libraries.
3.  **API Key Configuration:** Guide the user to set up a `.env` file for their LLM API key.
4.  **Backend Development:**
    *   Implement the safe data manipulation functions (tools) in `backend/data_tools.py`.
    *   Define the agents (Analyst, Executor, Explainer) and the main task in `backend/crew.py`.
    *   Set up the FastAPI server in `backend/main.py` with the `/load_data` and `/process_query` endpoints.
5.  **Frontend Development:**
    *   Build the complete user interface in `frontend/app.py`.
    *   Implement the logic for file uploading, sending requests to the backend, and dynamically displaying the returned data, charts, explanations, and suggestions.
    *   Add the client-side data export functionality.
