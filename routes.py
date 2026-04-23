from flask import Flask, render_template, abort,session,jsonify,request
from dotenv import load_dotenv
import sqlite3
import os
import random
import json
import spotipy
import webbrowser
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


class DataStore():
    boxdata = None

@app.route("/")
def home():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    data = cur.execute("SELECT id from Song").fetchall()
    id = data[random.randint(0, len(data) - 1)][0]
    print(id)
    res = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {id}").fetchall()
    print(res)
    name = res[0]
    artist = res[0][1]
    year = res[0][2]
    search_song = f"{name[0]}"
    results = spotifyObject.search(f"q=track:{name}%20artist:{artist}%20year:{year}")
    songs_dict = results['tracks']
    song_items = songs_dict['items']
    song = song_items[0]['uri']
    boxsong = cur.execute(f"SELECT boxes.boxid, song.* FROM boxes JOIN song ON boxes.songid = song.id").fetchall()
    songids = DataStore.boxdata
    
    

    title = "Home"
    conn.commit()
    conn.close()
    return render_template("home.html",title=title,song=song,name=name,search_song=search_song,year=year,artist=artist,boxsong=boxsong)


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