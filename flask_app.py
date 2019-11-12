import os

from flask import Flask, render_template, request, session, redirect, flash, g
from flask_session import Session
from helpers import login_required, apology, get_db, query_db
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import sqlite3

# when/why do I need to import OS?

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
# Logs debugging info tracing how template was loaded
app.config["EXPLAIN_TEMPLATE_LOADING"] = True # so where is it?

# Ensure responses aren't cached - LOOK INTO THIS
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp() # temp storage? defaults to flask_session in current working dir
app.config["SESSION_PERMANENT"] = False #default to true, use perm sess, why false?
app.config["SESSION_TYPE"] = "filesystem"  #defaults to null
Session(app) #creates Session-object by passing it the application

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
  # stores row from group AND game JOINTLY- USERspecific
  session["userrow"]=query_db("SELECT * FROM games INNER JOIN groups ON groups.group_name=games.group_name INNER JOIN users ON users.user_id=groups.user_id WHERE users.user_id=? AND games.active=?", [session["user_id"], 1], one=True)
  # stores row from group AND game JOINTLY where user is group-member - GROUPspecific
  session["gamerow"] = query_db("SELECT * FROM groups INNER JOIN games ON games.group_name=groups.group_name INNER JOIN users ON groups.user_id=users.user_id WHERE groups.user_id=? AND games.active=?", [session["user_id"], 1], one=True)
  if session["userrow"] is None:
    if request.method == "POST":
      groups = query_db("SELECT group_name FROM groups WHERE user_id=?", [session["user_id"]], one=False)
      print("GROUPSSS ARE: ", groups)
      return render_template("new_game.html", groups=groups)
  else:
    return render_template("index.html", game=session["userrow"])

  return render_template("index.html", game=session["userrow"])

@app.route("/end_game", methods=["GET", "POST"])
@login_required
def end_game():
  if request.method == "POST":
    group_name = session["gamerow"]["group_name"]
    newsentence = request.form.get("newsentence")
    get_db().execute("INSERT INTO sentences (game_id, sentence, group_name, user_id, time) VALUES (:game_id, :sentence, :group_name, :user_id, :timestamp)", {"game_id":session["gamerow"]["game_id"], "sentence":newsentence, "group_name":group_name, "user_id":session["gamerow"]["user_id"], "timestamp":datetime.now()})
    get_db().execute("UPDATE games SET active=? WHERE group_name=?",(0, group_name))
    get_db().commit()
    return redirect("/archive")

  # select active game(s) from games where the group_id (in groups) is the same as the group_id in games
  # AND the user_id in groups is the same as session["user_id"]
  # ===> GET USER'S GAME IF ANY
  # IF NONE, BUTTON directing to new_game.html, route new_game (INSERT into games), redir to "/"
  # -- check if user's turn (use helper function isturn())
  #-- DISPLAY form with ROUND#, last sentence, textbox, "Submit&Next" Button (greys out/hides, pass control), cheat API, "submit&End Game" redir to "Reveal Story"
  # (-> archive, inactive)
@app.route("/archive", methods=["GET", "POST"])
@login_required
def archive():
  # these are all the sentences ever played by groups user is in, GROUP BY GAME AND ORDER BY TIMESTAMP, GIVE IT NAMES AS so accessible under 2nd qery
  sentences = query_db("SELECT game_id, sentence, time FROM sentences INNER JOIN groups ON groups.group_name=sentences.group_name INNER JOIN users ON users.user_id=groups.user_id WHERE users.user_id=? ORDER BY time", [session["user_id"]], one=False)
  games = query_db("SELECT games.game_id, time FROM sentences INNER JOIN groups ON groups.group_name=sentences.group_name INNER JOIN users ON users.user_id=groups.user_id INNER JOIN games ON games.game_id=sentences.game_id WHERE users.user_id=? AND games.active=? GROUP BY sentences.game_id ORDER BY time", [session["user_id"], 0], one=False)
  # create dict "stories" saving only date and story-string
  stories = {}
  for game in games:
    s = ""
    for sen in sentences:
      if sen["game_id"] == game["game_id"]:
        s = s + sen["sentence"] + " "
    stories[game["time"]] = s
  # save dict in session, beacuse for some reason passed on stories (originally a dict) variable via archive.html only contains game["time"]-key, not value(story)
  session["stories"] = stories
  return render_template("archive.html", stories=stories)

@app.route("/story/<stories>", methods=["GET", "POST"])
@login_required
def story(stories):
  # FYI - passed on stories (originally a dict) variable only contains selected time-key, not value(story) for some reason
  return render_template("story.html", stories=session["stories"][stories])


