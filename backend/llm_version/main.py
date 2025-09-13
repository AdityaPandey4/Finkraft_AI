from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .data_tools import load_csv_from_upload, get_dataframe, update_dataframe
from . import llm_handler
import logging

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
        logger.info(f"File uploaded successfully. Data ID: {data_id}")
        return {"data_id": data_id, "columns": df.columns.tolist(), "rows": df.head().to_dict(orient='records')}
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.post("/process_query")
def process_query(request: QueryRequest):
    logger.info(f"Query endpoint called with data_id: {request.data_id} and query: '{request.query}'")
    try:
        df = get_dataframe(request.data_id)
        response = llm_handler.process_query_with_llm(request.query, df)
        logger.info(f"Response from LLM handler: {response}")

        response_type = response.get("type")

        if response_type == "code":
            new_df = response["dataframe"]
            explanation = response["explanation"]
            chart_spec = response.get("chart")
            logger.info("Updating dataframe in cache.")
            update_dataframe(request.data_id, new_df)
            logger.info("Returning new dataframe to frontend.")
            
            # Convert dataframe to list of records for JSON serialization
            records = new_df.to_dict(orient='records')
            
            return_payload = {
                "type": "code",
                "dataframe": records, # Send as records
                "columns": new_df.columns.tolist(), # Send columns separately
                "explanation": explanation,
                "chart": chart_spec
            }
            logger.info(f"Returning payload: {return_payload}")
            return return_payload
            
        elif response_type == "suggestions":
            logger.info("Returning suggestions to frontend.")
            return {
                "type": "suggestions",
                "suggestions": response["suggestions"]
            }
        else: # Handle error case
            logger.warning(f"LLM handler returned an error or unknown type: {response.get('explanation')}")
            return {
                "type": "error",
                "explanation": response.get("explanation", "An unknown error occurred.")
            }

    except ValueError as e:
        logger.error(f"ValueError in process_query: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Exception in process_query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")