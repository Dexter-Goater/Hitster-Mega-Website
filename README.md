<h1>Hitster mega website by Dexter Goater</h1>

<h2>How to run</h2>
<h3>Install Requirements.txt</h3>
1. Open Terminal or Command prompt<br>
2. Type the following command and press Enter:cd path/to/your/project_folder<br>
3. Type the following command and press Enter:pip install -r requirements.txt<br>
<br>
<h3>Create a .env file in the same folder as the routes.py</h3>
This is where all the api keys will be<br>
This is a list of everything you will need in your .env file <br>
SPOTIFY_CLIENT_ID={YourSpotifyDeveloperClientID} <br>
SPOTIFY_CLIENT_SECRET={YourSpotifyDeveloperClientSecret} <br>
GOOGLE_CLIENT_ID = {YourGoogleOauthClientID} <br>
GOOGLE_CLIENT_SECRET = {YourGoogleOauthClientSecret} <br>
APP_SECRET_KEY = {a 64 character long hexadecimal string} <br>
MAIL_USERNAME={your email adress} <br>
MAIL_PASSWORD={google app password} <br>

<h3>How to make a Spotify Client id and secret</h3>
Go to the Spotify Developer Dashboard (https://developer.spotify.com/), log in with your account, click Create app, fill in a app name and description,set the redirecturi to (https://example.com/), Select the Web Playback SDK, and click Save. Your Client ID and Client Secret will then be visible on your new app's dashboard page.

<h3>How to make a Google client id and secret</h3>
Go to console.cloud.google.com and create a new project,In the left sidebar<br>
Go to APIs & Services > OAuth consent screen,Input an app name and support email,Select External,Insert A contact email then continue<br>
Go to APIs & Services > Credentials, click 'Create Credentials' > 'OAuth client ID'. Choose the application type 'Web application'<br>
Set the Authorised JavaScript origins to (https://127.0.0.1:5000) and set the Authorised redirect URIs to (http://127.0.0.1:5000/login/authorized)<br>
After creating, Google shows you the Client ID and Client Secret. Copy them and put them in the .env file
