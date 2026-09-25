"""Hitster Mega Website - Flask web app.

Routes:

Pages:
/                       Home page and game
/add_song               Submit a song to the database
/songlist               List of approved songs
/help                   Forum post list
/help/<page_id>         Single forum post and its comments
/admin                  Admin panel
/banned                 Ban notice and appeal page

Backend:
/login                  Redirects to Google sign in
/login/authorized       Creates and updates the user in database
/logout                 Clears the sessions login
/process-data           Submits game data
/reset                  Clears all game boxes
/submit                 Create a forum post
/reply                  Comment on a forum post
/deletepost             Delete a post
/resolvepost            Mark a post as resolved
/ban,/unban             Ban or unban a user
/approvesong,/denysong  Approve or delete a submitted song
/banappeal              Email a ban appeal to the admin address
error handler           renders error page
"""

import sqlite3
import os
import random
import datetime
from functools import wraps
import spotipy
from flask import Flask, render_template, abort, session, jsonify, request, redirect, url_for
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
# Load environment variables from .env file
load_dotenv()
clientID = os.getenv("SPOTIFY_CLIENT_ID")
clientSecret = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = 'https://example.com/'
# Authenticate with Spotify API
oauth_object = spotipy.SpotifyOAuth(clientID, clientSecret, REDIRECT_URI)
token_dict = oauth_object.get_access_token()
token = token_dict['access_token']

SPOTIFYOBJECT = spotipy.Spotify(auth=token)
spotify_user_name = SPOTIFYOBJECT.current_user()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = 'https://127.0.0.1:5000/login/callback'


oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=google_client_id,
    client_secret=google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Configure directory and constraints for uploaded song covers
app.config['COVER_FOLDER'] = os.path.join(app.root_path, 'static', 'cover_art')
os.makedirs(app.config['COVER_FOLDER'], exist_ok=True)
ALLOWED_COVER_EXTENSIONS = {'.jpg'}
MAX_COVER_SIZE = 5 * 1024 * 1024

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)


class DataStore():
    """Holds shared game box data"""
    boxdata = None


def login_required(login_location):
    """Redirects to login_needed.html unless the user has a google_token."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'google_token' not in session:
                return render_template("login_needed.html", login_location=login_location)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Returns the logged in user's Google userinfo dict."""
    return session['google_token'].get('userinfo')


def is_banned(cur, user_id):
    """Returns True if the user with the given id is banned."""
    row = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user_id,)).fetchone()
    return bool(row and row[0] == 1)


