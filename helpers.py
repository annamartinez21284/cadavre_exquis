from flask import redirect, session, render_template, g
from functools import wraps
import sqlite3
import requests
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize
from sqlite3 import Error

# https://www.sqlitetutorial.net/sqlite-python/create-tables/
def create_connection(db_file):
  conn = None
  try:
    conn = sqlite3.connect(db_file)
    return conn
  except Error as e:
    print(e)
  return conn

def create_table(conn, create_table_sql):
  try:
    c = conn.cursor()
    c.execute(create_table_sql)
  except Error as e:
    print(e)

def schema():
  database = r"ce.db"
  sql_users = """ CREATE TABLE IF NOT EXISTS users (
	user_id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL,
	hash VARCHAR(255) NOT NULL,
	UNIQUE(name));"""

  sql_groups = """ CREATE TABLE IF NOT EXISTS groups (
	group_name VARCHAR(255) NOT NULL,
	turn INTEGER NOT NULL,
	user_id INTEGER,
	FOREIGN KEY (user_id) REFERENCES users(user_id)
	ON UPDATE CASCADE
	ON DELETE CASCADE);"""

  sql_sentences = """ CREATE TABLE IF NOT EXISTS sentences (
	counter INTEGER PRIMARY KEY,
	game_id INTEGER,
	sentence TEXT,
	group_name VARCHAR(255),
	user_id INTEGER,
	time TIMESTAMP,
	FOREIGN KEY (game_id) REFERENCES games(game_id)
	ON UPDATE CASCADE
	ON DELETE CASCADE,
	FOREIGN KEY (group_name) REFERENCES groups(group_name)
	ON UPDATE CASCADE
	ON DELETE NO ACTION,
	FOREIGN KEY (user_id) REFERENCES users(user_id)
	ON UPDATE CASCADE
	ON DELETE NO ACTION);"""

  sql_games = """ CREATE TABLE IF NOT EXISTS games (
	game_id INTEGER PRIMARY KEY,
	active INTEGER,
	turn INTEGER,
	group_name VARCHAR(255) NOT NULL,
	FOREIGN KEY (turn) REFERENCES groups(turn)
	ON UPDATE CASCADE
	ON DELETE CASCADE,
	FOREIGN KEY (group_name) REFERENCES groups(group_name)
	ON UPDATE CASCADE
	ON DELETE NO ACTION);"""

  conn = create_connection(database)

  if conn is not None:
    create_table(conn, sql_users)
    create_table(conn, sql_groups)
    create_table(conn, sql_sentences)
    create_table(conn, sql_games)
  else:
    print("Error! cannot create the database connection.")


# https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
# open database and return Row objects (namedtuples) from queries
def get_db():
  db=getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect("ce.db")
    db.row_factory = make_dicts #why function called without args????
  return db

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def number_sentences(text):
  return len(sent_tokenize(text))
