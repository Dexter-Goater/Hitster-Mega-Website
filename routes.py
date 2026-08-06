from flask import Flask, render_template, abort, session, jsonify, request,redirect,url_for,flash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import sqlite3
import os
import random
import json
import spotipy
import webbrowser
import requests
import datetime
from werkzeug.utils import secure_filename
load_dotenv()
username = 'wqgfeis2dlz27xoecb7h5oqfa'
clientID = os.getenv("SPOTIFY_CLIENT_ID")
clientSecret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = 'https://example.com/'
oauth_object = spotipy.SpotifyOAuth(clientID, clientSecret, redirect_uri)
token_dict = oauth_object.get_access_token()
token = token_dict['access_token']

spotifyObject = spotipy.Spotify(auth=token)
user_name = spotifyObject.current_user()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = 'https://127.0.0.1:5000/login/callback'

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=google_client_id,
    client_secret=google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

isadmin = False
app.config['COVER_FOLDER'] = os.path.join(app.root_path, 'static', 'cover_art')
os.makedirs(app.config['COVER_FOLDER'], exist_ok=True)


class DataStore():
    boxdata = None

@app.route("/")
def home():
    user_name = None
    user_picture = None
    login_location = "Home"
    if 'google_token' in session:
            user = session['google_token'].get('userinfo')
            if user:
                user_name = user.get('name')
                user_picture = user.get('picture')
      
            conn = sqlite3.connect("Hitster.db")
            cur = conn.cursor()
            if user:
                admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
                if admin:
                    if admin[0] == 1:
                        isadmin = True
                    else:
                        isadmin = False
                else:
                    isadmin = False
                
            data = cur.execute("SELECT id from Song WHERE Approved = 1").fetchall()
            id = data[random.randint(0, len(data) - 1)][0]
            res = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {id}").fetchall()
            name = res[0]
            artist = res[0][1]
            year = res[0][2]
            search_song = f"{name[0]}"
            results = spotifyObject.search(f"q=track:{name}%20artist:{artist}%20year:{year}")
            songs_dict = results['tracks']
            song_items = songs_dict['items']
            song = song_items[0]['uri']
            boxsong = cur.execute("SELECT boxes.boxid, song.* FROM boxes JOIN song ON boxes.songid = song.id").fetchall()
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
                                user_name=user_name,
                                user_picture=user_picture,
                                isadmin=isadmin)
    else:
        return render_template("login_needed.html",login_location=login_location)
    

@app.route("/add_song", methods=["GET", "POST"])
def add_song():
    user_name = None
    user_picture = None
    show_error_none = False
    isadmin = False
    login_location = "add a song"
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        if request.method == "POST":
            song_name = request.form.get("sname")
            song_year = request.form.get("syear")
            song_artist = request.form.get("sartist")
            if all(x is not None and x.strip() != "" for x in (song_name, song_year, song_artist)):
                cur.execute(
                    "INSERT INTO song (name, releaseyear, artist, approved) VALUES (?, ?, ?, ?)",
                    (song_name, song_year, song_artist, 0)
                )
                song_id = cur.lastrowid
                cover_file = request.files.get("scover")
                if cover_file and cover_file.filename != '':
                    _, ext = os.path.splitext(cover_file.filename)
                    if not ext:
                        ext = '.jpg'
                    new_filename = f"{song_id}{ext}"
                    cover_path = os.path.join(app.config['COVER_FOLDER'], new_filename)
                    cover_file.save(cover_path)
                conn.commit()
                conn.close()
                return redirect(url_for("home"))
            else:
                show_error_none = True
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True     
        title = "Add a song"
        conn.close()
        return render_template(
            "add_song.html",
            title=title,
            user_name=user_name,
            user_picture=user_picture,
            show_error_none=show_error_none,
            isadmin=isadmin
        )
    else:
        return render_template("login_needed.html", login_location=login_location)
    

@app.route("/songlist")
def song_list():
    user_name = None
    user_picture = None
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Songs List"

    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        songs = cur.execute("SELECT id,name,artist,releaseyear FROM song WHERE Approved = 1").fetchall()
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin[0] == 1:
            isadmin = True
        title = "Songs List"
        genre_rows = cur.execute("SELECT SongID, GenreID FROM GenreSong").fetchall()
        song_genres = {}
        for song_id, genre_id in genre_rows:
            song_genres.setdefault(song_id, []).append(genre_id)
        conn.commit()
        conn.close()

        return render_template("song_list.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            isadmin=isadmin,
                            songs=songs,
                            song_genres=song_genres)
    else:
        return render_template("login_needed.html",login_location=login_location)    
    