def load_user_context(cur, user):
    """Returns {user_name, user_picture, isadmin} for the given user."""
    # Looks up admin status using the Google 'sub' id as the primary key
    isadmin = cur.execute("SELECT ISADMIN FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
    return {
        "user_name": user.get('name'),
        "user_picture": user.get('picture'),
        "isadmin": bool(isadmin and isadmin[0] == 1),
    }


def save_cover_image(cover_file, song_id):
    """Validates and saves a song cover upload, if one was provided."""
    if not cover_file or cover_file.filename == '':
        return
    filename = secure_filename(cover_file.filename)
    ext = os.path.splitext(filename)[1].lower()
    # Falls back to .jpg if the uploaded extension isn't in the allowed set
    if ext not in ALLOWED_COVER_EXTENSIONS:
        ext = '.jpg'
    # Calculates file size
    cover_file.seek(0, os.SEEK_END)
    size = cover_file.tell()
    cover_file.seek(0)
    # Reject the upload if it's over the size limit
    if size > MAX_COVER_SIZE:
        return
    # Named after the song's id so the cover can be found again without storing a path
    cover_path = os.path.join(app.config['COVER_FOLDER'], f"{song_id}{ext}")
    cover_file.save(cover_path)


# Defines the home route
@app.route("/")
@login_required("Home")
def home():
    """Route for the home page
    Returns:
    home.html if the user is logged in
    A redirect to the ban page if the user is banned
    login_needed.html if the user is not logged in
    """
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    # This query is on most pages in the website and it checks if users are banned
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    ctx = load_user_context(cur, user)
    # This query selects all the songs
    data = cur.execute("SELECT id from Song WHERE Approved = 1").fetchall()
    # Pick a random song ID from all approved songs in the database
    song_id = data[random.randint(0, len(data) - 1)][0]
    res = cur.execute("""SELECT name, artist, releaseyear FROM Song WHERE id = ?""",
                      (song_id,)).fetchall()
    name = res[0]
    song_title = name[0]
    artist = res[0][1]
    year = res[0][2]
    search_song = f"{name[0]}"
    # This uses the spotify api to find the song on spotify
    results = SPOTIFYOBJECT.search(f"q=track:{song_title}%20artist:{artist}%20year:{year}")
    songs_dict = results['tracks']
    song_items = songs_dict['items']
    # Takes the top search result
    song = song_items[0]['uri']
    # this query gets all the relevant information in all the boxes
    boxsong = cur.execute("""SELECT boxes.boxid, song.id,name,releaseyear,artist FROM boxes
                             JOIN song ON boxes.songid = song.id""").fetchall()
    title = "Home"
    conn.commit()
    conn.close()

    return render_template("home.html",
                           title=title,
                           song=song,
                           name=name,
                           search_song=search_song,
                           year=year,
                           artist=artist,
                           boxsong=boxsong,
                           song_id=song_id,
                           **ctx)


# Defines the addsong route
@app.route("/add_song", methods=["GET", "POST"])
@login_required("add a song")
def add_song():
    """Route for the add song page
    Returns:
    add_song.html
    POST: Validates inputs, inserts the song and genre links into the database,
    saves uploaded cover art, and redirects to the home page."""
    show_error_none = False
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if is_banned(cur, user.get('sub')):
        conn.close()
        return redirect(url_for('banned'))
    if request.method == "POST":
        song_name = request.form.get("sname")
        song_year = request.form.get("syear")
        song_artist = request.form.get("sartist")
        selected_genres = request.form.getlist("genres")
        # Verify that all required fields are filled
        if all(x is not None and x.strip() != "" for x in (song_name, song_year, song_artist)):
            # inserts the songs information into the database
            cur.execute(
                "INSERT INTO song (name, releaseyear, artist, approved) VALUES (?, ?, ?, ?)",
                (song_name, song_year, song_artist, 0)
            )
            song_id = cur.lastrowid
            # A song can belong to multiple genres, linked via the genresong table
            for genre_id in selected_genres:
                # inserts the songs genres into the genresong linking table
                cur.execute(
                    "INSERT INTO genresong (songid, genreid) VALUES (?, ?)",
                    (song_id, genre_id)
                )
            save_cover_image(request.files.get("scover"), song_id)
            conn.commit()
            conn.close()
            return redirect(url_for("home"))
        else:
            show_error_none = True
    # gets all the genres for the user to choose from
    genres = cur.execute("SELECT Genreid, name FROM Genre").fetchall()
    ctx = load_user_context(cur, user)
    title = "Add a song"
    conn.close()
    return render_template(
        "add_song.html",
        title=title,
        show_error_none=show_error_none,
        genres=genres,
        **ctx
    )


# defines the songlist route
@app.route("/songlist")
@login_required("Songs List")
def song_list():
    """Route for the song list page
    Returns:
        song_list.html"""
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    # gets all the songs to be displayed on the page
    songs = cur.execute("SELECT id,name,artist,releaseyear FROM song WHERE Approved = 1").fetchall()
    ctx = load_user_context(cur, user)
    title = "Songs List"
    # gets all the songs and their genres
    genre_rows = cur.execute("SELECT SongID, GenreID FROM GenreSong").fetchall()
    # Connect genre IDs to each song ID using a dictionary
    song_genres = {}
    for song_id, genre_id in genre_rows:
        song_genres.setdefault(song_id, []).append(genre_id)
    conn.commit()
    conn.close()

    return render_template("song_list.html",
                           title=title,
                           songs=songs,
                           song_genres=song_genres,
                           **ctx)


# defines the help route
@app.route("/help")
@login_required("Help Forums")
def forum():
    """Route for the help page
    Returns:
        forum.html"""
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    ctx = load_user_context(cur, user)
    # gets all the posts to be displayed on the page
    posts = cur.execute("""SELECT PostID,
                                  OwnerID,
                                  Title,
                                  Resolved,
                                  PostDate,
                                  OwnerName,
                                  OwnerPFP FROM ForumPost""").fetchall()
    title = "Help Forums"
    conn.commit()
    conn.close()

    return render_template("forum.html",
                           title=title,
                           user_id=user.get('sub'),
                           posts=posts,
                           **ctx)


# defines the individual post page
@app.route("/help/<int:page_id>")
@login_required("Help Forums")
def helppage(page_id):
    """Route for the individual forum page
    Returns:
        forumpage.html"""
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    ctx = load_user_context(cur, user)
    # gets all the posts information where it matches the post from the page the user is on
    postinfo = cur.execute(
        """SELECT PostID,
                  OwnerID,
                  Title,
                  Content,
                  Resolved,
                  OwnerName,
                  OwnerPFP FROM ForumPost WHERE PostID = ?""",(page_id,)).fetchone()
    # gets all the comments on the post the user is on
    comments = cur.execute(
        "SELECT content, ownername, ownerpfp FROM ForumComment WHERE ParentID = ?",
        (page_id,)
    ).fetchall()
    title = postinfo[2]
    conn.commit()
    conn.close()

    return render_template("forumpage.html",
                           title=title,
                           postinfo=postinfo,
                           comments=comments,
                           page_id=page_id,
                           **ctx)


# defines the newpost route
@app.route("/help/newpost")
@login_required("Help Forums")
def newpost():
    """Route for the create forum post page
    Returns:
        newpost.html"""
    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    ctx = load_user_context(cur, user)
    title = "New Post"
    conn.commit()
    conn.close()

    return render_template("newpost.html", title=title, **ctx)


# defines the admin route
@app.route("/admin")
@login_required("Help Forums")
def admin():
    """Route for the admin panel page
    Returns:
        admin.html
    Regular users get a 403 error
    """

    user = get_current_user()
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    ctx = load_user_context(cur, user)
    # gives the user a forbidden error if they are not an admin
    if not ctx["isadmin"]:
        abort(403)
    if is_banned(cur, user.get('sub')):
        return redirect(url_for('banned'))
    # gets all the information on all the users
    users = cur.execute("""SELECT id,
                           name,
                           profile_pic,
                           isadmin,
                           date_joined,
                           isbanned,
                           banreason FROM Users""").fetchall()
    # gets all the songs that are yet to be approved
    unnaproved_songs = cur.execute("""SELECT id,
                                      name,
                                      releaseyear,
                                      artist from Song WHERE Approved = 0""").fetchall()
    title = "Admin"
    conn.commit()
    conn.close()

    return render_template("admin.html",
                           title=title,
                           users=users,
                           unnaproved_songs=unnaproved_songs,
                           **ctx)


# defines the banned route
@app.route("/banned")
def banned():
    """Route for the banned page
    shown to users who have been banned by an admin
    has 2 versions one where the user has appealed and one where they havent
    Returns:
        banned.html"""
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        # gets all the information on the current user
        isbanned = cur.execute("""SELECT Isbanned,Banreason FROM Users WHERE id = ?""",
                               (user.get('sub'),)).fetchone()
        # checks if the user is banned
        if isbanned[0] == 1:
            # this query finds out if the user has appealed their ban yet
            hasappealed = cur.execute("SELECT HasAppealed FROM Users WHERE id = ?",
                                      (user.get('sub'),)).fetchone()
            return render_template("banned.html", banned=isbanned, hasappealed=hasappealed)
        else:
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))


