import sqlite3
import hashlib
import random
import string
import os

# -------------- Init Auth DB --------------
def initialize_auth_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/auth.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# -------------- Password Hashing --------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------- Register User --------------
def add_user(username, password):
    conn = sqlite3.connect("data/auth.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
    conn.commit()
    conn.close()

# -------------- Verify Login --------------
def verify_user(username, password):
    conn = sqlite3.connect("data/auth.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == hash_password(password)

# -------------- Forgot Password - Reset with Temp --------------
def reset_password(username):
    conn = sqlite3.connect("data/auth.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(temp_password), username))
        conn.commit()
        conn.close()
        return temp_password
    conn.close()
    return None

# -------------- Change Password --------------
def update_password(username, new_password):
    conn = sqlite3.connect("data/auth.db")
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()

# -------------- Streamlit Login Section --------------
import streamlit as st
from db import create_user_db

def login_section():
    initialize_auth_db()

    st.title("🔐 Login")

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if verify_user(username, password):
                st.session_state.username = username
                st.success("Login successful!")
                create_user_db(username)
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username", key="register_user")
        new_pass = st.text_input("New Password", type="password", key="register_pass")
        if st.button("Register"):
            try:
                add_user(new_user, new_pass)
                create_user_db(new_user)
                st.success("Registration successful! Please login.")
            except sqlite3.IntegrityError:
                st.error("Username already exists.")

    with tab3:
        forgot_user = st.text_input("Username", key="forgot_user")
        if st.button("Reset Password"):
            temp = reset_password(forgot_user)
            if temp:
                st.warning(f"Temporary password: `{temp}`")
            else:
                st.error("Username not found.")
