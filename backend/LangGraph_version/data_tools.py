import pandas as pd
from typing import Dict, List, Any
import uuid

# In-memory caches
data_cache: Dict[str, pd.DataFrame] = {}
history_cache: Dict[str, List[Dict[str, Any]]] = {}

def load_csv_from_upload(file) -> str:
    """
    Loads a CSV file into a pandas DataFrame and stores it in the cache.
    Initializes an empty history for the session.
    """
    df = pd.read_csv(file)
    data_id = str(uuid.uuid4())
    data_cache[data_id] = df
    history_cache[data_id] = []  # Initialize history
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

def add_to_history(data_id: str, event: Dict[str, Any]):
    """
    Adds a new event to the session's history.
    """
    if data_id not in history_cache:
        history_cache[data_id] = []
    history_cache[data_id].append(event)

def get_history(data_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves the history for a given session.
    """
    return history_cache.get(data_id, [])