# redirects the user to the gooogle login
@app.route("/login")
def login():
    """
    Returns:
        url for google login"""
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/login/authorized')
def authorized():
    """
    Retrieves user information and updates/creates that users information in the database
    Returns:
        sends user to the home route"""
    google_token = google.authorize_access_token()
    if google_token is None:
        return 'Login failed.'
    session['google_token'] = google_token
    user = google_token.get('userinfo')

    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%d-%m-%y")
    # this query updates the users information in the database
    cur.execute("""
        INSERT INTO users (id, name, email, profile_pic, date_joined, ISADMIN, Isbanned)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            profile_pic = excluded.profile_pic
    """, (
        user.get('sub'),
        user.get('name'),
        user.get('email'),
        user.get('picture'),
        now,
        0,
        0

    ))

    conn.commit()
    conn.close()

    return redirect(url_for('home'))


# logs the user out
@app.route('/logout')
def logout():
    """Logs the user out
    Returns:
        redircts the user to the home route"""
    session.pop('google_token', None)
    return redirect(url_for('home'))


# this route processes the games data
@app.route('/process-data', methods=['POST'])
def process_data():
    """Saves the current game data
    Takes game information updates box data in the database
    Returns:
        json response"""
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    payload = request.json
    data = payload.get('data', {})
    # deletes the old information from the database
    cur.execute("DELETE FROM boxes")
    for box, song_ids in data.items():
        if song_ids:
            for song_id in song_ids:
                if song_id is not None:
                    # inserts the updated game information into the database
                    cur.execute("INSERT INTO boxes (boxid, songid) VALUES (?, ?)", (box, song_id))
    conn.commit()
    conn.close()
    return jsonify({'result': 'success'})


