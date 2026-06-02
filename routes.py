from flask import Flask, render_template, abort,session,jsonify,request,redirect,url_for
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import sqlite3
import os
import random
import json
import spotipy
import webbrowser
import requests
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


class DataStore():
    boxdata = None
@app.route("/")
def home():
    user_name = None
    user_picture = None

    if 'google_token' in session:
        user = session['google_token'].get('userinfo')
        if user:
            user_name = user.get('name')
            user_picture = user.get('picture')

    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
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
                           user_picture=user_picture)

@app.route("/add_song", methods=["GET","POST"])
def add_song():
    user_name = None
    user_picture = None
    show_error_none = False
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
                cur.execute(f"INSERT INTO song (id,name,releaseyear,artist,approved) VALUES (?,?,?,?,?)",(None,song_name,song_year,song_artist,0))
                show_error_none = False
            else:
                show_error_none = True


        title = "Add a song"
        conn.commit()
        conn.close()

        return render_template("add_song.html",
                            title=title,
                            user_name=user_name,
                            user_picture=user_picture,
                            show_error_none=show_error_none)
    else:
        return render_template(login_location=login_location)

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
    
    # Save user to database
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (id, name, email, profile_pic) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            profile_pic = excluded.profile_pic
    """, (
        user.get('sub'),      # Google user ID
        user.get('name'),
        user.get('email'),
        user.get('picture')
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



if __name__ == "__main__":
    app.run(debug=True)