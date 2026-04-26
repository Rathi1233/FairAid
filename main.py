import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# -------------------------------
# STEP 1: Load Dataset
# -------------------------------
df = pd.read_csv("data.csv")

# -------------------------------
# STEP 2: Mapping (Convert to numbers)
# -------------------------------
income_map = {"Low": 10, "Medium": 5, "High": 1}
health_map = {"Critical": 10, "Moderate": 5, "Healthy": 1}
food_map = {"Low": 10, "Medium": 5, "High": 1}
employment_map = {"Unemployed": 10, "DailyWage": 5, "Stable": 1}

df["IncomeScore"] = df["IncomeLevel"].map(income_map)
df["HealthScore"] = df["HealthCondition"].map(health_map)
df["FoodScore"] = df["FoodAvailability"].map(food_map)
df["EmploymentScore"] = df["EmploymentStatus"].map(employment_map)

# Family & Dependents
df["FamilyScore"] = df["FamilySize"].clip(upper=8)
df["DependentScore"] = df["Dependents"].clip(upper=5)

# -------------------------------
# STEP 3: Need Score Calculation
# -------------------------------
df["NeedScore"] = (
    0.3 * df["IncomeScore"] +
    0.2 * df["FamilyScore"] +
    0.2 * df["HealthScore"] +
    0.2 * df["FoodScore"] +
    0.1 * df["EmploymentScore"]
)

# -------------------------------
# STEP 4: Ranking
# -------------------------------
df_sorted = df.sort_values(by="NeedScore", ascending=False).reset_index(drop=True)

print("\n=== Top People by Need ===")
print(df_sorted[["ID", "NeedScore", "ReceivedHelp"]])

# -------------------------------
# STEP 5: Top 30% Needy
# -------------------------------
top_n = int(0.3 * len(df_sorted))
top_needy = df_sorted.head(top_n).copy()

print("\n=== Top Needy Group ===")
print(top_needy[["ID", "NeedScore", "ReceivedHelp"]])

# -------------------------------
# STEP 6: Convert Yes/No → 1/0
# -------------------------------
df["HelpNumeric"] = df["ReceivedHelp"].map({"Yes": 1, "No": 0})
top_needy["HelpNumeric"] = top_needy["ReceivedHelp"].map({"Yes": 1, "No": 0})

# -------------------------------
# STEP 7: Need Satisfaction Rate
# -------------------------------
need_satisfaction = top_needy["HelpNumeric"].mean()

print("\nNeed Satisfaction Rate:", round(need_satisfaction, 2))

# -------------------------------
# STEP 8: Interpretation
# -------------------------------
if need_satisfaction == 1.0:
    print("✅ Perfect: All high-need individuals are served.")
elif need_satisfaction >= 0.7:
    print("👍 Good: Most high-need individuals are served.")
elif need_satisfaction >= 0.5:
    print("⚠️ Moderate: Some high-need individuals are under-served.")
else:
    print("🚨 Poor: Many high-need individuals are not getting help.")

# -------------------------------
# STEP 9: ML MODEL
# -------------------------------
X = df[[
    "IncomeScore",
    "FamilyScore",
    "HealthScore",
    "FoodScore",
    "EmploymentScore"
]]

y = df["HelpNumeric"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Balanced model (fix bias)
model = LogisticRegression(class_weight='balanced')
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print("\nModel Accuracy:", round(accuracy, 2))

# Predict for all
df["PredictedHelp"] = model.predict(X)

print("\n=== Final Comparison ===")
print(df[["ID", "NeedScore", "HelpNumeric", "PredictedHelp"]])

# -------------------------------
# STEP 10: Detect REAL unfair cases
# -------------------------------
# High need but NOT helped (actual data)
unfair_cases = df[(df["NeedScore"] > 8) & (df["HelpNumeric"] == 0)]

print("\n=== High-Need but Not Served (Unfair Cases) ===")
print(unfair_cases[["ID", "NeedScore"]])