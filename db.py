import sqlite3
import json
import os
from encryption import encrypt_bytes, decrypt_bytes, encrypt_str, decrypt_str

DB_FILE = "app_data.db"

def get_conn():
    first = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    if first:
        create_schema(conn)
    return conn

def create_schema(conn):
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        profile BLOB
    )""")
    cur.execute("""
    CREATE TABLE progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        data BLOB,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    cur.execute("""
    CREATE TABLE lessons_cache (
        id INTEGER PRIMARY KEY,
        data BLOB
    )""")
    conn.commit()

def save_user(username: str, password_hash: str, profile: dict):
    conn = get_conn()
    cur = conn.cursor()
    enc_profile = encrypt_bytes(json.dumps(profile).encode("utf-8"))
    try:
        cur.execute("INSERT INTO users (username, password, profile) VALUES (?, ?, ?)", (username, password_hash, enc_profile))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_user(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, profile FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        return None
    uid, uname, password, profile_blob = row
    profile = {}
    if profile_blob:
        try:
            profile = json.loads(decrypt_bytes(profile_blob).decode("utf-8"))
        except Exception:
            profile = {}
    return {"id": uid, "username": uname, "password": password, "profile": profile}

def update_profile(user_id: int, profile: dict):
    conn = get_conn()
    cur = conn.cursor()
    enc_profile = encrypt_bytes(json.dumps(profile).encode("utf-8"))
    cur.execute("UPDATE users SET profile=? WHERE id=?", (enc_profile, user_id))
    conn.commit()

def save_progress(user_id: int, progress: dict):
    conn = get_conn()
    cur = conn.cursor()
    enc = encrypt_bytes(json.dumps(progress).encode("utf-8"))
    
    cur.execute("SELECT id FROM progress WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE progress SET data=? WHERE user_id=?", (enc, user_id))
    else:
        cur.execute("INSERT INTO progress (user_id, data) VALUES (?, ?)", (user_id, enc))
    conn.commit()

def load_progress(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT data FROM progress WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        return {}
    try:
        return json.loads(decrypt_bytes(row[0]).decode("utf-8"))
    except Exception:
        return {}

def cache_lessons(lesson_id: int, lesson_obj: dict):
    conn = get_conn()
    cur = conn.cursor()
    enc = encrypt_bytes(json.dumps(lesson_obj).encode("utf-8"))
    cur.execute("REPLACE INTO lessons_cache (id, data) VALUES (?, ?)", (lesson_id, enc))
    conn.commit()

def load_cached_lesson(lesson_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT data FROM lessons_cache WHERE id=?", (lesson_id,))
    row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(decrypt_bytes(row[0]).decode("utf-8"))
    except Exception:
        return None
