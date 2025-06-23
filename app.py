import streamlit as st
import pandas as pd

from scraper import Scraper

st.set_page_config(page_title="Spotify Playlist Mood", layout="centered")
st.title("What's the mood of your Spotify Playlist?")

playlist_url = st.text_input(
    label="",
    placeholder="Give me your playlist URL! 😈"
)

st.markdown("###")
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    analyze = st.button("🔍 Analyze Playlist", use_container_width=True)

if analyze:
    try:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        scraper = Scraper()
        fig, stats = scraper.plot_radar(playlist_id)
        st.pyplot(fig)
        st.subheader("Statistics")
        
        styled_df = stats.set_index('Features').style.set_properties(**{
            'text-align': 'right'
        }).set_table_styles([{
            'selector': 'th',
            'props': [('text-align', 'center')]
        }])

        st.dataframe(styled_df)
    except Exception as e:
        st.error(f"Give me your Playlist URL!!! 👿")
