from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .data_tools import (
    load_csv_from_upload, 
    get_dataframe, 
    update_dataframe,
    add_to_history,
    get_history
)
from .graph import app as graph_app, AgentState
from .profiler import get_profile, get_profile_as_dict
from .markdown_generator import create_chat_summary_markdown
from .nodes import generate_chat_summary
import logging
import pandas as pd
import numpy as np
import io
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class QueryRequest(BaseModel):
    query: str
    data_id: str

class HistoryRequest(BaseModel):
    data_id: str

@app.get("/")
def read_root():
    return {"message": "Finkraft Data Explorer Backend is running."}

@app.post("/upload")
def upload_csv(file: UploadFile = File(...)):
    logger.info("Upload endpoint called.")
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    try:
        data_id = load_csv_from_upload(file.file)
        df = get_dataframe(data_id)
        profile = get_profile(df)
        logger.info(f"File uploaded and profiled successfully. Data ID: {data_id}")
        return {
            "data_id": data_id, 
            "columns": df.columns.tolist(), 
            "rows": df.head().to_dict(orient='records'),
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.post("/process_query")
def process_query(request: QueryRequest):
    logger.info(f"Query endpoint called with data_id: {request.data_id} and query: '{request.query}'")
    try:
        df = get_dataframe(request.data_id)
        history = get_history(request.data_id)
        
        initial_state = AgentState(
            data_id=request.data_id,
            dataframe=df,
            query=request.query,
            chat_history=history,
            explanation=None,
            charts=None,
            suggestions=None,
            error=None,
            insight=None,
            classification=None
        )

        response = graph_app.invoke(initial_state)
        logger.info(f"Response from graph: {response}")

        response_type = response.get("classification")
        
        # Always handle dataframe if present
        if "dataframe" in response and isinstance(response["dataframe"], pd.DataFrame):
            new_df = response["dataframe"]
            if response_type == "code_generation":
                logger.info("Updating dataframe in cache.")
                update_dataframe(request.data_id, new_df)
            
            response["dataframe"] = new_df.to_dict(orient='records')
            response["columns"] = new_df.columns.tolist()

        # Log the event to history
        history_event = {"query": request.query, "response": {
            "classification": response.get("classification"),
            "explanation": response.get("explanation"),
            "charts": response.get("charts"),
            "suggestions": response.get("suggestions"),
            "error": response.get("error"),
            "insight": response.get("insight"),
        }}
        
        # Add dataframe and columns to history if they exist in the final response
        if "dataframe" in response:
            history_event["response"]["dataframe"] = response["dataframe"]
        if "columns" in response:
            history_event["response"]["columns"] = response["columns"]
            
        add_to_history(request.data_id, history_event)

        return JSONResponse(content=response)

    except ValueError as e:
        logger.error(f"ValueError in process_query: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Exception in process_query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")

@app.post("/history")
def get_chat_history(request: HistoryRequest):
    logger.info(f"History endpoint called for data_id: {request.data_id}")
    try:
        history = get_history(request.data_id)
        return JSONResponse(content=history)
    except Exception as e:
        logger.error(f"Exception in get_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {e}")

@app.get("/export/{data_id}/{format}")
def export_data(data_id: str, format: str):
    logger.info(f"Export endpoint called for data_id: {data_id} with format: {format}")
    if format == "md":
        history = get_history(data_id)
        df = get_dataframe(data_id)
        profile = get_profile_as_dict(df)
        summary = generate_chat_summary(history)
        md_content = create_chat_summary_markdown(profile, summary, history, data_id)
        return StreamingResponse(io.StringIO(md_content), media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=chat_summary.md"})
    
    elif format == "csv":
        df = get_dataframe(data_id)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return StreamingResponse(csv_buffer, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=final_data.csv"})

    else:
        raise HTTPException(status_code=400, detail="Invalid export format specified.")
