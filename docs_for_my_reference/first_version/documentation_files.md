
# Project File Documentation

This document provides an overview of each file used in the Data Explorer project and its specific purpose.

## Project Structure

```
.
├── backend/
│   ├── main.py
│   ├── llm_handler.py
│   └── data_tools.py
├── frontend/
│   └── app.py
├── .env
├── .gitignore
└── requirements.txt
```

---

## File Descriptions

### Root Directory

*   **`requirements.txt`**
    *   **Purpose:** Lists all the external Python libraries and dependencies required to run the project (e.g., `fastapi`, `streamlit`, `pandas`, `plotly`). This file allows for a consistent and reproducible environment setup using `pip install -r requirements.txt`.

*   **`.env`**
    *   **Purpose:** Stores environment variables, most importantly the `GOOGLE_API_KEY` needed to authenticate with the Google Generative AI service. This file is kept separate from the code to avoid exposing sensitive keys in version control.

*   **`.gitignore`**
    *   **Purpose:** Specifies which files and directories should be ignored by the Git version control system. This includes environment files (`.env`), Python cache (`__pycache__`), and other non-essential or sensitive files.

### `backend/` Directory

This directory contains the complete server-side logic for the application.

*   **`main.py`**
    *   **Purpose:** This is the main entry point for our backend. It uses the **FastAPI** framework to create a web server and define the API endpoints that the frontend communicates with.
    *   **Key Endpoints:**
        *   `/upload`: Handles CSV file uploads from the user.
        *   `/process_query`: Receives natural language queries, orchestrates the analysis, and sends back the results.
    *   **Functionality:** It manages web traffic, handles request and response validation, and calls the appropriate functions from other backend modules.

*   **`llm_handler.py`**
    *   **Purpose:** This is the brain of the application. It is responsible for all interactions with the Large Language Model (Google's Gemini).
    *   **Functionality:**
        1.  **Prompt Engineering:** Dynamically constructs detailed prompts for the LLM, including the user's query, the structure of the data, and instructions on how to respond.
        2.  **AI Interaction:** Sends the prompt to the Google AI service.
        3.  **Response Parsing:** Parses the JSON response from the LLM.
        4.  **Code Execution:** If the LLM returns `pandas` code, this module executes it in a controlled environment.
        5.  **Logic Handling:** Determines whether a query is clear or ambiguous and directs the response flow accordingly (providing either data or suggestions).

*   **`data_tools.py`**
    *   **Purpose:** A utility module for managing the user's data during a session.
    *   **Functionality:** It implements an in-memory cache (a Python dictionary) that stores the pandas DataFrame uploaded by the user. It provides functions to save a DataFrame with a unique `data_id` and retrieve it later, allowing the user's data to persist between queries within a single session.

### `frontend/` Directory

This directory contains the code for the user interface.

*   **`app.py`**
    *   **Purpose:** This file defines the entire user interface and user experience using the **Streamlit** framework.
    *   **Functionality:**
        1.  **UI Rendering:** Creates all the visual components the user interacts with, such as the title, file uploader, text input boxes, buttons, and data tables.
        2.  **State Management:** Uses `st.session_state` to keep track of the user's data, the current explanation, and any active suggestions.
        3.  **API Communication:** Sends requests to the backend (e.g., when a file is uploaded or a query is submitted).
        4.  **Dynamic Display:** Receives data from the backend and dynamically updates the UI to show new data tables, Plotly charts, explanations, and clarification suggestions.
