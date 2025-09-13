import pandas as pd
import numpy as np

def get_profile(df: pd.DataFrame) -> dict:
    """
    Generates a comprehensive profile of a pandas DataFrame.
    """
    
    # Basic info
    num_rows, num_cols = df.shape
    total_missing = int(df.isnull().sum().sum())
    
    # Column Details
    column_details = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing_count = int(df[col].isnull().sum())
        missing_percentage = round((missing_count / num_rows) * 100, 2) if num_rows > 0 else 0
        unique_count = df[col].nunique()
        
        col_info = {
            "Column": col,
            "Non-Null Count": num_rows - missing_count,
            "Null Count": missing_count,
            "Data Type": dtype,
        }
        column_details.append(col_info)

    # Numeric columns summary
    numeric_df = df.select_dtypes(include=np.number)
    numeric_summary = {}
    if not numeric_df.empty:
        numeric_summary = numeric_df.describe().round(2).to_dict()

    profile = {
        "dataset_summary": {
            "Number of Rows": num_rows,
            "Number of Columns": num_cols,
            "Duplicate Rows": int(df.duplicated().sum()),
            "Memory Usage": f"{df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
        },
        "column_details": column_details,
        "numeric_summary": numeric_summary,
    }
    
    return profile

def get_profile_as_dict(df: pd.DataFrame) -> dict:
    """
    Generates a comprehensive profile of a pandas DataFrame and returns it as a dictionary.
    """
    return get_profile(df)