import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Météo Expert Pro", page_icon="🌤️", layout="wide")

# --- CALCUL DE L'HUMIDEX ---
def calculer_humidex(temp, humidite):
    # Formule officielle de l'Humidex
    # h = T + 0.5555 * (6.11 * exp(5417.75 * (1/273.16 - 1/(273.16 + point_de_rosee))) - 10)
    # On utilise ici une version simplifiée très précise
    alpha = ((17.27 * temp) / (237.7 + temp)) + math.log(humidite/100.0)
    point_rosee = (237.7 * alpha) / (17.27 - alpha)
    e = 6.11 * math.exp(5417.75 * (1/273.16 - 1/(273.16 + point_rosee)))
    h = temp + (0.5555 * (e - 10.0))
    return round(h, 1)

# --- LOGIQUE DES ICONES ---
def obtenir_icone(temperature, proba_pluie, pluie_mm):
    if pluie_mm > 0.1 or proba_pluie > 45:
        return "🌧️"
    elif proba_pluie > 15:
        return "⛅"
    elif temperature > 22:
        return "☀️"
    else:
        return "🌤️"

# --- GÉOCODAGE ---
def obtenir_coordonnees(ville):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={ville}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'MeteoApp/1.0'}, timeout=5)
        data = res.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']
    except:
        pass
    return 46.36, 4.58, "Clermain (Par défaut)"

# --- RÉCUPÉRATION DONNÉES (Avec Humidité) ---
@st.cache_data(ttl=900)
def fetch_meteo(lati, longi, model, days):
    # Ajout de relative_humidity_2m dans la requête
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lati}&longitude={longi}&hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m&models={model}&timezone=Europe%2FBerlin&forecast_days={days}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame({
            'Heure': pd.to_datetime(data['hourly']['time']),
            'Temp': data['hourly']['temperature_2m'],
            'Humidite': data['hourly']['relative_humidity_2m'],
            'Pluie': data['hourly']['precipitation'],
            'Vent': data['hourly']['wind_speed_10m']
        })
        df['Proba'] = data['hourly'].get('precipitation_probability', [0]*len(df))
        
        # Calcul de l'Humidex pour chaque ligne
        df['Humidex'] = df.apply(lambda r: calculer_humidex(r['Temp'], r['Humidite']), axis=1)
        
        return df.fillna(0)
    except:
        return None

# --- INTERFACE ---
st.sidebar.header("⚙️ Configuration")
nom_ville = st.sidebar.text_input("📍 Ville", value="Clermain")
lat, lon, nom_complet = obtenir_coordonnees(nom_ville)

df_arome = fetch_meteo(lat, lon, "arome_france_hd", 2)
df_ecmwf = fetch_meteo(lat, lon, "ecmwf_ifs025", 7)

if df_arome is not None:
    now = datetime.now()
    idx = (df_arome['Heure'] - now).abs().idxmin()
    
    # Données actuelles
    t_actu = df_arome['Temp'].iloc[idx]
    h_actu = df_arome['Humidex'].iloc[idx]
    p_max = df_arome['Proba'].iloc[idx:idx+2].max()
    icone = obtenir_icone(t_actu, p_max, df_arome['Pluie'].iloc[idx])

    st.title(f"{icone} Météo Expert : {nom_ville.capitalize()}")
    st.info(f"📍 **{nom_complet}**")

    # --- METRICS (Avec Humidex) ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🌡️ Temp.", f"{t_actu}°C")
    c2.metric("🥵 Ressenti", f"{h_actu}", help="Indice Humidex (Température ressentie)")
    c3.metric("💨 Vent", f"{df_arome['Vent'].iloc[idx]} km/h")
    c4.metric("☔ Pluie", f"{p_max}%")
    c5.metric("✨ Ciel", icone)

    # --- GRAPHIQUE ---
    def make_fig(df, is_detail):
        fig = go.Figure()
        
        # Température Réelle
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Temp'], name="Temp. Réelle", line=dict(color='#FF9800', width=3)))
        
        # Humidex (Ressenti) - Ligne fine en rouge
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Humidex'], name="Humidex (Ressenti)", line=dict(color='#e74c3c', width=1, dash='dash')))
        
        # Vent
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Vent'], name="Vent", line=dict(color='#9E9E9E', width=1.5, dash='dot')))
        
        # Pluie
        fig.add_trace(go.Bar(x=df['Heure'], y=df['Pluie'], name="Pluie", marker_color='#2196F3', opacity=0.4))
        
        fig.update_layout(height=450, margin=dict(l=0,r=0,t=30,b=0), hovermode="x unified", legend=dict(orientation="h", y=1.15))
        return fig

    st.divider()
    st.subheader("🎯 Prévisions 48h (AROME)")
    st.plotly_chart(make_fig(df_arome, True), use_container_width=True)

    if df_ecmwf is not None:
        st.divider()
        st.subheader("📅 Tendance 7 Jours (ECMWF)")
        st.plotly_chart(make_fig(df_ecmwf, False), use_container_width=True)

    if st.sidebar.button("🔄 Actualiser"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error("Erreur de chargement.")
