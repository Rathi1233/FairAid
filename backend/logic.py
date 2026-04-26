import pandas as pd
from sklearn.linear_model import LogisticRegression

def analyze_data(df, threshold=8.0):
    # Mapping
    income_map = {"Low": 10, "Medium": 5, "High": 1}
    health_map = {"Critical": 10, "Moderate": 5, "Healthy": 1}
    food_map = {"Low": 10, "Medium": 5, "High": 1}
    employment_map = {"Unemployed": 10, "DailyWage": 5, "Stable": 1}

    df["IncomeScore"] = df["IncomeLevel"].map(income_map)
    df["HealthScore"] = df["HealthCondition"].map(health_map)
    df["FoodScore"] = df["FoodAvailability"].map(food_map)
    df["EmploymentScore"] = df["EmploymentStatus"].map(employment_map)

    df["FamilyScore"] = df["FamilySize"].clip(upper=8)

    # Need Score
    df["NeedScore"] = (
        0.3 * df["IncomeScore"] +
        0.2 * df["FamilyScore"] +
        0.2 * df["HealthScore"] +
        0.2 * df["FoodScore"] +
        0.1 * df["EmploymentScore"]
    )

    df_sorted = df.sort_values(by="NeedScore", ascending=False).reset_index(drop=True)

    # Convert Help
    df["HelpNumeric"] = df["ReceivedHelp"].replace({"Yes": 1, "No": 0, "yes": 1, "no": 0})
    df["HelpNumeric"] = pd.to_numeric(df["HelpNumeric"], errors='coerce').fillna(0)

    top_needy = df[df["NeedScore"] >= threshold].copy()
    if not top_needy.empty:
        need_satisfaction = top_needy["HelpNumeric"].mean()
    else:
        need_satisfaction = 0

    # ML MODEL
    X = df[[
        "IncomeScore",
        "FamilyScore",
        "HealthScore",
        "FoodScore",
        "EmploymentScore"
    ]]
    y = df["HelpNumeric"]

    # Handle NaNs that might have been introduced
    df.fillna(0, inplace=True)
    X.fillna(0, inplace=True)
    y.fillna(0, inplace=True)

    try:
        model = LogisticRegression(class_weight='balanced')
        model.fit(X, y)
        df["PredictedHelp"] = model.predict(X)
    except Exception as e:
        df["PredictedHelp"] = 0

    # Unfair Cases
    unfair_cases = df[(df["NeedScore"] >= threshold) & (df["HelpNumeric"] == 0)]
    
    # Recommendations
    recommendations = []
    if len(unfair_cases) > 0:
        recommendations = [
            "Prioritize individuals with high NeedScore",
            "Reallocate resources to underserved people",
            "Review allocation strategy for fairness"
        ]
    else:
        recommendations = [
            "Current allocation appears fair and efficient"
        ]

    # Status Message
    status_msg = ""
    status_type = ""
    if need_satisfaction == 1.0:
        status_msg = "Perfect Distribution"
        status_type = "success"
    elif need_satisfaction >= 0.7:
        status_msg = "Good Distribution"
        status_type = "info"
    elif need_satisfaction >= 0.5:
        status_msg = "Moderate Issues Detected"
        status_type = "warning"
    else:
        status_msg = "Serious Unfair Distribution"
        status_type = "error"

    return {
        "total_people": len(df),
        "high_need_count": len(top_needy),
        "satisfaction_rate": float(need_satisfaction),
        "status_msg": status_msg,
        "status_type": status_type,
        "top_people": df_sorted[["ID", "NeedScore", "ReceivedHelp"]].head(20).to_dict(orient="records"),
        "high_need_group": top_needy[["ID", "NeedScore", "ReceivedHelp"]].to_dict(orient="records"),
        "unfair_cases": unfair_cases[["ID", "NeedScore"]].to_dict(orient="records"),
        "predictions": df[["ID", "NeedScore", "HelpNumeric", "PredictedHelp"]].head(20).to_dict(orient="records"),
        "recommendations": recommendations
    }
