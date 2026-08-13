import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd

# Set up page configuration
st.set_page_config(
    page_title="Spotify Music Analytics Dashboard",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("🎵 Spotify Music Analytics Dashboard")
st.markdown("""
This app allows you to explore music data using the official Spotify Web API. 
You can switch between exploring public Spotify data or connecting your personal account to analyze your listening habits.
""")

# Sidebar instructions and credentials configuration
st.sidebar.header("Step 1: Setup Credentials")
st.sidebar.markdown("""
To use this application, you need to set up a Spotify Developer Application:
1. Go to the [Spotify Developer Dashboard](https://spotify.com).
2. Create an app to obtain a **Client ID** and **Client Secret**.
3. Edit settings and set the **Redirect URI** to `http://localhost:8501/` (default Streamlit port).
""")

# Input widgets for API keys
client_id = st.sidebar.text_input("Spotify Client ID", type="password", help="Enter your Spotify API Client ID")
client_secret = st.sidebar.text_input("Spotify Client Secret", type="password", help="Enter your Spotify API Client Secret")
redirect_uri = st.sidebar.text_input("Redirect URI", value="http://localhost:8501/", help="Must exactly match your Spotify developer settings")

# Dropdown to choose application mode
st.sidebar.header("Step 2: Choose Mode")
app_mode = st.sidebar.selectbox(
    "Select Dashboard Mode",
    ["Public Music Explorer", "Personal Account Analytics"]
)

def get_public_spotify(cid, secret):
    """Authenticates with client credentials flow for public data access."""
    try:
        auth_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

def get_personal_spotify(cid, secret, ruri):
    """Authenticates with user authorization flow for private user data."""
    try:
        # Define the permissions (scopes) our application requires
        scope = "user-top-read user-read-recently-played user-library-read"
        sp_oauth = SpotifyOAuth(
            client_id=cid,
            client_secret=secret,
            redirect_uri=ruri,
            scope=scope,
            cache_handler=spotipy.cache_handler.StreamlitCacheHandler()
        )
        
        # Check if auth token exists or guide user to sign in
        token_info = sp_oauth.validate_token(sp_oauth.cache_handler.get_cached_token())
        
        if not token_info:
            # Generate login button if not authenticated
            auth_url = sp_oauth.get_authorize_url()
            st.info("Please log in to your Spotify account to view personal data.")
            st.markdown(f'<a href="{auth_url}" target="_blank" style="display: inline-block; padding: 0.5em 1em; background-color: #1DB954; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">Log in with Spotify</a>', unsafe_allow_html=True)
            
            # Streamlit handles redirect query params automatically
            code = st.query_params.get("code")
            if code:
                token_info = sp_oauth.get_access_token(code)
                if token_info:
                    return spotipy.Spotify(auth=token_info['access_token'])
            return None
        else:
            return spotipy.Spotify(auth=token_info['access_token'])
            
    except Exception as e:
        st.error(f"OAuth Authentication failed: {e}")
        return None

# Core Application Logic
if not client_id or not client_secret:
    st.warning("⚠️ Please provide your Spotify Client ID and Client Secret in the sidebar to load the application features.")
else:
    # ---------------- MODE 1: PUBLIC MUSIC EXPLORER ----------------
    if app_mode == "Public Music Explorer":
        sp = get_public_spotify(client_id, client_secret)
        
        if sp:
            st.header("🔍 Public Music Explorer")
            search_query = st.text_input("Search for an Artist or Song:", value="Billie Eilish")
            search_type = st.radio("Search Category:", ["Artist", "Track"], horizontal=True)
            
            if search_query:
                if search_type == "Artist":
                    results = sp.search(q=search_query, type='artist', limit=5)
                    artists = results['artists']['items']
                    
                    if artists:
                        for artist in artists:
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if artist['images']:
                                    st.image(artist['images'][0]['url'], width=150)
                            with col2:
                                st.subheader(artist['name'])
                                st.write(f"**Genres:** {', '.join(artist['genres'])}")
                                st.write(f"**Popularity:** {artist['popularity']}/100")
                                st.write(f"**Followers:** {artist['followers']['total']:,}")
                            st.markdown("---")
                    else:
                        st.info("No artists found with that name.")
                        
                elif search_type == "Track":
                    results = sp.search(q=search_query, type='track', limit=10)
                    tracks = results['tracks']['items']
                    
                    if tracks:
                        track_data = []
                        for track in tracks:
                            track_data.append({
                                "Song Name": track['name'],
                                "Artist": track['artists'][0]['name'],
                                "Album": track['album']['name'],
                                "Popularity": track['popularity'],
                                "Duration (min)": round(track['duration_ms'] / 60000, 2),
                                "Track ID": track['id']
                            })
                        
                        df = pd.DataFrame(track_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Analyze audio features for the first track selected
                        st.subheader("📊 Audio Feature Analysis")
                        selected_track = st.selectbox("Select a song from your search to analyze features:", df["Song Name"].unique())
                        selected_id = df[df["Song Name"] == selected_track]["Track ID"].values[0]
                        
                        features = sp.audio_features([selected_id])[0]
                        
                        if features:
                            # Isolate numeric metrics suited for chart visualization
                            feature_metrics = {
                                "Danceability": features["danceability"],
                                "Energy": features["energy"],
                                "Speechiness": features["speechiness"],
                                "Acousticness": features["acousticness"],
                                "Instrumentalness": features["instrumentalness"],
                                "Liveness": features["liveness"],
                                "Valence (Happiness)": features["valence"]
                            }
                            
                            feature_df = pd.DataFrame(list(feature_metrics.items()), columns=["Audio Feature", "Value"])
                            
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.bar_chart(feature_df.set_index("Audio Feature"))
                            with col2:
                                st.write(f"**Tempo:** {features['tempo']} BPM")
                                st.write(f"**Key:** {features['key']}")
                                st.write(f"**Loudness:** {features['loudness']} dB")
                                st.write(f"**Time Signature:** {features['time_signature']}/4")
                        else:
                            st.info("Audio features are not available for this track.")
                    else:
                        st.info("No tracks found with that name.")

    # ---------------- MODE 2: PERSONAL ACCOUNT ANALYTICS ----------------
    elif app_mode == "Personal Account Analytics":
        sp = get_personal_spotify(client_id, client_secret, redirect_uri)
        
        if sp:
            st.header("📈 Personal Account Insights")
            
            try:
                user_profile = sp.current_user()
                st.write(f"Welcome to your dashboard, **{user_profile['display_name']}**! 🎉")
                
                tab1, tab2, tab3 = st.tabs(["Top Tracks", "Top Artists", "Recently Played"])
                
                with tab1:
                    time_range = st.selectbox(
                        "Select Timeframe (Tracks):",
                        ["short_term", "medium_term", "long_term"],
                        format_func=lambda x: "Past 4 Weeks" if x == "short_term" else "Past 6 Months" if x == "medium_term" else "All Time"
                    )
                    
                    top_tracks = sp.current_user_top_tracks(limit=15, time_range=time_range)
                    if top_tracks and top_tracks['items']:
                        for i, item in enumerate(top_tracks['items']):
                            st.write(f"{i+1}. **{item['name']}** by *{item['artists'][0]['name']}* (Popularity: {item['popularity']})")
                    else:
                        st.info("Not enough data found for this timeframe.")
                        
                with tab2:
                    time_range_art = st.selectbox(
                        "Select Timeframe (Artists):",
                        ["short_term", "medium_term", "long_term"],
                        format_func=lambda x: "Past 4 Weeks" if x == "short_term" else "Past 6 Months" if x == "medium_term" else "All Time",
                        key="artists_timeframe"
                    )
                    
                    top_artists = sp.current_user_top_artists(limit=15, time_range=time_range_art)
                    if top_artists and top_artists['items']:
                        for i, item in enumerate(top_artists['items']):
                            st.write(f"{i+1}. **{item['name']}** - Genres: {', '.join(item['genres'][:3])}")
                    else:
                        st.info("Not enough data found for this timeframe.")
                        
                with tab3:
                    recent_tracks = sp.current_user_recently_played(limit=15)
                    if recent_tracks and recent_tracks['items']:
                        for i, item in enumerate(recent_tracks['items']):
                            track = item['track']
                            st.write(f"{i+1}. **{track['name']}** by *{track['artists'][0]['name']}*")
                    else:
                        st.info("No recently played tracks found.")
                        
            except Exception as e:
                st.error(f"Could not retrieve personal user insights: {e}")