# Cadavre Exquis
Collaborative story-writing game implemented as web-application on Python 3.7.
In the live version a group of minimum 3 uses a pen and a piece of paper to collaboratively write a story ([more](https://en.wikipedia.org/wiki/Exquisite_corpse)).
Player #1 will start with a sentence and pass it on to the next in line, covering up
all but the last one or two lines, just enough to give player #2 a cue to continue the storyline with
the next sentence. Player #2 will then cover up all of player #1 and all but 1 or 2 lines of his/her
own sentence before passing the paper on to player #3, and so on...
When players run out of paper or decide to finish the game, the paper is uncovered/unfolded and the
story revealed.

1. Sign Up with a username and password.
2. You will need at least 3 players to start playing.
3. To start a new group, navigate to "Groups->Start New Group", pick a name for your group and add players (you will need to know their usernames and they are case-sensitive).
4. To add players to an existing group, navigate to "Groups->My Groups" and click on the group name to view details and add members.
5. To start a game, click on the top left "Cadavre Exquis" welcome menu, click on "Start New Game", select a group and start playing!
6. Make sure you write one full sentence. The next in line will be shown the last 7 words of it.
7. When you wish to end the game and it is your turn, just select "End Story" when you are done writing.
8. To view the full story, go to "Archive" where you will find a list of all your stories.

## Usage
Runs on Flask. I run my project out of a virtual environment folder py. To activate it, execute:
```
cd py/bin
. ./activate
```

Then, cd into the project directory and export the FLASK_APP environment variable, setting it to the filename and run:
```
export FLASK_APP=flask_app.py
flask run
```

## Installation

Installed packages required are:
* certifi (2019.9.11)
* chardet (3.0.4)
* Click (7.0)
* Flask (1.1.1)
* Flask-Session (0.3.1)
* idna (2.8)
* itsdangerous (1.1.0)
* Jinja2 (2.10.3)
* MarkupSafe (1.1.1)
* nltk (3.4.5)
* pip (9.0.1)
* pkg-resources (0.0.0)
* requests (2.22.0)
* setuptools (39.0.1)
* six (1.13.0)
* urllib3 (1.25.6)
* Werkzeug (0.16.0)

## Schema
If the database does not yet exist, run:

    python db_setup.py

which will create the following schema:

    CREATE TABLE users (
    	user_id INTEGER PRIMARY KEY,
	    name VARCHAR(255) NOT NULL,
	    hash VARCHAR(255) NOT NULL,
	    UNIQUE(name));

    CREATE TABLE IF NOT EXISTS groups (
      group_name VARCHAR(255) NOT NULL,
    	turn INTEGER NOT NULL,
	    user_id INTEGER,
	    FOREIGN KEY (user_id) REFERENCES users(user_id)
	    ON UPDATE CASCADE
	    ON DELETE CASCADE);

    CREATE TABLE IF NOT EXISTS sentences (
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
	    ON DELETE NO ACTION);

    CREATE TABLE IF NOT EXISTS games (
	    game_id INTEGER PRIMARY KEY,
	    active INTEGER,
	    turn INTEGER,
	    group_name VARCHAR(255) NOT NULL,
	    FOREIGN KEY (turn) REFERENCES groups(turn)
	    ON UPDATE CASCADE
	    ON DELETE CASCADE,
	    FOREIGN KEY (group_name) REFERENCES groups(group_name)
	    ON UPDATE CASCADE
	    ON DELETE NO ACTION);

  # Limitations

  * Players can only play one game at a time
  * In order to add members to a group, the members need to have created an account and the user adding them,
  needs to know their usernames. There is no way to look these up and there is no way for a user to look up
  and/or join an existing group.
  * There is no email address linked to the accounts and there is also no way to recover/reset forgotten passwords.
  * The layout and GUI can be embellished, it is very rudimentary. e.g. the final stories could be displayed with
  varying colors/fonts to tell one player's sentence from the next.
  * All the warnings/flash messages would probably better be handled in Javascript, instead of using Python flash messages.
  * When creating a group, the user needs to add him/herself and there is no check to ensure that the user creating is also in the group.
