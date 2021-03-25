import pandas as pd
import sqlite3
from sqlite3 import Connection
import streamlit as st

URI_SQLITE_DB = "data.db"

@st.cache(hash_funcs={Connection: id})
def get_connection():
    """Put the connection in cache to reuse if path does not change between Streamlit reruns.
    NB : https://stackoverflow.com/questions/48218065/programmingerror-sqlite-objects-created-in-a-thread-can-only-be-used-in-that-sa
    """
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
