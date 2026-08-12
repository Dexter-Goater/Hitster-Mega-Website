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
from flask_mail import Mail,Message
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

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587                   
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'hitstermegawebsite@gmail.com'
app.config['MAIL_PASSWORD'] = 'wxzjessajytnbqwj' 
app.config['MAIL_DEFAULT_SENDER'] = 'hitstermegawebsite@gmail.com'

mail = Mail(app)



class DataStore():
    boxdata = None


@app.route("/")
def home():
    user_name = None
    user_picture = None
    isadmin = False
    login_location = "Home"
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True  
        data = cur.execute("SELECT id from Song WHERE Approved = 1").fetchall()
        id = data[random.randint(0, len(data) - 1)][0]
        res = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {id}").fetchall()
        name = res[0]
        song_title = name[0]
        artist = res[0][1]
        year = res[0][2]
        search_song = f"{name[0]}"
        results = spotifyObject.search(f"q=track:{song_title}%20artist:{artist}%20year:{year}")
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
                                isadmin=isadmin,
                                song_id=id)
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
            selected_genres = request.form.getlist("genres")
            if all(x is not None and x.strip() != "" for x in (song_name, song_year, song_artist)):
                cur.execute(
                    "INSERT INTO song (name, releaseyear, artist, approved) VALUES (?, ?, ?, ?)",
                    (song_name, song_year, song_artist, 0)
                )
                song_id = cur.lastrowid
                for genre_id in selected_genres:
                    cur.execute(
                        "INSERT INTO genresong (songid, genreid) VALUES (?, ?)",
                        (song_id, genre_id)
                    )
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
        genres = cur.execute("SELECT Genreid, name FROM Genre").fetchall()
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            conn.close()
            return redirect(url_for('banned'))
        title = "Add a song"
        conn.close()
        return render_template(
            "add_song.html",
            title=title,
            user_name=user_name,
            user_picture=user_picture,
            show_error_none=show_error_none,
            isadmin=isadmin,
            genres=genres
        )
    else:
        return render_template("login_needed.html", login_location=login_location)

@app.route("/songlist")
def song_list():
    user_name = None
    user_picture = None
    isadmin = False
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
        if admin and admin[0] == 1:
            isadmin = True  
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
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
    isadmin = False
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True  
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
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
    isadmin = False
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned')) 
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
    isadmin = False
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))  
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


@app.route("/admin")     
def admin():
    user_name = None
    user_picture = None
    isadmin = False
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True
            banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
            if banned and banned[0] == 1:
                redirect(url_for('banned'))
            users = cur.execute("SELECT * FROM Users").fetchall()
            unnaproved_songs = cur.execute("SELECT * from Song WHERE Approved = 0").fetchall()
            title = "New Post"
            conn.commit()
            conn.close()

            return render_template("admin.html",
                                title=title,
                                user_name=user_name,
                                user_picture=user_picture,
                                isadmin=isadmin,
                                users=users,
                                unnaproved_songs=unnaproved_songs)
        else:
            abort(403)
    else:
        return render_template("login_needed.html",login_location=login_location)

@app.route("/banned")   
def banned():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        userinfo = cur.execute("SELECT id,name,email FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        msg = Message(
            subject = f"Ban Appeal for {userinfo[1]}",
            recipients=["hitstermegawebsite@gmail.com"]
        )
        msg.body = f"{userinfo[2]} is requesting a ban appeal for"
        
        mail.send(msg)
        return render_template("banned.html",banned=banned) 
    
    else:
        return redirect(url_for('home'))

    
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
        INSERT INTO users (id, name, email, profile_pic, date_joined, Isadmin, Isbanned)
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

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('home'))


@app.route('/process-data', methods=['POST'])
def process_data():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor() 
    payload = request.json
    data = payload.get('data', {})
    cur.execute("DELETE FROM boxes")
    for box, song_ids in data.items():
        if song_ids:
            for song_id in song_ids:
                if song_id is not None:
                    cur.execute("INSERT INTO boxes (boxid, songid) VALUES (?, ?)", (box, song_id))                   
    conn.commit()
    conn.close()
    return jsonify({'result': 'success'})

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

@app.route('/unban', methods=['POST'])
def unban():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("UPDATE Users SET Isbanned = 0 WHERE id = ?", (user_id,))
        cur.execute("UPDATE Users SET Banreason = Null WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/ban', methods=['POST'])
def ban():
    user_id = request.form.get('user_id')
    ban_reason = request.form.get('ban_reason')  
    if user_id and ban_reason:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute(
            "UPDATE Users SET Isbanned = 1, BanReason = ? WHERE id = ?", 
            (ban_reason, user_id)
        ) 
        cur.execute("DELETE FROM ForumPost WHERE OwnerID = ?", (user_id,))

        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/promoteadmin', methods=['POST'])
def promoteadmin():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("UPDATE Users SET Isadmin = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/demoteadmin', methods=['POST'])
def demoteadmin():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("UPDATE Users SET Isadmin = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/approvesong', methods=['POST'])
def approvesong():
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("UPDATE Song SET Approved = 1 WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/denysong', methods=['POST'])
def denysong():
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM genresong WHERE songid = ?", (song_id,))
        cur.execute("DELETE FROM Song WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
        cover_folder = app.config.get('COVER_FOLDER')
        image_filename = f"{song_id}.jpg"
        image_path = os.path.join(cover_folder, image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    return redirect(request.referrer or url_for('index'))

@app.route('/deletepost', methods=['POST'])
def deletepost():
    post_id = request.form.get('post_id')  
    if post_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM ForumPost WHERE id = ?", (post_id,)) 
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)


   