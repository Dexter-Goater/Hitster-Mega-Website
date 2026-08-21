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
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)



class DataStore():
    boxdata = None


#Defines the home route
@app.route("/")
def home():
    user_name = None
    user_picture = None
    isadmin = False
    login_location = "Home"
    #Checks if the user is logged in with google
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #This query is on most pages in the website and it checks if users are banned so the appropriate measures can be taken
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
        #This query is on most pages in the website and it checks if users are admins so they can be given permissions
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True  
        #This query selects all the songs
        data = cur.execute("SELECT id from Song WHERE Approved = 1").fetchall()
        id = data[random.randint(0, len(data) - 1)][0]
        res = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {id}").fetchall()
        name = res[0]
        song_title = name[0]
        artist = res[0][1]
        year = res[0][2]
        search_song = f"{name[0]}"
        #This uses the spotify api to find the song on spotify
        results = spotifyObject.search(f"q=track:{song_title}%20artist:{artist}%20year:{year}")
        songs_dict = results['tracks']
        song_items = songs_dict['items']
        song = song_items[0]['uri']
        #this query gets all the information in all the boxes
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
    #redirects to user to the loginpage if they are not logged in
    else:
        return render_template("login_needed.html",login_location=login_location)
    
#Defines the addsong route
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
                #inserts the songs information into the database
                cur.execute(
                    "INSERT INTO song (name, releaseyear, artist, approved) VALUES (?, ?, ?, ?)",
                    (song_name, song_year, song_artist, 0)
                )
                song_id = cur.lastrowid
                for genre_id in selected_genres:
                    #inserts the songs genres into the genresong linking table
                    cur.execute(
                        "INSERT INTO genresong (songid, genreid) VALUES (?, ?)",
                        (song_id, genre_id)
                    )
                cover_file = request.files.get("scover")
                #checks that the image is a .jpg and then inserts it into the coverart folder with the id as the name
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
        #gets all the genres for the user to choose from
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

#defines the songlist route
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
        #gets all the songs to be displayed on the page
        songs = cur.execute("SELECT id,name,artist,releaseyear FROM song WHERE Approved = 1").fetchall()
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True  
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
        title = "Songs List"
        #gets all the songs and their genres
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
    
#defines the help route
@app.route("/help")
def help():
    user_name = None
    user_picture = None
    user_id = None
    isadmin = False
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    login_location = "Help Forums"    
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')
            user_id = user.get('sub')
        admin = cur.execute("SELECT Isadmin FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if admin and admin[0] == 1:
            isadmin = True  
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        if banned and banned[0] == 1:
            return redirect(url_for('banned'))
        #gets all the posts to be displayed on the page
        posts = cur.execute("SELECT PostID,OwnerID,Title,Resolved,PostDate,OwnerName,OwnerPFP FROM ForumPost").fetchall()
        title = "Help Forums"
        conn.commit()
        conn.close()

        return render_template("forum.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            user_id=user_id,
                            isadmin=isadmin,
                            posts=posts)
    else:
        return render_template("login_needed.html",login_location=login_location)  

#defines the individual post page
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
        #gets all the posts information where it matches the post from the page the user is on
        postinfo = cur.execute("SELECT PostID,OwnerID,Title,Content,Resolved,OwnerName,OwnerPFP FROM ForumPost WHERE PostID = ?",(page_ID,)).fetchone()
        #gets all the comments on the post the user is on
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

#defines the newpost route
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

#defines the admin route
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
            #gets all the information on all the users
            users = cur.execute("SELECT * FROM Users").fetchall()
            #gets all the songs that are yet to be approved
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
        #gives the user a forbidden error if they are not an admin
        else:
            abort(403)
    else:
        return render_template("login_needed.html",login_location=login_location)

#defines the banned route
@app.route("/banned")   
def banned():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        #gets all the information on the current user
        banned = cur.execute("SELECT Isbanned,Banreason FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
        #checks if the user is banned
        if banned[0] == 1:
            #this query finds out if the user has appealed their ban yet
            hasappealed = cur.execute("SELECT HasAppealed FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
            return render_template("banned.html",banned=banned,hasappealed=hasappealed)
        else:
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))

#redirects the user to the gooogle login
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
    #checks if the user exists
    existing = cur.execute("SELECT id FROM users WHERE id = ?", (user.get('sub'),)).fetchone()
    is_new_user = existing is None

    now = datetime.datetime.now().strftime("%d-%m-%y")
    #this query updates the users information in the database
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

#logs the user out
@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('home'))

