import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import json
import subprocess
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Finkraft Data Explorer",
    page_icon="🤖",
    layout="wide"
)

# --- Backend URL ---
BACKEND_URL = "http://127.0.0.1:8000"

# --- Session State Initialization ---
def init_session_state():
    if 'data_id' not in st.session_state:
        st.session_state.data_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'profile' not in st.session_state:
        st.session_state.profile = None
    if 'markdown_preview' not in st.session_state:
        st.session_state.markdown_preview = None
    if 'server_process' not in st.session_state:
        st.session_state.server_process = None

init_session_state()

# --- Backend Communication ---
def get_history(data_id):
    try:
        response = requests.post(f"{BACKEND_URL}/history", json={"data_id": data_id})
        if response.status_code == 200:
            st.session_state.chat_history = response.json()
        else:
            st.error(f"Could not retrieve history: {response.text}")
    except Exception as e:
        st.error(f"Error getting history: {e}")

def process_query(query_text):
    payload = {"query": query_text, "data_id": st.session_state.data_id}
    try:
        response = requests.post(f"{BACKEND_URL}/process_query", json=payload)
        if response.status_code == 200:
            # After processing, just update the history, which will trigger a rerun
            get_history(st.session_state.data_id)
        else:
            st.error(f"Error from backend: {response.text}")
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the backend.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# --- UI Rendering ---