# this route clears all the games boxes
@app.route('/reset', methods=['POST'])
def reset():
    """Clears all the boxes in the game
    Returns:
    json response"""
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    # clears all the boxes
    cur.execute("UPDATE boxes SET songid = NULL")
    conn.commit()
    conn.close()
    return jsonify({'result': 'success'})


# this route inserts the users new post into the database
@app.route('/submit', methods=['POST'])
def submit():
    """Processes new forum post creation and uploads information to the database
    Returns:
    redirects user to the forum page"""
    post_title = request.form['title']
    post_content = request.form['content']
    post_time = datetime.datetime.now().strftime("%d-%m-%y")

    user = session.get('google_token', {}).get('userinfo', {})
    user_name = user.get('name')
    user_picture = user.get('picture')
    user_id = user.get('sub')

    if not user_id:
        return redirect(url_for('home'))

    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    # inserts the users post information into the database
    cur.execute(
        "INSERT INTO ForumPost (OwnerID, title, content, PostDate, Ownername, OwnerPFP, Resolved)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, post_title, post_content, post_time, user_name, user_picture, 0)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("forum"))


# this route runs when a user replys to a forum post
@app.route('/reply', methods=['POST'])
def reply():
    """Processes comments to forum posts.
    Returns:
        Redirects users to the forum page they came from
    """
    comment_content = request.form['reply']
    page_id = request.form['page_id']

    user = session.get('google_token', {}).get('userinfo', {})
    user_name = user.get('name')
    user_picture = user.get('picture')
    user_id = user.get('sub')

    if not user_id:
        return redirect(url_for('home'))

    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()

    # inserts the comment into the database
    cur.execute(
        """INSERT INTO ForumComment (OwnerID,
                                     content,
                                     ParentID,
                                    OwnerName,
                                    OwnerPFP) VALUES (?, ?, ?, ?, ?)""",
        (user_id, comment_content, page_id, user_name, user_picture)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("helppage", page_id=page_id))



@app.route('/unban', methods=['POST'])
def unban():
    """Unbans the specified user and sends them an email
    Returns:
    url for the page the user came from"""
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # this query unbans the user in the database
        cur.execute("UPDATE Users SET Isbanned = 0 WHERE id = ?", (user_id,))
        # this query clears the users banreason
        cur.execute("UPDATE Users SET Banreason = Null WHERE id = ?", (user_id,))
        # this query gets the unbanned users information
        userinfo = cur.execute("SELECT HasAppealed,email,Name FROM Users WHERE id = ?",
                               (user_id,)).fetchone()
        # checks if the unbanned user has sent an appeal and sends the appropriate email
        if userinfo[0] == 0:
            msg = Message(
                subject="Ban status",
                recipients=[userinfo[1]]
            )
            msg.body = (
                f"Hello {userinfo[2]} if you are seeing this email it means that you have been"
                " unbanned from the Hitster Mega Website"
            )

            mail.send(msg)
        # checks if the unbanned user has sent an appeal and sends the appropriate email
        if userinfo[0] == 1:
            msg = Message(
                subject="Ban appeal",
                recipients=[userinfo[1]]
            )
            msg.body = (
                f"Hello {userinfo[2]} if you are seeing this email it means that your appeal has"
                " been accepted and you have been unbanned from the Hitster Mega Website"
            )

            mail.send(msg)
        # this query resets the users appeal so that if they are banned again they can appeal again
        cur.execute("UPDATE Users SET HasAppealed = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs when an admin bans a user
@app.route('/ban', methods=['POST'])
def ban():
    """Bans the specified user deletes their posts and sends them an email with their ban reason
    Returns:
    url for the page the user came from"""
    user_id = request.form.get('user_id')
    ban_reason = request.form.get('ban_reason')
    if user_id and ban_reason:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # bans the user in the database
        cur.execute(
            "UPDATE Users SET Isbanned = 1, BanReason = ? WHERE id = ?",
            (ban_reason, user_id)
        )
        # deletes all the banned users posts
        cur.execute("DELETE FROM ForumPost WHERE OwnerID = ?", (user_id,))
        # gets the appropriate information on the user
        userinfo = cur.execute("SELECT HasAppealed,email,Name FROM Users WHERE id = ?",
                               (user_id,)).fetchone()
        # sends the user an email informing them of their ban
        msg = Message(
            subject="Ban",
            recipients=[userinfo[1]]
        )
        msg.body = (
            f"Hello {userinfo[2]} if you are seeing this email it means that you have been"
            f" banned from the Hitster Mega Website for {ban_reason}"
        )

        mail.send(msg)

        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs when an admin promotes a user to an admin
@app.route('/promoteadmin', methods=['POST'])
def promoteadmin():
    """Grants a user admin privileges
    Returns:
    url for the page the user came from"""
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # makes the user an admin in the database
        cur.execute("UPDATE Users SET ISADMIN = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs whenever an admin demotes an admin to a user
@app.route('/demoteadmin', methods=['POST'])
def demoteadmin():
    """Revokes a users admin privileges
    Returns:
    url for the page the user came from"""
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # makes the admin a user in the database
        cur.execute("UPDATE Users SET ISADMIN = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs whenever an admin approves a users song
@app.route('/approvesong', methods=['POST'])
def approvesong():
    """Admin route that approves a submitted song
    Returns:
    url for the page the user came from"""
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # makes the song approved in the database so that it can show up on the website
        cur.execute("UPDATE Song SET Approved = 1 WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs whenever an admin denys a users song request
@app.route('/denysong', methods=['POST'])
def denysong():
    """Admin route that denys and deletes a submitted song
    Returns:
    url for the page the user came from"""
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # these querys deletes the song from the genre and song table
        cur.execute("DELETE FROM genresong WHERE songid = ?", (song_id,))
        cur.execute("DELETE FROM Song WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
        # Remove uploaded cover art file from storage if it exists
        cover_folder = app.config.get('COVER_FOLDER')
        image_filename = f"{song_id}.jpg"
        image_path = os.path.join(cover_folder, image_filename)
        # deletes the image from the coverart folder
        if os.path.exists(image_path):
            os.remove(image_path)
    return redirect(request.referrer or url_for('home'))


# this route runs when a admin or the owner of a post deletes it
@app.route('/deletepost', methods=['POST'])
def deletepost():
    """Deletes a specified post from the database
    Returns:
    url for the page the user came from"""
    post_id = request.form.get('post_id')
    if post_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # deletes the post from the database
        cur.execute("DELETE FROM ForumPost WHERE POSTID = ?", (post_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs when a admin or the owner of a post resolves it
@app.route('/resolvepost', methods=['POST'])
def resolvepost():
    """marks a post as resolved
    Returns:
    url for the page the user came from"""
    post_id = request.form.get('post_id')
    if post_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        # resolves the post in the database
        cur.execute("UPDATE ForumPost SET Resolved = 1 WHERE POSTID = ?", (post_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('home'))


# this route runs when a user requests a ban appeal
@app.route('/banappeal', methods=['post'])
def banappeal():
    """submits a ban appeal email on behalf of a banned user
    updates the users Hasappealed in the database to prevent duplicate appeals
    Returns:
    route for the banned papge"""
    appeal_reason = request.form['AppealReason']
    content = request.form['content']
    user = session['google_token'].get('userinfo')
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    # gets all the users information
    userinfo = cur.execute(
        "SELECT id,name,email,Isbanned,Banreason,HasAppealed FROM Users WHERE id = ?",
        (user.get('sub'),)
    ).fetchone()
    # sends an email with the users appeal to the admin email
    if userinfo[5] == 0:
        msg = Message(
            subject=f"{userinfo[2]} is requesting a ban appeal for {userinfo[4]}",
            recipients=["hitstermegawebsite@gmail.com"]
        )
        msg.body = (
            f'The reason for the appeal is "{appeal_reason}".'
            f' They provided the following information "{content}" '
        )

        mail.send(msg)
        cur.execute("UPDATE Users SET HasAppealed = ? WHERE id = ?", (1, userinfo[0]))
    conn.commit()
    conn.close()

    return redirect(url_for("banned"))


# handles 500 errors
@app.errorhandler(500)
def server_error(servererror):
    """Error handler for 500 errors
    Returns:
    error.html with status code 500"""
    return render_template('error.html',
                           title=servererror,
                           message="""The website's server encountered
                           an unexpected condition that prevented it
                           from fulfilling your request""",
                           code=500)


# handles 404 errors
@app.errorhandler(404)
def pagenotfound(notfound):
    """Error handler for 404 errors
    Returns:
    error.html with status code 404"""
    return render_template("error.html",
                           title=notfound, message="""We can't
                            seem to find the page
                           you were looking for""",
                           code=404)


# handles 403 errors
@app.errorhandler(403)
def pageforbidden(notfound):
    """Error handler for 403 errors
    Returns:
    error.html with status code 403"""
    return render_template("error.html",
                           title=notfound,
                           message="""You dont have permisson to acsess this page""",
                           code=403)


if __name__ == "__main__":
    app.run(debug=True)
