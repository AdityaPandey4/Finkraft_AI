import pandas as pd
from typing import Dict
import uuid

# In-memory cache for storing dataframes
data_cache: Dict[str, pd.DataFrame] = {}

def load_csv_from_upload(file) -> str:
    """
    Loads a CSV file into a pandas DataFrame and stores it in the cache.
    """
    df = pd.read_csv(file)
    data_id = str(uuid.uuid4())
    data_cache[data_id] = df
    return data_id

def get_dataframe(data_id: str) -> pd.DataFrame:
    """
    Retrieves a DataFrame from the cache.
    """
    if data_id not in data_cache:
        raise ValueError("Invalid data_id")
    return data_cache[data_id]

def update_dataframe(data_id: str, df: pd.DataFrame):
    """
    Updates a DataFrame in the cache.
    """
    if data_id not in data_cache:
        raise ValueError("Invalid data_id")
    data_cache[data_id] = df