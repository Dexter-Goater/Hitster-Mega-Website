from flask import Flask, render_template, abort,session,jsonify,request
import sqlite3
import random
import json
import spotipy
import webbrowser
username = 'wqgfeis2dlz27xoecb7h5oqfa'
clientID = 'f1d1f56639ec493ea1102ab8d340f871'
clientSecret = '4623201be31f464c83c89dd084da2527'
redirect_uri = 'https://example.com/'
oauth_object = spotipy.SpotifyOAuth(clientID, clientSecret, redirect_uri)
token_dict = oauth_object.get_access_token()
token = token_dict['access_token']
spotifyObject = spotipy.Spotify(auth=token)
user_name = spotifyObject.current_user()
app = Flask(__name__)
@app.route("/")

def home():
    conn = sqlite3.connect("Hitster.db")
    cur = conn.cursor()
    data = cur.execute("SELECT id from Song").fetchall()
    id = data[random.randint(0, len(data) - 1)][0]
    starting_box_song_id = data[random.randint(0, len(data) - 1)][0]
    cur.execute("UPDATE boxes SET songid = ? WHERE boxid = 'box5'",(starting_box_song_id,))
    res = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {id}").fetchall()
    name = res[0]
    artist = res[0][1]
    year = res[0][2]
    search_song = f"{name[0]}"
    results = spotifyObject.search(f"q=track:{name}%20artist:{artist}%20year:{year}")
    songs_dict = results['tracks']
    song_items = songs_dict['items']
    song = song_items[0]['uri']
    gamedata = cur.execute("SELECT id from Song").fetchall()
    gameid = gamedata[random.randint(0, len(data) - 1)][0]
    while gameid == id:
      gameid = gamedata[random.randint(0, len(data) - 1)][0]
    gameres = cur.execute(f"SELECT name,artist,releaseyear from Song WHERE id = {gameid}").fetchall()
    boxsong = cur.execute(f"SELECT boxes.boxid, song.* FROM boxes JOIN song ON boxes.songid = song.id").fetchall()
   


    title = "Home"
    conn.commit()
    conn.close()

    return render_template("home.html",title=title,song=song,search_song=search_song,artist=artist, year=year, gameres=gameres,boxsong=boxsong)




  
if __name__ == "__main__":
    app.run(debug=True)