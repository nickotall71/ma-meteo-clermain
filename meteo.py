import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Météo Pro", page_icon="🌤️", layout="wide")

# --- FONCTION DE GÉOCODAGE (Nom de ville -> Coordonnées) ---
def obtenir_coordonnees(ville):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={ville}&format=json&limit=1"
        headers = {'User-Agent': 'MonAppliMeteo/1.0'}
        response = requests.get(url, headers=headers)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']
    except:
        pass
    return 46.36, 4.58, "Clermain (Par défaut)"

# --- BARRE DE RECHERCHE ---
st.sidebar.header("🔍 Recherche")
nom_ville = st.sidebar.text_input("Entrez une ville (ex: Clermain, Mâcon, Paris...)", value="Clermain")

# On récupère les coordonnées de la ville saisie
lat, lon, nom_complet = obtenir_coordonnees(nom_ville)

# --- FONCTION DE RÉCUPÉRATION DES DONNÉES MÉTÉO ---
@st.cache_data(ttl=900)
def recuperer_meteo(lati, longi):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lati}&longitude={longi}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability,precipitation&models=arome_france_hd&timezone=Europe%2FBerlin&forecast_days=2"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame({
            'Heure': pd.to_datetime(data['hourly']['time']),
            'Température': data['hourly']['temperature_2m'],
            'Humidité': data['hourly']['relative_humidity_2m'],
            'Vent': data['hourly']['wind_speed_10m'],
            'Probabilité Pluie': data['hourly']['precipitation_probability'],
            'Pluie': data['hourly']['precipitation']
        })
        return df
    except:
        return None

def calculer_humidex(T, H):
    Td = T - ((100 - H) / 5.0)
    e = 6.11 * math.exp(5417.75 * (1.0/273.16 - 1.0/(273.15 + Td)))
    return round(T + 0.5555 * (e - 10.0), 1)

# --- CHARGEMENT ---
df_meteo = recuperer_meteo(lat, lon)

if df_meteo is not None:
    maintenant = datetime.now()
    idx = (df_meteo['Heure'] - maintenant).abs().idxmin()
    
    t = df_meteo['Température'].iloc[idx]
    v = df_meteo['Vent'].iloc[idx]
    p = df_meteo['Probabilité Pluie'].iloc[idx]
    ressenti = calculer_humidex(t, df_meteo['Humidité'].iloc[idx])

    st.title(f"🌤️ Météo : {nom_ville.capitalize()}")
    st.caption(f"📍 {nom_complet}")

    # Encarts
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Température", f"{t}°C")
    c2.metric("Vent", f"{v} km/h")
    c3.metric("Pluie (Prob.)", f"{p}%")
    c4.metric("Ressenti", f"{ressenti}°C")

    st.divider()

    # Graphe
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_meteo['Heure'], y=df_meteo['Température'], name='Température (°C)', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df_meteo['Heure'], y=df_meteo['Vent'], name='Vent (km/h)', line=dict(color='gray', dash='dash')))
    fig.add_trace(go.Bar(x=df_meteo['Heure'], y=df_meteo['Pluie'], name='Pluie (mm)', marker_color='blue', opacity=0.5))
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1), height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Carte et Infos
    col_m, col_i = st.columns([1, 2])
    with col_m:
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=10)
    with col_i:
        st.info(f"Coordonnées : {lat}, {lon}")
        if st.button('🔄 Actualiser'):
            st.cache_data.clear()
            st.rerun()
