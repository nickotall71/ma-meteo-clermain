import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import plotly.graph_objects as go
import streamlit.components.v1 as components
import requests

# --- 1. CONFIGURATION ET GÉOCODAGE ---
st.set_page_config(page_title="Météo Expert Pro", layout="wide", page_icon="🌤️")

def get_coords(ville):
    """Transforme un nom de ville en coordonnées GPS via l'API Geocoding"""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={ville}&count=1&language=fr&format=json"
    try:
        r = requests.get(url).json()
        if "results" in r:
            res = r["results"][0]
            return res["latitude"], res["longitude"], res.get("name", ville), res.get("admin1", "")
    except:
        pass
    return 46.368, 4.581, "Clermain", "Saône-et-Loire"

# Barre latérale de recherche
st.sidebar.header("🔍 Localisation")
ville_input = st.sidebar.text_input("Ville ou Commune", "Clermain")
LAT, LON, NOM_VILLE, REGION = get_coords(ville_input)

# --- 2. LOGIQUE DES ICÔNES RÉALISTES (SVG ANIMÉS) ---
def get_weather_icon(code):
    """Retourne l'URL d'une icône animée selon le code météo WMO"""
    base_url = "https://www.amcharts.com/wp-content/themes/amcharts4/css/img/icons/weather/animated/"
    # Mapping des codes météo vers les fichiers SVG animés
    icons = {
        0: "day.svg",              # Ciel dégagé
        1: "cloudy-day-1.svg",     # Principalement dégagé
        2: "cloudy-day-3.svg",     # Partiellement nuageux
        3: "cloudy.svg",           # Couvert
        45: "cloudy.svg",          # Brouillard
        48: "cloudy.svg",          # Brouillard givrant
        51: "rainy-4.svg",         # Bruine légère
        61: "rainy-5.svg",         # Pluie modérée
        63: "rainy-6.svg",         # Pluie forte
        71: "snowy-4.svg",         # Neige légère
        80: "rainy-1.svg",         # Averses légères
        95: "thunder.svg",         # Orage
    }
    filename = icons.get(int(code), "day.svg")
    if code > 3 and code < 50: filename = "cloudy.svg"
    elif code >= 51 and code <= 67: filename = "rainy-6.svg"
    elif code >= 71 and code <= 77: filename = "snowy-6.svg"
    
    return base_url + filename

# --- 3. RÉCUPÉRATION DES DONNÉES (MODÈLE AROME) ---
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

params = {
    "latitude": LAT,
    "longitude": LON,
    "hourly": ["temperature_2m", "precipitation", "weather_code", "wind_speed_10m"],
    "models": "best_match",
    "timezone": "Europe/Paris"
}

try:
    responses = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast", params=params)
    response = responses[0]
    hourly = response.Hourly()
    
    df = pd.DataFrame({
        "date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True).tz_convert('Europe/Paris'),
            end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True).tz_convert('Europe/Paris'),
            freq = pd.Timedelta(seconds = hourly.Interval()), inclusive = "left"
        ),
        "temp": hourly.Variables(0).ValuesAsNumpy(),
        "pluie": hourly.Variables(1).ValuesAsNumpy(),
        "code": hourly.Variables(2).ValuesAsNumpy(),
        "vent": hourly.Variables(3).ValuesAsNumpy()
    })
    
    df['icon_url'] = df['code'].apply(get_weather_icon)

    # --- 4. INTERFACE GRAPHIQUE ---
    st.title(f"🌦️ Station Météo : {NOM_VILLE} ({REGION})")
    
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("📡 Radar de pluie Live")
        # Radar RainViewer intégré
        radar_url = f"https://www.rainviewer.com/map.html?loc={LAT},{LON},10&type=radar&range=true&rt=1&st=1&v=1&p=1&is=1&v=1&sm=1&sn=1"
        components.iframe(radar_url, height=500)
        
        st.metric("🌡️ Température Actuelle", f"{df.iloc[0]['temp']:.1f} °C")
        st.metric("💨 Vent", f"{df.iloc[0]['vent']:.1f} km/h")

    with col2:
        st.subheader("📊 Prévisions & Phénomènes (AROME 1.3km)")
        
        fig = go.Figure()

        # Courbe de Température
        fig.add_trace(go.Scatter(
            x=df['date'][:48], y=df['temp'][:48],
            name="Température (°C)",
            line=dict(color='#FF8C00', width=4, shape='spline'),
            mode='lines'
        ))

        # Barres de Précipitations
        fig.add_trace(go.Bar(
            x=df['date'][:48], y=df['pluie'][:48],
            name="Pluie (mm)",
            marker_color='rgba(0, 150, 255, 0.5)',
            yaxis="y2"
        ))

        # AJOUT DES ICÔNES ANIMÉES SUR LE GRAPHIQUE
        # On affiche une icône toutes les 4 heures
        for i in range(0, 48, 4):
            fig.add_layout_image(
                dict(
                    source=df['icon_url'][i],
                    xref="x", yref="y",
                    x=df['date'][i],
                    y=df['temp'][i] + 1.2,
                    sizex=4 * 3600000, # Largeur de l'icône
                    sizey=2.5,         # Hauteur de l'icône
                    xanchor="center", yanchor="bottom"
                )
            )

        fig.update_layout(
            hovermode="x unified",
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis=dict(title="Température (°C)", gridcolor='rgba(255,255,255,0.1)'),
            yaxis2=dict(title="Précipitations (mm)", overlaying="y", side="right", range=[0, 10], showgrid=False),
            showlegend=False,
            font=dict(color="white")
        )
        st.plotly_chart(fig, use_container_width=True)

    # Style CSS pour l'ambiance "Dark Mode"
    st.markdown("""
        <style>
        .stApp { background-color: #121212; color: #e0e0e0; }
        .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
        </style>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur de flux : {e}")