@app.route("/live_game", methods=["GET", "POST"])
@login_required
def live_game():
  if session["userrow"] is None:
    print("IS THIS COING OUT?")
    return redirect("/")

  # get last written sentence
  lastsntnc = query_db("SELECT * FROM sentences WHERE game_id=? and counter=(SELECT MAX(counter) FROM sentences)", [session["userrow"]["game_id"]], one=True)
  # if no previous sentence, this is the 1st round
  if lastsntnc is None:
    session["round"] = 1
    sentence = None
    lastplayer = None
  # otherwise get round (#of sentences in game +1), last player and last sentence to display
  else:
    session["round"] = 1 + query_db("SELECT COUNT(*) FROM sentences WHERE game_id=?", [session["userrow"]["game_id"]], one=True)["COUNT(*)"]
    lastplayer = query_db("SELECT name FROM users WHERE user_id=?", [lastsntnc["user_id"]], one=True)["name"]
    sentence = lastsntnc["sentence"]
  # if it is the user's turn (game's turn == user's's turn?)
  isturn = (session["gamerow"]["turn"] == session["userrow"]["turn"])
  # get current player's name to display who's turn it is if not user's
  player_id = query_db("SELECT user_id FROM groups WHERE group_name=? AND turn=?", [session["gamerow"]["group_name"], session["gamerow"]["turn"]], one=True)["user_id"]
  player = query_db("SELECT name FROM users WHERE user_id=?", [player_id], one=True)["name"]
  return render_template("live_game.html", round=session["round"], group_name=session["gamerow"]["group_name"], isturn=isturn, sentence=sentence, lastplayer=lastplayer, player=player) #parse group_name, turn, players


@app.route("/next", methods=["GET", "POST"])
@login_required
def next():
  if request.method == "POST":
    # insert written sentence into group's game
    group_name = session["gamerow"]["group_name"]
    newsentence = request.form.get("newsentence")
    get_db().execute("INSERT INTO sentences (game_id, sentence, group_name, user_id, time) VALUES (:game_id, :sentence, :group_name, :user_id, :timestamp)", {"game_id":session["gamerow"]["game_id"], "sentence":newsentence, "group_name":group_name, "user_id":session["gamerow"]["user_id"], "timestamp":datetime.now()})
    get_db().commit()
    # get current turn, max turn (# of players), increment & insert to DB
    turn = session["userrow"]["turn"]
    maxturn = query_db("SELECT MAX(turn) FROM groups WHERE group_name=?", [group_name], one=True)["MAX(turn)"]
    turn = 1 if turn == maxturn else turn + 1
    get_db().execute("UPDATE games SET turn=? WHERE game_id=?", (turn, session["userrow"]["game_id"]))
    get_db().commit()

    player_id = query_db("SELECT user_id FROM groups WHERE group_name=? AND turn=?", [session["gamerow"]["group_name"], turn], one=True)["user_id"]
    player = query_db("SELECT name FROM users WHERE user_id=?", [player_id], one=True)["name"]
    session["round"] += 1
  return render_template("live_game.html", round=session["round"], group_name=group_name, player=player)

@app.route("/new_game", methods=["GET", "POST"])
@login_required
def new_game():
  # get group_name from form & initiating user's turn
  if request.method == "POST":
    group_name = request.form.get("group")
    # think below unreachable, redundant, NO actually - ensures that users in active group cannot start playing another game!
    if query_db("SELECT * FROM games WHERE group_name=? AND active=?", [group_name, "1"], one=True):
      flash(group_name, " is already currently playing a game.")
      return redirect ("/live_game")
    # check that no game started with group where one of members is currently in an active game
    activeusers = query_db("SELECT users.user_id FROM games INNER JOIN groups ON groups.group_name=games.group_name INNER JOIN users ON users.user_id=groups.user_id WHERE games.active=?", [True,], one=False)
    members = query_db("SELECT user_id FROM groups WHERE group_name=?", [group_name], one=False)
    intersection = [value for value in activeusers if value in members]
    if intersection:
      flash("One or more members of selected group is busy playing.")
      return redirect("/")

    row = query_db("SELECT * FROM groups WHERE group_name=? AND user_id=?",[group_name, session["user_id"]], one=True)
    # new DB entry for new game
    get_db().execute("INSERT INTO games (active, turn, group_name) VALUES (:active, :turn, :group_name)", {"active":1, "turn":row["turn"], "group_name":row["group_name"]})
    get_db().commit()
    session["userrow"] = query_db("SELECT * FROM games INNER JOIN groups ON groups.group_name=games.group_name INNER JOIN users ON users.user_id=groups.user_id WHERE users.user_id=? AND games.active=?", [session["user_id"], 1], one=True)
    session["gamerow"] = query_db("SELECT * FROM groups INNER JOIN games ON games.group_name=groups.group_name INNER JOIN users ON groups.user_id=users.user_id WHERE groups.user_id=? AND games.active=?", [session["user_id"], 1], one=True)
    session["round"] = 1
    return render_template("live_game.html", turn=row["turn"], round=session["round"], isturn=True, group_name=group_name)
  else:
    groups = query_db("SELECT group_name FROM groups WHERE user_id=?", [session["user_id"]], one=False)
    print("GORUPS ARE:", groups)
    return render_template("new_game.html", groups=groups)


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
  # Clear session
  session.clear()
  #Ensure all fields filled out also if JS disabled
  if request.method == "POST":
    name = request.form.get("username")
    if not name:
      return apology("Please provide username") #handle in JS later OR USE flash? Nad below too? to het popup confirming stuff
    if not request.form.get("password") or not request.form.get("confirmation"):
      return apology("Please provide password and confirm it")

    hashp = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
    if not check_password_hash(hashp, request.form.get("confirmation")):
      return apology("password does not match confirmation")
    try:
      cur = get_db().execute("INSERT INTO users (name, hash) VALUES (:name, :hash)", {"name":name, "hash":hashp})
      get_db().commit()
    except sqlite3.IntegrityError:
      return apology("username already exists")

    # Login user automatically, storing their id in session, then layout will also show index.html? &menu?
    session["user_id"] = query_db("SELECT user_id FROM users WHERE name=?", [name], one=True)["user_id"]
    session["name"] = query_db("SELECT name FROM users WHERE user_id=?", [session["user_id"]], one=True)["name"]
    return render_template("index.html")
  else:
    return render_template("sign_up.html")

