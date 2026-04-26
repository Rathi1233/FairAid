import streamlit as st
import pandas as pd
from sklearn.linear_model import LogisticRegression

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(page_title="FairAid", layout="wide")

st.title("🍲 FairAid - Fair Food Distribution System")
st.markdown("Ensure **aid reaches the people who need it most** using data-driven insights.")

# -------------------------------
# File Upload
# -------------------------------
uploaded_file = st.file_uploader("📂 Upload NGO Data (CSV)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("📊 Raw Data")
    st.dataframe(df)

    # -------------------------------
    # Mapping
    # -------------------------------
    income_map = {"Low": 10, "Medium": 5, "High": 1}
    health_map = {"Critical": 10, "Moderate": 5, "Healthy": 1}
    food_map = {"Low": 10, "Medium": 5, "High": 1}
    employment_map = {"Unemployed": 10, "DailyWage": 5, "Stable": 1}

    df["IncomeScore"] = df["IncomeLevel"].map(income_map)
    df["HealthScore"] = df["HealthCondition"].map(health_map)
    df["FoodScore"] = df["FoodAvailability"].map(food_map)
    df["EmploymentScore"] = df["EmploymentStatus"].map(employment_map)

    df["FamilyScore"] = df["FamilySize"].clip(upper=8)

    # -------------------------------
    # Need Score
    # -------------------------------
    df["NeedScore"] = (
        0.3 * df["IncomeScore"] +
        0.2 * df["FamilyScore"] +
        0.2 * df["HealthScore"] +
        0.2 * df["FoodScore"] +
        0.1 * df["EmploymentScore"]
    )

    df_sorted = df.sort_values(by="NeedScore", ascending=False).reset_index(drop=True)

    # -------------------------------
    # Convert Help
    # -------------------------------
    df["HelpNumeric"] = df["ReceivedHelp"].map({"Yes": 1, "No": 0})

    # ===============================
    # 🎚️ Dynamic Threshold
    # ===============================
    st.subheader("🎚️ Set Need Threshold")

    threshold = st.slider(
        "Select minimum Need Score to classify as HIGH NEED",
        min_value=0.0,
        max_value=10.0,
        value=8.0,
        step=0.1
    )

    top_needy = df[df["NeedScore"] >= threshold].copy()
    top_needy["HelpNumeric"] = top_needy["ReceivedHelp"].map({"Yes": 1, "No": 0})

    # -------------------------------
    # Need Satisfaction
    # -------------------------------
    if len(top_needy) > 0:
        need_satisfaction = top_needy["HelpNumeric"].mean()
    else:
        need_satisfaction = 0

    # -------------------------------
    # ML MODEL
    # -------------------------------
    X = df[[
        "IncomeScore",
        "FamilyScore",
        "HealthScore",
        "FoodScore",
        "EmploymentScore"
    ]]
    y = df["HelpNumeric"]

    model = LogisticRegression(class_weight='balanced')
    model.fit(X, y)

    df["PredictedHelp"] = model.predict(X)

    # -------------------------------
    # Unfair Cases
    # -------------------------------
    unfair_cases = df[(df["NeedScore"] >= threshold) & (df["HelpNumeric"] == 0)]

    # ===============================
    # UI DISPLAY
    # ===============================

    st.divider()

    # 📊 Metrics
    col1, col2, col3 = st.columns(3)

    col1.metric("👥 Total People", len(df))
    col2.metric("🔥 High Need Count", len(top_needy))
    col3.metric("📊 Satisfaction Rate", round(need_satisfaction, 2))

    # 🚨 Status
    if need_satisfaction == 1.0:
        st.success("✅ Perfect Distribution")
    elif need_satisfaction >= 0.7:
        st.info("👍 Good Distribution")
    elif need_satisfaction >= 0.5:
        st.warning("⚠️ Moderate Issues Detected")
    else:
        st.error("🚨 Serious Unfair Distribution")

    st.divider()

    # 📊 Top People
    st.subheader("🔥 Top People by Need")
    st.dataframe(df_sorted[["ID", "NeedScore", "ReceivedHelp"]])

    # 🎯 High Need Group
    st.subheader(f"🎯 High Need Individuals (NeedScore ≥ {threshold})")
    st.dataframe(top_needy[["ID", "NeedScore", "ReceivedHelp"]])

    # 🚨 Unfair Cases
    st.subheader("🚨 High-Need but Not Served")
    st.dataframe(unfair_cases[["ID", "NeedScore"]])

    # 🤖 Predictions
    st.subheader("🤖 Model Predictions")
    st.dataframe(df[["ID", "NeedScore", "HelpNumeric", "PredictedHelp"]])

    # 💡 Recommendations
    st.subheader("💡 Recommendations")

    if len(unfair_cases) > 0:
        st.write("• Prioritize individuals with high NeedScore")
        st.write("• Reallocate resources to underserved people")
        st.write("• Review allocation strategy for fairness")
    else:
        st.write("• Current allocation appears fair and efficient")

    st.success("Analysis Complete ✅")