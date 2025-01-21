import streamlit as st
from googleapiclient.discovery import build
import re
import emoji
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import hashlib

# Set up SQLite database
engine = create_engine('sqlite:///sentiment_analysis.db')
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    phone = Column(String)
    age = Column(Integer)
    gender = Column(String)
    password = Column(String)

class SentimentResult(Base):
    __tablename__ = 'sentiment_results'
    id = Column(Integer, primary_key=True)
    video_id = Column(String)
    positive = Column(Float)
    neutral = Column(Float)
    negative = Column(Float)
    compound = Column(Float)
    recommendation = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

# Function to clean comments
def clean_comment(comment):
    comment = emoji.replace_emoji(comment, replace='')
    comment = re.sub(r'http\S+', '', comment)
    comment = re.sub(r'[^A-Za-z0-9\s]+', '', comment)
    return comment

# Function to get YouTube comments
def get_youtube_comments(video_id, api_key, max_results=100):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText"
        )
        response = request.execute()
        comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in response['items']]
        return comments
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return []

# Function to get video description
def get_video_description(video_id, api_key):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        response = request.execute()
        description = response['items'][0]['snippet']['description']
        return description
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return "No description available."

# Extract video ID from URL
def extract_video_id(url):
    video_id_match = re.search(r'(?:youtu\.be/|youtube\.com(?:/embed/|/v/|/watch\?v=|/watch\?.+&v=))([^&]{11})', url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        return None

# Function to provide recommendations
def provide_recommendation(positive, negative, total, age):
    if total == 0:
        return "Not enough comments to provide a recommendation."
    
    positive_ratio = positive / total
    negative_ratio = negative / total

    if age < 13:  # Children
        if positive_ratio > 0.8:
            return "Highly recommended for children."
        elif positive_ratio > 0.5:
            return "Recommended for children (12-18)."
        elif positive_ratio > 0.3:
            return "Recommended for adults."
        elif negative_ratio > 0.5:
            return "Not recommended for children."
        else:
            return "Mixed reviews. Suitable for mature audiences."
    elif 13 <= age <= 18:  # Teens
        if positive_ratio > 0.7:
            return "Highly recommended for teens."
        elif positive_ratio > 0.5:
            return "Recommended for most teens."
        elif negative_ratio > 0.5:
            return "Not recommended for teens."
        else:
            return "Mixed reviews. Suitable for mature audiences."
    elif 19 <= age <= 64:  # Adults
        if positive_ratio > 0.7:
            return "Highly recommended for adults."
        elif positive_ratio > 0.5:
            return "Recommended for most adults."
        elif negative_ratio > 0.5:
            return "Not recommended for adults."
        else:
            return "Mixed reviews. Suitable for mature audiences."
    else:  # Aged people
        if positive_ratio > 0.8:
            return "Highly recommended for aged people."
        elif positive_ratio > 0.5:
            return "Recommended for aged people."
        elif negative_ratio > 0.5:
            return "Not recommended for aged people."
        else:
            return "Mixed reviews. Suitable for mature audiences."

# Home page
def home(user):
    st.markdown("""
    <style>
    body {
        background-image: url('https://www.example.com/your-image.jpg');
        background-size: cover;
    }
    .title {
        font-size: 36px;
        color: BLACK;
        text-align: center;
    }
    .subheader {
        font-size: 28px;
        color: #4CAF50;
        text-align: center;
    }
    .important {
        font-size: 20px;
        color: red;
    }
    .input-area {
        background: rgba(255, 255, 255, 0.8);
        padding: 3px;
        border-radius: 10px;
        margin: 0px;
    }
    .result-area {
        background: rgba(255, 255, 255, 0.8);
        padding: 20px;
        border-radius: 10px;
        margin: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="title">YouTube Comments Sentiment Analysis with Recommendations</h1>', unsafe_allow_html=True)

    # Input field for YouTube video URL
    with st.container():
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        video_url = st.text_input("Enter the YouTube video URL")
        st.markdown('</div>', unsafe_allow_html=True)

    # Input field for child age
    child_age = user.age

    # Fixed YouTube API key
    api_key = 'AIzaSyBNo84A-ezvwTS01rT-MReUwSrr8Ky91zY'

    if st.button("Analyze"):
        if video_url:
            video_id = extract_video_id(video_url)
            if video_id:
                # Show loading spinner while fetching data
                with st.spinner('Fetching data...'):
                    # Get comments
                    comments = get_youtube_comments(video_id, api_key)
                    # Get video description
                    description = get_video_description(video_id, api_key)
                    
                    if comments:
                        # Clean comments
                        cleaned_comments = [clean_comment(comment) for comment in comments]
                        
                        # Sentiment analysis
                        analyzer = SentimentIntensityAnalyzer()
                        sentiments = [analyzer.polarity_scores(comment) for comment in cleaned_comments]
                        
                        # Aggregate sentiment scores
                        positive = sum([s['pos'] for s in sentiments])
                        neutral = sum([s['neu'] for s in sentiments])
                        negative = sum([s['neg'] for s in sentiments])
                        compound = sum([s['compound'] for s in sentiments])
                        
                        # Provide recommendation
                        total_comments = len(comments)
                        recommendation = provide_recommendation(positive, negative, total_comments, child_age)
                        
                        # Display results
                        with st.container():
                            st.markdown('<div class="result-area">', unsafe_allow_html=True)
                            st.markdown('<h2 class="subheader">Video Description</h2>', unsafe_allow_html=True)
                            st.write(description)
                            
                            st.markdown('<h2 class="subheader">Sentiment Analysis</h2>', unsafe_allow_html=True)
                            st.write(f"Positive sentiment: {positive}")
                            st.write(f"Neutral sentiment: {neutral}")
                            st.write(f"Negative sentiment: {negative}")
                            st.write(f"Compound sentiment: {compound}")
                            st.markdown('<h2 class="subheader">Recommendation</h2>', unsafe_allow_html=True)
                            st.write(recommendation)
                            st.markdown('</div>', unsafe_allow_html=True)

                        # Sentiment distribution
                        sentiment_distribution = {
                            'Sentiment': ['Positive', 'Neutral', 'Negative'],
                            'Count': [positive, neutral, negative]
                        }
                        df_sentiment = pd.DataFrame(sentiment_distribution)

                        # Plotly bar chart
                        fig_bar = px.bar(df_sentiment, x='Sentiment', y='Count', title="Sentiment Distribution", color='Sentiment', height=400)
                        st.plotly_chart(fig_bar)

                        # Create word cloud
                        all_comments = ' '.join(cleaned_comments)
                        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_comments)
                        
                        # Display word cloud
                        plt.figure(figsize=(10, 6))
                        plt.imshow(wordcloud, interpolation='bilinear')
                        plt.axis('off')
                        st.pyplot(plt)

                        # Save results to the database
                        sentiment_result = SentimentResult(
                            video_id=video_id,
                            positive=positive,
                            neutral=neutral,
                            negative=negative,
                            compound=compound,
                            recommendation=recommendation
                        )
                        session.add(sentiment_result)
                        session.commit()

                        # Filtering comments
                        st.markdown('<h2 class="subheader">Comments</h2>', unsafe_allow_html=True)
                        sentiment_filter = st.selectbox("Filter comments by sentiment", ["All", "Positive", "Neutral", "Negative"])
                        
                        if sentiment_filter == "All":
                            filtered_comments = comments
                        else:
                            sentiment_mapping = {"Positive": "pos", "Neutral": "neu", "Negative": "neg"}
                            filtered_comments = [comment for comment, sentiment in zip(comments, sentiments) if sentiment[sentiment_mapping[sentiment_filter]] > 0.5]
                        
                        for comment in filtered_comments:
                            st.write(comment)
                    else:
                        st.write("No comments found for the given video URL.")
            else:
                st.write("Invalid YouTube video URL.")

# Login page
def login():
    st.markdown("""
    <style>
    .title {
        font-size: 40px;
        color: black;
        text-align: center;
    }
    .subheader {
        font-size: 28px;
        color: #4CAF50;
        text-align: center;
    }
    .important {
        font-size: 20px;
        color: red;
    }
    .input-area {
        background: rgba(255, 255, 255, 0.8);
        padding: 3px;
        border-radius: 10px;
        margin: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="title">Login Page</h1>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = session.query(User).filter_by(email=email).first()
            if user and verify_password(user.password, password):
                st.session_state["user"] = user
                st.success("Login successful")
            else:
                st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)

# Register page
def register():
    st.markdown("""
    <style>
    .title {
        font-size: 40px;
        color: black;
        text-align: center;
    }
    .subheader {
        font-size: 28px;
        color: #4CAF50;
        text-align: center;
    }
    .important {
        font-size: 20px;
        color: red;
    }
    .input-area {
        background: rgba(255, 255, 255, 0.8);
        padding: 3px;
        border-radius: 10px;
        margin: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="title">Register Page</h1>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        age = st.number_input("Age", min_value=5, max_value=100, step=1)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            if not session.query(User).filter_by(email=email).first():
                new_user = User(
                    name=name,
                    email=email,
                    phone=phone,
                    age=age,
                    gender=gender,
                    password=hash_password(password)
                )
                session.add(new_user)
                session.commit()
                st.success("Registration successful")
            else:
                st.error("Email already registered")
        st.markdown('</div>', unsafe_allow_html=True)

# Main function to control page navigation
def main():
    st.sidebar.title("Comment Analyzer")
    if "user" not in st.session_state:
        selection = st.sidebar.radio("Go to", ["Login", "Register"])
        if selection == "Login":
            login()
        elif selection == "Register":
            register()
    else:
        user = st.session_state["user"]
        st.sidebar.write(f"Logged in as {user.name}")
        if st.sidebar.button("Logout"):
            del st.session_state["user"]
            st.experimental_rerun()
        home(user)

import streamlit as st
import streamlit as st
import streamlit as st
from IPython.display import YouTubeVideo

# Function to fetch top YouTube videos
def fetch_top_videos(api_key):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            maxResults=10  # Change this value to fetch more or fewer videos
        )
        response = request.execute()
        video_ids = [item['id'] for item in response['items']]
        return video_ids
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return []

# Main function to control page navigation
def main():
    st.sidebar.title("Comment Analyzer")
    if "user" not in st.session_state:
        selection = st.sidebar.radio("Go to", ["Login", "Register"])
        if selection == "Login":
            login()
        elif selection == "Register":
            register()
    else:
        user = st.session_state["user"]
        st.sidebar.write(f"Logged in as {user.name}")
        if st.sidebar.button("Logout"):
            del st.session_state["user"]
            st.experimental_rerun()
        home(user)

        api_key = 'AIzaSyBNo84A-ezvwTS01rT-MReUwSrr8Ky91zY'  # Your YouTube API key
        top_video_ids = fetch_top_videos(api_key)
        if top_video_ids:
            st.write("Top 10 YouTube Videos:")
            for video_id in top_video_ids:
                st.video(f"https://www.youtube.com/watch?v={video_id}")
        else:
            st.write("Failed to fetch top videos.")


    import re
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def extract_channel_id(url):
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/]+/)?(?:user|channel|c)/|youtu\.be/)([a-zA-Z0-9_-]{24})'
    match = re.match(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

def fetch_videos(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=10
    )
    response = request.execute()
    video_ids = [item['id']['videoId'] for item in response['items']]
    return video_ids

def fetch_comments(api_key, video_ids):
    comments = []
    analyzer = SentimentIntensityAnalyzer()
    youtube = build('youtube', 'v3', developerKey=api_key)
    for video_id in video_ids:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
    return comments

def analyze_channel(api_key, channel_url):
    channel_id = extract_channel_id(channel_url)
    if channel_id:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.channels().list(
            part="snippet",
            id=channel_id
        )
        response = request.execute()
        channel_title = response['items'][0]['snippet']['title']
        print(f"Channel Title: {channel_title}")

        video_ids = fetch_videos(api_key, channel_id)
        comments = fetch_comments(api_key, video_ids)
        # Perform sentiment analysis on comments and aggregate results
        # Display overall sentiment and any other relevant metrics
    else:
        print("Invalid YouTube channel URL.")
    


    import re
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import streamlit as st

def extract_channel_id(url):
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/]+/)?(?:user|channel|c)/|youtu\.be/)([a-zA-Z0-9_-]{24})'
    match = re.match(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

def fetch_videos(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=10
    )
    response = request.execute()
    video_ids = [item['id']['videoId'] for item in response['items']]
    return video_ids

def fetch_comments(api_key, video_ids):
    comments = []
    analyzer = SentimentIntensityAnalyzer()
    youtube = build('youtube', 'v3', developerKey=api_key)
    for video_id in video_ids:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
    return comments

def analyze_channel(api_key, channel_url):
    channel_id = extract_channel_id(channel_url)
    if channel_id:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.channels().list(
            part="snippet",
            id=channel_id
        )
        response = request.execute()
        channel_title = response['items'][0]['snippet']['title']
        st.write(f"Channel Title: {channel_title}")

        video_ids = fetch_videos(api_key, channel_id)
        comments = fetch_comments(api_key, video_ids)
        # Perform sentiment analysis on comments and aggregate results
        # Display overall sentiment and any other relevant metrics
    else:
        st.write("Invalid YouTube channel URL.")

        
if __name__ == "__main__":
    main()