@app.route("/login", methods = ["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
      if not (request.form.get("username") and request.form.get("password")):
        return apology("Please provide username and password.") # handle in JS

      name = query_db("SELECT name FROM users WHERE name=?", [request.form.get("username")], one=True)
      if not name: # try if name is None
        return apology("Username not found.")

      name = name["name"]
      hash = query_db("SELECT hash FROM users WHERE name=?", [name], one=True)["hash"]

      if not check_password_hash(hash, request.form.get("password")):
        return apology("Password incorrect.")
      else:
        session["user_id"] = query_db("SELECT user_id FROM users WHERE name=?", [name], one=True)["user_id"]
        session["name"] = name
        return redirect ("/")
    return render_template("login.html")

@app.route("/new_group", methods = ["GET", "POST"])
@login_required
def new_group():
  if request.method == "POST":
    group_name = request.form.get("group_name")
    if not group_name:
      return apology("Please choose a group name!") # handle in JS

    if query_db("SELECT * FROM groups WHERE group_name=?", [group_name], one=True) is not None:
      return apology("Group name not available.")
    # set turn in group (for game) to 0 before looping
    turn=0
    # get usernames typed into fields[]
    for field in zip(request.form.getlist("fields[]")):
      if not field[0]:
        return apology("Please select player")
      user_id = query_db("SELECT user_id FROM users WHERE name=?", [field[0]], one=True)["user_id"]
      # check that user not duplicated in form AND group
      # if user enters inexistent username, remove all entries - handle in JS better...
      if (turn > 0) and (user_id is None):
        get_db().execute("DELETE FROM groups WHERE group_name=?", (group_name,))
        get_db().commit()
        return apology(field[0]+" is not registered")
      # if username entered is already in group, remove all entries - handle in JS better...
      checkusers = query_db("SELECT user_id FROM groups WHERE group_name=?", [group_name], one=False)
      if checkusers:
        for check in checkusers:
          print("CHECK IS:", check["user_id"])
          if (turn>0) and (user_id == check["user_id"]):
            get_db().execute("DELETE FROM groups WHERE group_name=?", (group_name,))
            get_db().commit()
            return apology(field[0]+ " is already added to "+ group_name)

      turn+=1
      try:
        get_db().execute("INSERT INTO groups (group_name, turn, user_id) VALUES (:group_name, :turn, :user_id)", {"group_name":group_name, "turn":turn, "user_id":user_id})
        get_db().commit()

      except sqlite3.IntegrityError:
        return apology("something went wrong in DB")
    return redirect("/groups")
  else:
    return render_template("new_group.html")

@app.route("/groups", methods=["GET", "POST"])
@login_required
def groups():
  groups = query_db("SELECT group_name FROM groups WHERE user_id=?", [session["user_id"]], one=False)

  if request.method == "POST":
    request.get("leave")
  else:
    return render_template("groups.html", groups=groups)

@app.route("/join_group", methods=["GET", "POST"])
@login_required
def join_group():
  #TODO
  return render_template ("join_group.html")

@app.route("/group/<group>")
@login_required
def group(group):
  #TODO .. DISPLAY ...db requests on group info based on group name, members, games, date
  return render_template("group.html", group=group)

@app.route("/add/<group>", methods=["GET", "POST"])
@login_required
def add(group):
  #if request.method == "POST":

  return render_template("add.html", group=group)

@app.route("/leave_group/<group>")
@login_required
def leave_group(group):
  get_db().execute("DELETE FROM groups WHERE user_id=? AND group_name=?", (session["user_id"], group))
  get_db().commit()
  flash("You left "+group+"!")
  return redirect("/groups")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")
