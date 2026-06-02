import pandas as pd

def generate_analytics(df: pd.DataFrame):
    analytics = {}

    # Total applications
    analytics["total_applications"] = len(df)

    # Call Screening
    analytics["call_screening_cleared"] = len(df[df["Call_Screening"] == "Yes"])
    analytics["call_screening_failed"] = len(df[df["Call_Screening"] == "No"])

    # AI Interview
    analytics["ai_cleared"] = len(df[df["AI_Interview"] == "Yes"])
    analytics["ai_failed"] = len(df[df["AI_Interview"] == "No"])

    # Assessment
    analytics["assessment_passed"] = len(df[df["Assessment_Result"] == "Pass"])
    analytics["assessment_failed"] = len(df[df["Assessment_Result"] == "Fail"])

    # Final Hires
    analytics["hired"] = len(df[df["Hired"] == "Yes"])
    analytics["not_hired"] = len(df[df["Hired"] == "No"])

    return analytics
