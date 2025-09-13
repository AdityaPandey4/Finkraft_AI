import streamlit as st
import pandas as pd
import requests
import plotly.express as px

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
    if 'full_df' not in st.session_state:
        st.session_state.full_df = None
    if 'display_df' not in st.session_state:
        st.session_state.display_df = None
    if 'explanation' not in st.session_state:
        st.session_state.explanation = ""
    if 'suggestions' not in st.session_state:
        st.session_state.suggestions = []
    if 'chart_spec' not in st.session_state:
        st.session_state.chart_spec = None

init_session_state()

# --- Backend Communication ---
def process_query(query_text):
    payload = {"query": query_text, "data_id": st.session_state.data_id}
    try:
        response = requests.post(f"{BACKEND_URL}/process_query", json=payload)
        if response.status_code == 200:
            data = response.json()
            response_type = data.get("type")

            st.session_state.chart_spec = None # Reset chart on new query

            if response_type == "code":
                st.session_state.display_df = pd.DataFrame(data['dataframe'], columns=data['columns'])
                st.session_state.explanation = data['explanation']
                st.session_state.suggestions = []
                if data.get("chart"):
                    st.session_state.chart_spec = data["chart"]
            elif response_type == "suggestions":
                st.session_state.suggestions = data['suggestions']
                st.session_state.explanation = ""
            elif response_type == "error":
                st.error(data.get("explanation", "An unknown error occurred."))
                st.session_state.suggestions = []
        else:
            st.error(f"Error from backend: {response.text}")
            st.session_state.suggestions = []

    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the backend.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# --- UI Rendering ---

st.title("🤖 Finkraft Data Explorer")
st.markdown("Upload your CSV and ask questions in plain English!")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
    if uploaded_file is not None and st.session_state.data_id is None:
        with st.spinner('Uploading and processing file...'):
            files = {'file': (uploaded_file.name, uploaded_file, 'text/csv')}
            try:
                response = requests.post(f"{BACKEND_URL}/upload", files=files)
                if response.status_code == 200:
                    uploaded_file.seek(0)
                    st.session_state.full_df = pd.read_csv(uploaded_file)
                    st.session_state.display_df = st.session_state.full_df
                    st.session_state.data_id = response.json()['data_id']
                    st.session_state.explanation = "File uploaded successfully! The full dataset is shown below."
                    st.success('File Uploaded!')
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- Main Area for Data and Charts ---
if st.session_state.data_id is None:
    st.info("Please upload a CSV file to begin.")
else:
    query = st.text_input("Enter your query:", placeholder="e.g., 'What are the total sales per region?'")

    if st.button("Ask", type="primary") and query:
        with st.spinner('Thinking...'):
            process_query(query)

    # Display explanation in main area
    if st.session_state.explanation:
        st.info(st.session_state.explanation)

    # Display suggestions with context
    if st.session_state.suggestions:
        st.warning("💡 Your query is a bit vague. Please choose a more specific option below:")
        for i, suggestion in enumerate(st.session_state.suggestions):
            with st.container():
                if st.button(suggestion['query'], key=f"suggestion_{i}"):
                    with st.spinner('Thinking...'):
                        process_query(suggestion['query'])
                    st.rerun()
                st.markdown(f"> {suggestion['explanation']}")
        st.divider()

    # Display chart if spec exists
    if st.session_state.chart_spec:
        st.subheader("Chart")
        spec = st.session_state.chart_spec
        chart_df = st.session_state.display_df
        
        try:
            if spec['type'] == 'bar':
                fig = px.bar(chart_df, x=spec['x_column'], y=spec['y_column'], color=spec.get('color_column'))
                st.plotly_chart(fig, use_container_width=True)
            elif spec['type'] == 'pie':
                fig = px.pie(chart_df, names=spec['names_column'], values=spec['values_column'], color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Could not create chart: {e}")
        st.divider()

    st.subheader("Data View")
    st.dataframe(st.session_state.display_df)

    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df_to_csv(st.session_state.display_df)
    st.download_button(
        label="Download Current View as CSV",
        data=csv,
        file_name='current_view.csv',
        mime='text/csv',
    )