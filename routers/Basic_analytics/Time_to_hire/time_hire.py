from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
from io import StringIO

router = APIRouter()

@router.get("/")
def home():
    return {"message": "Hiring Analytics API is running 🚀"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_csv(StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

    required_cols = {"name", "position", "application_date", "hire_date"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")

    # Parse dates safely
    for col in ["application_date", "hire_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=["application_date", "hire_date"])

    if df.empty:
        raise HTTPException(status_code=400, detail="No valid rows found in dataset")

    # Calculate hiring time
    df["hiring_time"] = (df["hire_date"] - df["application_date"]).dt.days

    # Stats
    avg_time = round(df["hiring_time"].mean(), 2)
    fastest = int(df["hiring_time"].min())
    longest = int(df["hiring_time"].max())

    # Charts
    bar_data = {
        "labels": df["name"].tolist(),
        "values": df["hiring_time"].tolist()
    }

    pie_data = {
        "labels": df["position"].value_counts().index.tolist(),
        "values": df["position"].value_counts().tolist()
    }

    donut_data = {
        "labels": ["Fastest Hire", "Average Hire", "Longest Hire"],
        "values": [fastest, avg_time, longest]
    }

    # Line chart: hires per month
    df["hire_month"] = df["hire_date"].dt.to_period("M").astype(str)
    line_group = df.groupby("hire_month").size()
    line_data = {
        "labels": line_group.index.tolist(),
        "values": line_group.values.tolist()
    }

    return {
        "stats": {
            "average_time": avg_time,
            "fastest_hire": fastest,
            "longest_hire": longest
        },
        "charts": {
            "bar": bar_data, 
            "pie": pie_data,
            "donut": donut_data,
            "line": line_data
        }
    }