def render_chat():
    for event in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(event['query'])

        with st.chat_message("assistant"):
            try:
                response = event['response']
                if not isinstance(response, dict):
                    st.error("Invalid response from backend.")
                    continue

                response_type = response.get("classification") or response.get("type")

                if response_type == "code_generation" or response_type == "code":
                    st.info(response.get("explanation", ""))
                    
                    # Display charts in tabs
                    if response.get("charts"):
                        st.subheader("Charts")
                        chart_tabs = st.tabs([spec['type'].capitalize() for spec in response["charts"]])
                        for i, spec in enumerate(response["charts"]):
                            with chart_tabs[i]:
                                chart_df = pd.DataFrame(response['dataframe'], columns=response['columns'])
                                try:
                                    if spec['type'] == 'bar':
                                        fig = px.bar(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                                    elif spec['type'] == 'pie':
                                        fig = px.pie(chart_df, names=spec['names_column'], values=spec['values_column'], color_discrete_sequence=px.colors.sequential.RdBu)
                                    elif spec['type'] == 'line':
                                        fig = px.line(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                                    elif spec['type'] == 'scatter':
                                        fig = px.scatter(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                                    st.plotly_chart(fig, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Could not create {spec['type']} chart: {e}")
                        st.divider()

                    # Display dataframe
                    st.subheader("Data View")
                    display_df = pd.DataFrame(response['dataframe'], columns=response['columns'])
                    st.dataframe(display_df)

                    # Display insight
                    if response.get("insight"):
                        st.markdown("--- ")
                        insight = response["insight"]
                        st.info(f"💡 **Proactive Insight:** {insight['insight']}")
                        if st.button(insight['follow_up_query'], key=f"insight_{event['query']}"):
                            with st.spinner('Discovering more insights...'):
                                process_query(insight['follow_up_query'])
                            st.rerun()

                elif response_type == "suggestion" or response_type == "suggestions":
                    st.warning("💡 Your query is a bit vague. Please choose a more specific option below:")
                    for i, suggestion in enumerate(response['suggestions']):
                        if st.button(suggestion['query'], key=f"suggestion_{event['query']}_{i}"):
                            with st.spinner('Thinking...'):
                                process_query(suggestion['query'])
                            st.rerun()
                        st.markdown(f"> {suggestion['explanation']}")
                
                elif response_type == "error":
                    st.error(response.get("explanation", "An unknown error occurred."))
            except Exception as e:
                st.error(f"An error occurred while rendering the response: {e}")

st.title("🤖 Finkraft Data Explorer")
st.markdown("Upload your CSV and ask questions in plain English!")

# --- Server Control ---
def start_server(version):
    if st.session_state.server_process:
        st.session_state.server_process.kill()
    
    if version == "LLM Version":
        command = ["uvicorn", "backend.llm_version.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    else:
        command = ["uvicorn", "backend.LangGraph_version.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    
    st.session_state.server_process = subprocess.Popen(command)
    st.success(f"Started {version} server.")

def stop_server():
    if st.session_state.server_process:
        st.session_state.server_process.kill()
        st.session_state.server_process = None
        st.success("Server stopped.")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("Controls")

    # Version selection
    version = st.selectbox(
        "Choose the application version",
        ("LLM Version", "LangGraph Version")
    )

    if st.button("Start Server"):
        start_server(version)

    if st.button("Stop Server"):
        stop_server()

    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
    if uploaded_file is not None and st.session_state.data_id is None:
        with st.spinner('Uploading and processing file...'):
            files = {'file': (uploaded_file.name, uploaded_file, 'text/csv')}
            try:
                response = requests.post(f"{BACKEND_URL}/upload", files=files)
                if response.status_code == 200:
                    response_data = response.json()
                    st.session_state.data_id = response_data['data_id']
                    st.session_state.profile = response_data['profile']
                    st.session_state.chat_history = [] # Reset history on new upload
                    st.success('File Uploaded!')
                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    if st.session_state.data_id:
        st.header("Export")
        st.download_button(
            label="Export Chat as JSON",
            data=json.dumps(st.session_state.chat_history, indent=2),
            file_name="chat_history.json",
            mime="application/json",
        )
        st.markdown(f'<a href="{BACKEND_URL}/export/{st.session_state.data_id}/csv" download>Export Final Data as CSV</a>', unsafe_allow_html=True)
        
        if st.button("Preview Summary"):
            with st.spinner("Generating Summary..."):
                response = requests.get(f"{BACKEND_URL}/export/{st.session_state.data_id}/md")
                if response.status_code == 200:
                    st.session_state.markdown_preview = response.text
                else:
                    st.error("Could not generate summary.")

        st.markdown(f'<a href="{BACKEND_URL}/export/{st.session_state.data_id}/md" download>Export Summary as Markdown</a>', unsafe_allow_html=True)


# --- Main Chat Interface ---
if st.session_state.data_id is None:
    st.info("Please upload a CSV file to begin.")
else:
    # Display Data Profile
    if st.session_state.profile:
        with st.expander("📊 Data Profile & Quality Check"):
            st.subheader("Dataset Summary")
            summary = st.session_state.profile['dataset_summary']
            cols = st.columns(4)
            i = 0
            for key, value in summary.items():
                cols[i].metric(label=key, value=value)
                i += 1

            st.subheader("Column Details")
            column_details_df = pd.DataFrame(st.session_state.profile['column_details'])
            st.dataframe(column_details_df, use_container_width=True)

            st.subheader("Numeric Column Statistics")
            numeric_summary_dict = st.session_state.profile['numeric_summary']
            if numeric_summary_dict:
                numeric_summary_df = pd.DataFrame(numeric_summary_dict).reset_index()
                numeric_summary_df = numeric_summary_df.rename(columns={'index': 'Statistic'})
                st.dataframe(numeric_summary_df, use_container_width=True)
            else:
                st.write("No numeric columns found in the dataset.")

    # Render the chat history
    render_chat()

    # Chat input
    if prompt := st.chat_input("What would you like to ask?"):
        process_query(prompt)
        st.rerun()

    # Markdown Preview Modal
    if st.session_state.markdown_preview:
        with st.container():
            st.markdown("## Chat Summary Preview")
            st.markdown(st.session_state.markdown_preview, unsafe_allow_html=True)
            if st.button("Close Preview"):
                st.session_state.markdown_preview = None
                st.rerun()