#this route processes the games data
@app.route('/process-data', methods=['POST'])
def process_data():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor() 
    payload = request.json
    data = payload.get('data', {})
    #deletes the old information from the database
    cur.execute("DELETE FROM boxes")
    for box, song_ids in data.items():
        if song_ids:
            for song_id in song_ids:
                if song_id is not None:
                    #inserts the updated game information into the database
                    cur.execute("INSERT INTO boxes (boxid, songid) VALUES (?, ?)", (box, song_id))                   
    conn.commit()
    conn.close()
    return jsonify({'result': 'success'})

#this route clears all the games boxes
@app.route('/reset', methods=['POST'])
def reset():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    #clears all the boxes
    cur.execute("UPDATE boxes SET songid = NULL")
    conn.commit()
    conn.close()
    return jsonify({'result': 'success'})

#this route inserts the users new post into the database
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
    #inserts the users post information into the database
    cur.execute(
        "INSERT INTO ForumPost (OwnerID, title, content, PostDate, Ownername, OwnerPFP, Resolved) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        (user_id, post_title, post_content, post_time, user_name, user_picture, 0)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for("help"))

#this route runs when a user replys to a forum post
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
    #inserts the comment into the database
    cur.execute(
        "INSERT INTO ForumComment (OwnerID, content, ParentID, OwnerName, OwnerPFP) VALUES (?, ?, ?, ?, ?)",
        (user_id, comment_content, page_ID, user_name, user_picture)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("help",page_ID=page_ID))

#this route unbans a user in the database when an admin unbans them
@app.route('/unban', methods=['POST'])
def unban():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #this query unbans the user in the database
        cur.execute("UPDATE Users SET Isbanned = 0 WHERE id = ?", (user_id,))
        #this query clears the users banreason
        cur.execute("UPDATE Users SET Banreason = Null WHERE id = ?", (user_id,))
        #this query gets the unbanned users information
        userinfo = cur.execute("SELECT HasAppealed,email,Name FROM Users WHERE id = ?", (user_id,)).fetchone()
        #checks if the unbanned user has sent an appeal and sends the appropriate email
        if userinfo[0] == 0:
            msg = Message(
                subject = f"Ban status",
                recipients=[userinfo[1]]
            )
            msg.body = f"""Hello {userinfo[2]} if you are seeing this email it means that you have been unbanned from the Hitster Mega Website"""
            
            mail.send(msg)
        #checks if the unbanned user has sent an appeal and sends the appropriate email
        if userinfo[0] == 1:
            msg = Message(
                subject = f"Ban appeal",
                recipients=[userinfo[1]]
            )
            msg.body = f"""Hello {userinfo[2]} if you are seeing this email it means that your appeal has been accepted and you have been unbanned from the Hitster Mega Website"""
            
            mail.send(msg)
        #this query resets the users appeal so that if they are banned again they can appeal again
        cur.execute("UPDATE Users SET HasAppealed = 0 WHERE id = ?",(user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs when an admin bans a user
@app.route('/ban', methods=['POST'])
def ban():
    user_id = request.form.get('user_id')
    ban_reason = request.form.get('ban_reason')  
    if user_id and ban_reason:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #bans the user in the database
        cur.execute(
            "UPDATE Users SET Isbanned = 1, BanReason = ? WHERE id = ?", 
            (ban_reason, user_id)
        ) 
        #deletes all the banned users posts
        cur.execute("DELETE FROM ForumPost WHERE OwnerID = ?", (user_id,))
        #gets the appropriate information on the user
        userinfo = cur.execute("SELECT HasAppealed,email,Name FROM Users WHERE id = ?", (user_id,)).fetchone()
        #sends the user an email informing them of their ban
        msg = Message(
            subject = f"Ban",
            recipients=[userinfo[1]]
        )
        msg.body = f"""Hello {userinfo[2]} if you are seeing this email it means that you have been banned from the Hitster Mega Website for {ban_reason}"""

        mail.send(msg)

        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs when an admin promotes a user to an admin
@app.route('/promoteadmin', methods=['POST'])
def promoteadmin():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #makes the user an admin in the database
        cur.execute("UPDATE Users SET Isadmin = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs whenever an admin demotes an admin to a user
@app.route('/demoteadmin', methods=['POST'])
def demoteadmin():
    user_id = request.form.get('user_id')
    if user_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #makes the admin a user in the database
        cur.execute("UPDATE Users SET Isadmin = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs whenever an admin approves a users song
@app.route('/approvesong', methods=['POST'])
def approvesong():
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #makes the song approved in the database so that it can show up on the website
        cur.execute("UPDATE Song SET Approved = 1 WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs whenever an admin denys a users song request
@app.route('/denysong', methods=['POST'])
def denysong():
    song_id = request.form.get('song_id')
    if song_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #these querys deletes the song from the genre and song table
        cur.execute("DELETE FROM genresong WHERE songid = ?", (song_id,))
        cur.execute("DELETE FROM Song WHERE id = ?", (song_id,))
        conn.commit()
        conn.close()
        cover_folder = app.config.get('COVER_FOLDER')
        image_filename = f"{song_id}.jpg"
        image_path = os.path.join(cover_folder, image_filename)
        #deletes the image from the coverart folder
        if os.path.exists(image_path):
            os.remove(image_path)
    return redirect(request.referrer or url_for('index'))

#this route runs when a admin or the owner of a post deletes it
@app.route('/deletepost', methods=['POST'])
def deletepost():
    post_id = request.form.get('post_id')  
    if post_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #deletes the post from the database
        cur.execute("DELETE FROM ForumPost WHERE POSTID = ?", (post_id,)) 
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs when a admin or the owner of a post resolves it
@app.route('/resolvepost', methods=['POST'])
def resolvepost():
    post_id = request.form.get('post_id')  
    if post_id:
        conn = sqlite3.connect("Hitster.db")
        cur = conn.cursor()
        #resolves the post in the database
        cur.execute("UPDATE ForumPost SET Resolved = 1 WHERE POSTID = ?", (post_id,)) 
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for('index'))

#this route runs when a user requests a ban appeal
@app.route('/banappeal', methods=['post'])
def banappeal():
    appeal_reason = request.form['AppealReason']
    content = request.form['content']
    user = session['google_token'].get('userinfo')
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    #gets all the users information
    userinfo = cur.execute("SELECT id,name,email,Isbanned,Banreason,HasAppealed  FROM Users WHERE id = ?", (user.get('sub'),)).fetchone()
    #sends an email with the users appeal to the admin email
    if userinfo[5] == 0:
        msg = Message(
            subject = f"{userinfo[2]} is requesting a ban appeal for {userinfo[4]}",
            recipients=["hitstermegawebsite@gmail.com"]
        )
        msg.body = f"""The reason for the appeal is "{appeal_reason}". They provided the following information "{content}" """
        
        mail.send(msg)
        cur.execute("UPDATE Users SET HasAppealed = ? WHERE id = ?", (1, userinfo[0]))
    conn.commit()
    conn.close()
    
    return redirect(url_for("banned")) 


# handles 500 errors
@app.errorhandler(500)
def ServerError(servererror):
    return render_template('error.html',
                           title=servererror,
                           message="""The website's server encountered
                           an unexpected condition that prevented it
                           from fulfilling your request""",
                           code=500)


# handles 404 errors
@app.errorhandler(404)
def PageNotFound(notfound):
    return render_template("error.html",
                           title=notfound, message="""We can't
                            seem to find the page
                           you were looking for""",
                           code=404)

# handles 403 errors
@app.errorhandler(403)
def PageNotFound(notfound):
    return render_template("error.html",
                           title=notfound, message="""You dont have permisson to acsess this page""",
                           code=403)

if __name__ == "__main__":
    app.run(debug=True)


   