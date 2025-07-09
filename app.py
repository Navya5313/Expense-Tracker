import streamlit as st
import pandas as pd
from db import (
    add_record, get_records, set_goal, get_goal, log_goal_history, get_goal_history,
    get_total_income, get_total_expenses,
    get_streak, get_best_streak, get_streak_growth,
    add_recurring_transaction, get_recurring_transactions, process_due_recurring_transactions,
    get_base_currency, set_base_currency,
    unlock_achievement, get_achievements,
    get_monthly_spending_by_category
)
from Auth import login_section
from datetime import date

# -------------- Logout --------------
def logout():
    st.session_state.clear()
    st.success("You have been logged out.")
    st.rerun()

# -------------- Dashboard --------------
def dashboard(username):
    st.subheader("📊 Dashboard")
    process_due_recurring_transactions(username)

    income = get_total_income(username)
    expenses = get_total_expenses(username)
    savings = income - expenses
    base = get_base_currency(username)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"{base} {income}")
    col2.metric("Total Expenses", f"{base} {expenses}")
    col3.metric("Current Savings", f"{base} {savings}")

# -------------- Records Section --------------
def record_section(username):
    st.subheader("➕ Add Record")

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Other"])
        amount = st.number_input("Amount", min_value=0.0)
        currency = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"])
    with col2:
        rtype = st.radio("Type", ["Income", "Expense"])
        desc = st.text_input("Description")

    if st.button("Add Record"):
        add_record(username, category, amount, rtype, desc, currency)
        st.success("Record added!")

    st.subheader("📋 Your Records")
    df = get_records(username)
    if not df.empty:
        st.dataframe(df)

# -------------- Goals and Streaks --------------
def goal_section(username):
    st.subheader("🎯 Monthly Goal")

    current = get_goal(username)
    new_goal = st.number_input("Set Monthly Goal", value=float(current), min_value=0.0)

    if st.button("Update Goal"):
        set_goal(username, new_goal)
        log_goal_history(username, new_goal)
        unlock_achievement(username, "First Goal Set")
        st.success("Goal updated!")

    st.subheader("📈 Goal History")
    history = get_goal_history(username)
    if not history.empty:
        st.line_chart(history.set_index("date")["goal"])

    # Streak Tracking
    st.subheader("🔥 Streak Tracker")
    streak = get_streak(username)
    best = get_best_streak(username)

    if streak >= 7:
        unlock_achievement(username, "7-Day Streak")

    col1, col2 = st.columns(2)
    col1.metric("Current Streak", f"{streak} days")
    col2.metric("Best Streak", f"{best} days")

    growth = get_streak_growth(username)
    if not growth.empty:
        st.line_chart(growth.set_index("Date")["Streak"])

# -------------- Budget Prediction --------------
def budget_prediction(username):
    st.subheader("📊 Budget Prediction")

    data = get_monthly_spending_by_category(username)
    if not data.empty:
        st.bar_chart(data)
    else:
        st.info("Not enough data for prediction yet.")

# -------------- Recurring Transactions --------------
def recurring_section(username):
    st.subheader("🔁 Recurring Transactions")

    with st.expander("➕ Add Recurring"):
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", ["Rent", "Bills", "Subscription", "Salary", "Other"])
            amount = st.number_input("Amount", min_value=0.0)
            freq = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
        with col2:
            rtype = st.radio("Type", ["Income", "Expense"], key="rec_type")
            desc = st.text_input("Description", key="rec_desc")
            start_date = st.date_input("Start Date", value=date.today())
            currency = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"], key="rec_currency")

        if st.button("Add Recurring"):
            add_recurring_transaction(username, category, amount, rtype, desc, freq, start_date.isoformat(), currency)
            st.success("Recurring transaction added!")

    st.subheader("📅 Upcoming Recurring Entries")
    rec = get_recurring_transactions(username)
    if not rec.empty:
        st.dataframe(rec)
    else:
        st.info("No recurring transactions yet.")

# -------------- Achievements Section --------------
def achievements_section(username):
    st.subheader("🏅 Achievements")

    income = get_total_income(username)
    if income >= 10000:
        unlock_achievement(username, "Saved ₹10,000")

    badges = get_achievements(username)
    if badges.empty:
        st.info("No achievements unlocked yet.")
    else:
        for _, row in badges.iterrows():
            st.success(f"🏆 {row['name']} — unlocked on {row['date']}")

# -------------- Sidebar with Currency Selector --------------
def sidebar(username):
    st.sidebar.markdown(f"**User:** `{username}`")
    base = get_base_currency(username)
    new_currency = st.sidebar.selectbox("💱 Base Currency", ["INR", "USD", "EUR", "GBP"], index=["INR", "USD", "EUR", "GBP"].index(base))
    if new_currency != base:
        set_base_currency(username, new_currency)
        st.experimental_rerun()

    return st.sidebar.radio("📂 Navigation", ["Dashboard", "Add Record", "Goals", "Recurring", "Prediction", "Achievements"])

# -------------- Profile Summary --------------
def profile_section(username):
    st.subheader("👤 Profile")

    income = get_total_income(username)
    expenses = get_total_expenses(username)
    savings = income - expenses
    base = get_base_currency(username)

    st.write(f"**Username:** `{username}`")
    st.write(f"**Base Currency:** {base}")
    st.write(f"**Total Income:** {base} {income}")
    st.write(f"**Total Expenses:** {base} {expenses}")
    st.write(f"**Total Savings:** {base} {savings}")

# -------------- Main --------------
def main():
    st.set_page_config(page_title="Expense Tracker", layout="wide")

    if "username" not in st.session_state:
        login_section()
    else:
        username = st.session_state.username

        col1, col2 = st.columns([6, 1])
        with col1:
            st.title("💼 Expense Tracker")
        with col2:
            if st.button("🔓", help="Logout"):
                logout()

        page = sidebar(username)

        if page == "Dashboard":
            dashboard(username)
        elif page == "Add Record":
            record_section(username)
        elif page == "Goals":
            goal_section(username)
        elif page == "Recurring":
            recurring_section(username)
        elif page == "Prediction":
            budget_prediction(username)
        elif page == "Achievements":
            achievements_section(username)

# -------------- Run --------------
if __name__ == "__main__":
    main()
