import spotipy

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib as mpl
import matplotlib.pyplot as plt

from spotipy.oauth2 import SpotifyClientCredentials

class Scraper:
    
    KEY_FEATURES = ['danceability', 'energy', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence']
    FEATURE_RENAME = {
        'danceability': 'Danceable',
        'energy': 'Energy Level',
        'speechiness': 'Speech-like',
        'acousticness': 'Acoustic Sound',
        'instrumentalness': 'Instrumental Feel',
        'liveness': 'Live Performance',
        'valence': 'Happiness'
    }
    
    def __init__(self):
        client_credentials_manager = SpotifyClientCredentials(
            client_id=st.secrets['CLIENT_ID'],
            client_secret=st.secrets['CLIENT_SECRET']
        )
        self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    def get_tracks_from_playlist(self, playlist_id, with_features=True):
        track_ids = []
        results = self.sp.playlist_tracks(playlist_id, limit=100)
        
        while results:
            for item in results['items']:
                if item['track'] is not None:
                    track_ids.append(item['track']['id'])

            if results['next']:
                results = self.sp.next(results)
            else:
                break

        if with_features:
            return self.get_audio_features(track_ids=track_ids)
        
        return track_ids
    
    def get_audio_features(self, track_ids):
        features = self.sp.audio_features(tracks=track_ids)

        return [
            {key: f[key] for key in self.KEY_FEATURES + ['id']} 
            for f in features if f is not None
        ]
        
    def get_tracks_dataframe(self, playlist_id):
        feature_dicts = self.get_tracks_from_playlist(playlist_id, with_features=True)
        df = pd.DataFrame(feature_dicts)
        return df
    

    def plot_radar(self, playlist_id):
        df = self.get_tracks_dataframe(playlist_id).iloc[:, :7]
        features_mean = df.mean()
        labels = [self.FEATURE_RENAME.get(col, col) for col in features_mean.index]
        stats = features_mean.values

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        stats = np.concatenate((stats, [stats[0]]))
        angles += angles[:1]

        mpl.rcParams['font.family'] = 'DejaVu Sans'

        fig, ax = plt.subplots(
            figsize=(7, 7),
            subplot_kw=dict(polar=True),
            facecolor='white'
        )
        ax.set_facecolor('white')

        ax.plot(angles, stats, color='#00B386', linewidth=2.5)
        ax.fill(angles, stats, color='#00B386', alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=11, fontweight='medium', color='#333333')  

        ax.set_yticklabels([])
        ax.tick_params(axis='x', pad=10)
        ax.spines['polar'].set_color('#AAAAAA')
        ax.spines['polar'].set_linewidth(1)

        ax.grid(color='#AAAAAA', linestyle='dotted', linewidth=1)
        ax.set_title('Playlist Mood Profile', fontsize=16, fontweight='semibold', color='#222222', pad=20)

        plt.tight_layout()

        features_mean = features_mean.rename(self.FEATURE_RENAME)
        features_mean = pd.DataFrame(features_mean).reset_index()
        features_mean.columns = ['Features', 'Value']

        return fig, features_mean