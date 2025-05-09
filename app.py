import streamlit as st
import pickle
import requests
import sqlite3
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "c7ec19ffdd3279641fb606d19ceb9bb1")  # Fallback for local testing

# Initialize database schema
def init_db():
    try:
        conn = sqlite3.connect('movie_app.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS ratings 
                     (movie TEXT, rating INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS suggestions 
                     (movie TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS favorites 
                     (movie TEXT)''')
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()

# DB Functions with error handling
def add_rating(movie, rating):
    try:
        conn = sqlite3.connect('movie_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO ratings VALUES (?, ?)", (movie, rating))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to add rating: {e}")
    finally:
        conn.close()

def add_suggestion(movie):
    try:
        conn = sqlite3.connect('movie_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO suggestions VALUES (?)", (movie,))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to add suggestion: {e}")
    finally:
        conn.close()

def add_favorite(movie):
    try:
        conn = sqlite3.connect('movie_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO favorites VALUES (?)", (movie,))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to add favorite: {e}")
    finally:
        conn.close()

def get_favorites():
    try:
        conn = sqlite3.connect('movie_app.db')
        c = conn.cursor()
        c.execute("SELECT movie FROM favorites")
        favorites = [row[0] for row in c.fetchall()]
        return favorites
    except sqlite3.Error as e:
        st.error(f"Failed to fetch favorites: {e}")
        return []
    finally:
        conn.close()

# Cache TMDB API calls
@lru_cache(maxsize=100)
def fetch_movie_details(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        poster_path = data.get('poster_path')
        genre_ids = [genre['name'] for genre in data.get('genres', [])]
        rating = data.get('vote_average', 'N/A')
        release_date = data.get('release_date', 'N/A')
        
        poster_url = f"https://image.tmdb.org/t/p/w500/{poster_path}" if poster_path else ""
        
        return {
            'poster_url': poster_url,
            'genres': genre_ids,
            'rating': rating,
            'release_date': release_date
        }
    except requests.RequestException as e:
        st.error(f"Failed to fetch movie details: {e}")
        return {'poster_url': '', 'genres': [], 'rating': 'N/A', 'release_date': 'N/A'}

# Fetch all genres from TMDB
def fetch_genres():
    try:
        url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
        response = requests.get(url)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return [genre['name'] for genre in genres]
    except requests.RequestException as e:
        st.error(f"Failed to fetch genres: {e}")
        return []

# Load models and movie list
try:
    movies = pickle.load(open("movies_list.pkl", 'rb'))
    similarity = pickle.load(open("similarity.pkl", 'rb'))
    movies_list = movies['title'].values
except FileNotFoundError as e:
    st.error(f"Model files not found: {e}")
    movies_list = []

# Custom UI Styling (unchanged)
st.markdown("""
<style>
    body {
        background: #1a1a1a;
        color: #e0e0e0;
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 20px;
    }
    h1 {
        text-align: center;
        color: #e0e0e0;
        font-size: 36px;
        margin-bottom: 20px;
    }
    p {
        text-align: center;
        color: #b0b0b0;
        font-size: 16px;
        margin-bottom: 30px;
        line-height: 1.6;
    }
    .stButton > button {
        background: #1a1a1a;
        color: #d4af37;
        border: 1px solid #d4af37;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    .stButton > button:hover {
        background: #d4af37;
        color: #1a1a1a;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
    }
    .stButton > button:active {
        transform: translateY(1px);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    }
    .stSelectbox {
        background-color: #252525;
        color: #e0e0e0;
        border-radius: 4px;
        padding: 8px;
        border: none;
        transition: border-color 0.3s ease;
    }
    .stSelectbox > div {
        background-color: #252525;
        border-radius: 4px;
    }
    .stSelectbox:hover {
        border: 1px solid #aca58c;
    }
    div[data-testid="stSlider"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stSlider"] > div {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    div[data-testid="stSlider"]::before,
    div[data-testid="stSlider"]::after {
        display: none !important;
    }
    div[data-testid="stHorizontalBlock"] > div:has(> div[data-testid="stSlider"]) {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    div[data-testid="stSlider"] > div > div > div > div > div {
        color: #d4af37 !important;
        font-weight: 500;
        font-size: 14px;
    }
    .movie-details {
        color: #ba4747;
        font-size: 14px;
        text-align: center;
        margin-top: 10px;
        line-height: 1.8;
    }
    .genre {
        font-style: italic;
        color: #000000;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .rating, .release-date {
        color: #000000;
        font-weight: bold;
    }
    .movie-title {
        font-weight: 700;
        color: #ffffff;
        font-size: 18px;
    }
    .center-align {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80px;
    }
    .button-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
        padding: 20px;
        background: #252525;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        max-width: 500px;
        margin: 0 auto;
    }
    @media (max-width: 768px) {
        h1 {
            font-size: 28px;
        }
        p {
            font-size: 14px;
        }
        .stButton > button {
            padding: 4px 8px;
            font-size: 10px;
        }
        .button-container {
            padding: 15px;
            max-width: 100%;
        }
        div[data-testid="stSlider"] > div > div > div > div > div {
            font-size: 12px;
        }
    }
    @media (max-width: 480px) {
        h1 {
            font-size: 24px;
        }
        p {
            font-size: 12px;
        }
        .stButton > button {
            padding: 3px 6px;
            font-size: 9px;
        }
        .button-container {
            padding: 10px;
            gap: 15px;
        }
        div[data-testid="stSlider"] > div > div > div > div > div {
            font-size: 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()

# Title
st.markdown("<h1>🎥 Movie Recommender System</h1>", unsafe_allow_html=True)
st.markdown("<p>Discover movies similar to your favorite picks!</p>", unsafe_allow_html=True)

# Movie Selection and Genre Filter
col1, col2 = st.columns([3, 1])
with col1:
    selectvalue = st.selectbox("Select movie from dropdown", movies_list)
with col2:
    genres = fetch_genres()
    selected_genre = st.selectbox("Filter by genre", ["All"] + genres)

# Recommendation logic with genre filter
def recommend(movie, genre_filter="All"):
    try:
        index = movies[movies['title'] == movie].index[0]
        distance = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
        
        recommend_movie = []
        recommend_details = []
        
        for i in distance[1:]:
            movie_id = movies.iloc[i[0]].id
            movie_details = fetch_movie_details(movie_id)
            # Apply genre filter
            if genre_filter == "All" or genre_filter in movie_details['genres']:
                recommend_movie.append(movies.iloc[i[0]].title)
                recommend_details.append(movie_details)
            if len(recommend_movie) >= 5:
                break
        
        return recommend_movie, recommend_details
    except IndexError:
        st.error("Movie not found in dataset.")
        return [], []

# Show recommendations
if selectvalue:
    st.markdown("---")
    st.subheader("🎬 Recommendations")
    movie_name, movie_details = recommend(selectvalue, selected_genre)
    
    if movie_name:
        cols = st.columns(5)
        for i in range(min(5, len(movie_name))):
            with cols[i]:
                st.image(movie_details[i]['poster_url'], use_container_width=True)
                st.markdown(f"<p class='movie-title'>{movie_name[i]}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='genre'>{', '.join(movie_details[i]['genres'])}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='rating'>Rating: {movie_details[i]['rating']}/10</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='release-date'>Release Date: {movie_details[i]['release_date']}</p>", unsafe_allow_html=True)
    else:
        st.warning("No recommendations match the selected genre.")

# Rating and actions
with st.container():
    st.markdown("<div class='button-container'>", unsafe_allow_html=True)
    rating = st.slider("Rate this movie", 0, 10, 5)
    button_cols = st.columns(2)
    with button_cols[0]:
        if st.button("Submit Rating"):
            add_rating(selectvalue, rating)
            st.success(f"You rated {selectvalue}: {rating}/10")
    with button_cols[1]:
        if st.button("Add to Favourites"):
            add_favorite(selectvalue)
            st.success(f"{selectvalue} added to favorites!")
    st.markdown("</div>", unsafe_allow_html=True)

# Show favorites
favorites = get_favorites()
if favorites:
    st.subheader("🎯 Your Favourite Movies")
    for fav in favorites:
        st.markdown(f"• {fav}")

# Movie suggestion with validation
suggestion = st.text_input("Suggest a movie")
if st.button("Submit Suggestion"):
    if suggestion and suggestion.strip():
        add_suggestion(suggestion.strip())
        st.success(f"Thanks for suggesting: {suggestion.strip()}")
    else:
        st.warning("Please enter a valid movie name.")