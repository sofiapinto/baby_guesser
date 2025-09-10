import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import numpy as np

# --- Configuration ---
DB_FILE = "guesses.json"
MIN_WEIGHT = 5.0
MAX_WEIGHT = 12.0
DEFAULT_WEIGHT = 8.0

# --- Helper Functions for Data Persistence ---

def load_guesses():
    """Loads guesses from the JSON file."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_guesses(guesses):
    """Saves the list of guesses to the JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(guesses, f, indent=4)

# --- Main App ---

# Page Configuration
st.set_page_config(
    page_title="Baby Shower Guessing Game",
    page_icon="👶",
    layout="wide"
)

# --- Header ---
st.title("👶 Baby Shower Guessing Game")
st.markdown("Let's celebrate our amazing colleague! Add your guess for the new arrival below.")

# Load existing guesses
all_guesses = load_guesses()

# --- Layout (Form on the left, Chart on the right) ---
col1, col2 = st.columns([1, 2])

# --- Input Form ---
with col1:
    st.header("Your Guess")
    with st.form("guess_form", clear_on_submit=True):
        guesser_name = st.text_input("Your Name", placeholder="e.g., Jane Doe")
        baby_name_guess = st.text_input("Guessed Baby Name", placeholder="e.g., Alex")
        weight_guess = st.slider(
            "Guessed Weight (lbs)",
            min_value=MIN_WEIGHT,
            max_value=MAX_WEIGHT,
            value=DEFAULT_WEIGHT,
            step=0.1
        )
        arrival_guess = st.radio(
            "Arrival Time",
            ["Early", "On-time", "Late"],
            horizontal=True
        )
        
        submitted = st.form_submit_button("Submit My Guess!")

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
                all_guesses.append(new_guess)
                save_guesses(all_guesses)
                st.success("Your guess has been submitted! 🎉")

# --- Guesses Visualization ---
with col2:
    st.header("Guess Distribution")

    if not all_guesses:
        st.info("No guesses yet. Be the first!")
    else:
        # Convert to DataFrame for plotting
        df = pd.DataFrame(all_guesses)
        
        # Add a 'jitter' column for better visualization to avoid overlap
        np.random.seed(42) # for consistent jitter
        df['jitter'] = np.random.uniform(-0.5, 0.5, size=len(df))

        # Color scheme for arrival times
        color_scheme = alt.Scale(
            domain=['Early', 'On-time', 'Late'],
            range=['#3b82f6', '#16a34a', '#f97316'] # Blue, Green, Orange
        )

        # Base chart for the points
        points = alt.Chart(df).mark_circle(
            size=400,
            opacity=0.8
        ).encode(
            x=alt.X('weight:Q', title='Guessed Weight (lbs)', scale=alt.Scale(domain=[MIN_WEIGHT, MAX_WEIGHT])),
            y=alt.Y('jitter:Q', title=None, axis=None),
            color=alt.Color('arrival:N', scale=color_scheme, legend=alt.Legend(title="Arrival Guess")),
            tooltip=[
                alt.Tooltip('guesserName', title='Guesser'),
                alt.Tooltip('babyName', title='Baby Name Guess'),
                alt.Tooltip('weight', title='Weight (lbs)', format=".1f"),
                alt.Tooltip('arrival', title='Arrival')
            ]
        ).properties(
            height=200
        )

        # Text layer for the names inside the circles
        text = alt.Chart(df).mark_text(
            align='center',
            baseline='middle',
            color='white',
            fontSize=10,
            fontWeight='bold'
        ).encode(
            x='weight:Q',
            y='jitter:Q',
            text='babyName:N'
        )

        # Combine the charts
        chart = (points + text).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        st.markdown("---")
        st.subheader("All Guesses")
        st.dataframe(df[['guesserName', 'babyName', 'weight', 'arrival']], use_container_width=True)