@app.route("/help")
def help():
    user_name = None
    user_picture = None
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin[0] == 1:
            isadmin = True
        posts = cur.execute("SELECT PostID,OwnerID,Title,Resolved,PostDate,OwnerName,OwnerPFP FROM ForumPost").fetchall()
        title = "Help Forums"
        conn.commit()
        conn.close()

        return render_template("forum.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            isadmin=isadmin,
                            posts=posts)
    else:
        return render_template("login_needed.html",login_location=login_location)  

@app.route("/help/<int:page_ID>")  
def helppage(page_ID):
    user_name = None
    user_picture = None
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin[0] == 1:
            isadmin = True
        postinfo = cur.execute("SELECT PostID,OwnerID,Title,Content,Resolved,OwnerName,OwnerPFP FROM ForumPost WHERE PostID = ?",(page_ID,)).fetchone()
        comments = cur.execute(f"SELECT * FROM ForumComment WHERE CommentID IN (SELECT CommentID FROM ForumComment WHERE ParentID = ?)", (page_ID,)).fetchall()
        title = postinfo[2]
        conn.commit()
        conn.close()

        return render_template("forumpage.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            isadmin=isadmin,
                            postinfo=postinfo,
                            comments=comments,
                            page_ID = page_ID)
    else:
        return render_template("login_needed.html",login_location=login_location)     

@app.route("/help/newpost")
def newpost():
    user_name = None
    user_picture = None
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin[0] == 1:
            isadmin = True
        title = "New Post"
        conn.commit()
        conn.close()

        return render_template("newpost.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            isadmin=isadmin,)
    else:
        return render_template("login_needed.html",login_location=login_location)      
    
@app.route("/login")
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/authorized')
def authorized():
    token = google.authorize_access_token()
    if token is None:
        return 'Login failed.'
    session['google_token'] = token
    user = token.get('userinfo')

    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()

    existing = cur.execute("SELECT id FROM users WHERE id = ?", (user.get('sub'),)).fetchone()
    is_new_user = existing is None

    now = datetime.datetime.now().strftime("%d-%m-%y")

    cur.execute("""
        INSERT INTO users (id, name, email, profile_pic, date_joined)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            profile_pic = excluded.profile_pic
    """, (
        user.get('sub'),
        user.get('name'),
        user.get('email'),
        user.get('picture'),
        now
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('home'))


@app.route('/process-data', methods=['POST'])
def process_data():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    data = request.json['data']
    print(data)
    result = {k: v[0].split('\n')[0] for k, v in data.items() if v}
    print(result)
    
    song_ids = {}
    for box, name in result.items():
        row = cur.execute("SELECT id FROM song WHERE name = ?", (name,)).fetchone()
        song_ids[box] = row[0] if row else None
    
    cur.execute("UPDATE boxes SET songid = NULL")
    for box, song_id in song_ids.items():
        if song_id is not None:
            cur.execute("UPDATE boxes SET songid = ? WHERE boxid = ?", (song_id, box))
    
    conn.commit()
    conn.close()
    print(song_ids)
    DataStore.boxdata = song_ids
    return jsonify({'result': result, 'song_ids': song_ids})

@app.route('/reset', methods=['POST'])
def reset():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    cur.execute("UPDATE boxes SET songid = NULL")
    conn.commit()
    conn.close()

@app.route('/submit', methods=['POST'])
def submit():
    post_title = request.form['title']
    post_content = request.form['content']
    post_time = datetime.datetime.now().strftime("%d-%m-%y")

    user = session['google_token'].get('userinfo')
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    
    if user:
        user_name = user.get('name')
        user_picture = user.get('picture')
        user_id = user.get('sub')
    cur.execute(
        "INSERT INTO ForumPost (OwnerID, title, content, PostDate, Ownername, OwnerPFP, Resolved) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        (user_id, post_title, post_content, post_time, user_name, user_picture, 0)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for("help"))

@app.route('/reply', methods=['POST'])
def reply():
    comment_content = request.form['reply']
    page_ID = request.form['page_ID']

    user = session['google_token'].get('userinfo')
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    
    if user:
        user_name = user.get('name')
        user_picture = user.get('picture')
        user_id = user.get('sub')
    
    cur.execute(
        "INSERT INTO ForumComment (OwnerID, content, ParentID, OwnerName, OwnerPFP) VALUES (?, ?, ?, ?, ?)",
        (user_id, comment_content, page_ID, user_name, user_picture)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("help",page_ID=page_ID))


if __name__ == "__main__":
    app.run(debug=True)


   