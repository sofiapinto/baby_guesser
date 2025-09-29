import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import boto3
from collections import Counter
from PIL import Image
from wordcloud import get_single_color_func
from botocore import UNSIGNED
from botocore.client import Config

PASTEL_COLORS_DARKER = [
    "#E67C7C",  # deeper pastel pink
    "#7FB3D5",  # deeper pastel blue
    "#82B366",  # deeper pastel green
    "#E6A97B",  # deeper pastel peach
    "#A999D8",  # deeper pastel lavender
]

# Custom color function
class SimplePastelColorFunc(object):
    def __init__(self, colors):
        self.colors = colors

    def __call__(self, word, font_size, position, orientation, random_state=None, **kwargs):
        return np.random.choice(self.colors)

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
BUCKET = "bb-guesser-app"

MIN_WEIGHT = 5.0
MAX_WEIGHT = 12.0
DEFAULT_WEIGHT = 8.0

# --- Helper Functions for Data Persistence ---


def load_guesses():
    """Reads all user guess JSONs and combines them into one list."""
    all_guesses = []

    # List objects in the guesses folder
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="guesses/")

    if "Contents" not in response:
        return []  # no guesses yet

    for obj in response["Contents"]:
        key = obj["Key"]

        # Skip non-json files if needed
        if not key.endswith(".json"):
            continue

        # Download the object
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        data = json.loads(resp["Body"].read())

        # Merge guesses
        all_guesses.extend(data)

    return all_guesses

def save_guesses(user_id, new_guesses):
    user_id = user_id.lower()
    key = f"guesses/{user_id}.json"
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        guesses = json.loads(resp["Body"].read())
    except s3.exceptions.NoSuchKey:
        guesses = []

    guesses.extend(new_guesses)

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(guesses, indent=4),
        ContentType="application/json"
    )

# --- Main App ---

# Page Configuration
st.set_page_config(
    page_title="Liz's baby shower guessing game",
    page_icon="🧸",
    layout="wide"
)

# --- Header ---
st.title("🧸 Liz's baby shower guessing game 🧸")
st.markdown("## 💖 We will miss you Liz! Wishing you all the best on this exciting journey into parenthood. 💖")


# --- Layout (Form on the left, Chart on the right) ---
col1, col2 = st.columns([1, 2])

# --- Input Form ---
with col1:
    st.header("Your guess")
    st.markdown("Let's celebrate our amazing colleague Liz! Add as many guesses as you wish for the new arrival below.")

    with st.form("guess_form", clear_on_submit=True):
        guesser_name = st.text_input("Your name", placeholder="e.g., Seth")
        baby_name_guess = st.text_input("Guess the baby name", placeholder="e.g., Alex")
        weight_guess = st.slider(
            "Guess the weight (lbs)",
            min_value=MIN_WEIGHT,
            max_value=MAX_WEIGHT,
            value=DEFAULT_WEIGHT,
            step=0.5
        )
        arrival_guess = st.radio(
            "Arrival time",
            ["Early", "On-time", "Late"],
            horizontal=True
        )
        
        submitted = st.form_submit_button("Submit my guess!")

        if submitted:
            if not guesser_name or not baby_name_guess:
                st.warning("Please fill out all the fields before submitting.")
            else:
                new_guess = {
                    "guesserName": guesser_name,
                    "babyName": baby_name_guess,
                    "weight": weight_guess,
                    "arrival": arrival_guess
                }
                save_guesses(guesser_name, [new_guess])
                st.success("Your guess has been submitted! 🎉")

# Visualising guesses
with col2:
    st.header("Guesses from everyone so far")
    # Load existing guesses
    all_guesses = load_guesses()

    refresh_data_button = st.button("Click to get newest data!")
    if refresh_data_button:
        all_guesses = load_guesses()

    if not all_guesses:
        st.info("No guesses yet. Be the first!")
    else:
        # Convert to DataFrame for plotting
        df = pd.DataFrame(all_guesses)

        # Color scheme for arrival times
        color_scheme = alt.Scale(
            domain=['Early', 'On-time', 'Late'],
            range=['#3b82f6', '#16a34a', '#f97316'] # Blue, Green, Orange
        )

        col3, wordcloud_col, col4 = st.columns([1,4,1])
        with wordcloud_col:
            # Join names into one string

            name_counts = Counter(df["babyName"].str.lower().str.strip().tolist())

            wordcloud = WordCloud(
                width=400,
                height=200,
                scale=2,
                background_color="white",
                colormap="inferno"
            ).generate_from_frequencies(name_counts)

            # Apply pastel colors
            wordcloud.recolor(color_func=SimplePastelColorFunc(PASTEL_COLORS_DARKER))

            # Display with matplotlib
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.set_title("Baby name guesses", fontsize=20, fontweight="bold", pad=20)
            ax.axis("off")

            st.pyplot(fig, use_container_width=True)

        st.markdown("---")

        # Base chart for the points
        df['stack'] = df.groupby('weight').cumcount()

        # Compress vertical spacing by multiplying stack level
        stack_spacing = 0.05
        df['stack'] = df['stack'] * stack_spacing

        points = alt.Chart(df).mark_circle(size=1000, opacity=0.8).encode(
            x=alt.X('weight:Q', title='Guessed Weight (lbs)', scale=alt.Scale(domain=[MIN_WEIGHT-0.5, MAX_WEIGHT+0.5])),
            y=alt.Y('stack:Q', title=None, axis=None, scale =alt.Scale(domain=[df['stack'].min()-stack_spacing, df['stack'].max()+stack_spacing])), 
            color=alt.Color('arrival:N', scale=color_scheme, legend=alt.Legend(title="Arrival time guess")),
            tooltip=[
                alt.Tooltip('babyName', title='Baby name guess'),
                alt.Tooltip('weight', title='Weight (lbs)', format=".1f"),
                alt.Tooltip('arrival', title='Arrival')
            ]
        ).properties(
            height=400
        )

        text = alt.Chart(df).mark_text(
            align='center',
            baseline='middle',
            color='white',
            fontSize=10
        ).encode(
            x='weight:Q',
            y='stack:Q',
            text='babyName:N'
        )

        chart = (points + text).properties(
            title=alt.TitleParams(
                text="Baby weight and arrival time guesses",
                fontSize=30,
                anchor="middle",
                color="black"
            )
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        st.markdown("---")