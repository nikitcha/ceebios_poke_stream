import pandas as pd
import sqlite3
from sqlite3 import Connection
import streamlit as st

URI_SQLITE_DB = 'data.db'
@st.cache(hash_funcs={Connection: id})
def get_connection():
    return sqlite3.connect(URI_SQLITE_DB, check_same_thread=False)


def init_db(conn: Connection):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS userdata
            (
                username TEXT,
                search TEXT,
                UNIQUE(username, search)
            );"""
    )
    conn.commit()

def init_session(conn: Connection, session_id:str):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS searchdata
            (
                id TEXT,
                search TEXT,
                level TEXT,
                name TEXT,
                UNIQUE(id)
            );"""

    )
    conn.execute(f"INSERT INTO searchdata (id, search, level, name) VALUES ('{session_id}', '', '', '')")
    conn.commit()


def update_search_data(conn, uid, dic):
    for key,val in dic.items():
        conn.execute(f"update searchdata set {key}='{val}' where id='{uid}'")
    conn.commit()    

def get_searchdata(conn: Connection, uid:str):
    df = pd.read_sql(f"SELECT * FROM searchdata where id='{uid}'", con=conn)
    return df.iloc[0]


def get_alldata(conn: Connection):
    df = pd.read_sql("SELECT * FROM userdata", con=conn)
    return df

def add_userdata(conn: Connection, username:str, search:str):
    try:
        conn.execute(f"INSERT INTO userdata (username, search) VALUES ('{username}', '{search}')")
        conn.commit()
    except:
        print('Entry present')

def get_userdata(conn: Connection, username:str):
    df = pd.read_sql(f"SELECT DISTINCT search FROM userdata where username='{username}'", con=conn)
    return df
