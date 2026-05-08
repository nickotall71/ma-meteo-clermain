import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Météo Clermain", page_icon="🌤️", layout="wide")

# --- FONCTION DE RÉCUPÉRATION DES DONNÉES ---
@st.cache_data(ttl=900)
def recuperer_meteo():
    # Coordonnées de Clermain (71)
    lat, lon = 46.36, 4.58
    # On demande les données AROME pour 48h (2 jours)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability,precipitation&models=arome_france_hd&timezone=Europe%2FBerlin&forecast_days=2"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Création du tableau avec noms en Français pour le survol
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

# --- CALCUL DE L'HUMIDEX (RESSENTI) ---
def calculer_humidex(T, H):
    Td = T - ((100 - H) / 5.0)
    e = 6.11 * math.exp(5417.75 * (1.0/273.16 - 1.0/(273.15 + Td)))
    return round(T + 0.5555 * (e - 10.0), 1)

# --- CHARGEMENT DES DONNÉES ---
df_meteo = recuperer_meteo()

if df_meteo is not None:
    # 1. Index de l'heure actuelle
    maintenant = datetime.now()
    idx = (df_meteo['Heure'] - maintenant).abs().idxmin()
    
    # 2. Données pour les 4 cases (Metrics)
    t_actuelle = df_meteo['Température'].iloc[idx]
    v_actuel = df_meteo['Vent'].iloc[idx]
    p_actuelle = df_meteo['Probabilité Pluie'].iloc[idx]
    h_actuelle = df_meteo['Humidité'].iloc[idx]
    ressenti = calculer_humidex(t_actuelle, h_actuelle)

    st.title("🌤️ Météo Clermain - Haute Précision")

    # --- AFFICHAGE DES 4 CASES ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌡️ Température", f"{t_actuelle}°C")
    col2.metric("💨 Vent", f"{v_actuel} km/h")
    col3.metric("☔ Probabilité Pluie", f"{p_actuelle}%")
    col4.metric("🧘 Ressenti", f"{ressenti}°C")

    st.divider()

    # --- GRAPHE INTERACTIF (PLOTLY) ---
    st.subheader("Prévisions détaillées sur 48 heures")
    
    fig = go.Figure()

    # Courbe de Température
    fig.add_trace(go.Scatter(
        x=df_meteo['Heure'], 
        y=df_meteo['Température'],
        name='Température (°C)',
        line=dict(color='#FF4B4B', width=3),
        hovertemplate='%{y}°C'
    ))

    # Courbe du Vent
    fig.add_trace(go.Scatter(
        x=df_meteo['Heure'], 
        y=df_meteo['Vent'],
        name='Vent (km/h)',
        line=dict(color='#31333F', dash='dash'),
        hovertemplate='%{y} km/h'
    ))

    # Barres de Précipitations
    fig.add_trace(go.Bar(
        x=df_meteo['Heure'], 
        y=df_meteo['Pluie'],
        name='Pluie (mm)',
        marker_color='#0077FF',
        opacity=0.6,
        hovertemplate='%{y} mm'
    ))

    # Réglages de l'interactivité et du design
    fig.update_layout(
        hovermode="x unified",  # Affiche toutes les valeurs au survol d'une heure
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Date et Heure"),
        yaxis=dict(title="Valeurs"),
        height=500,
        margin=dict(l=0, r=0, t=50, b=0)
    )

    # Affichage du graphe
    st.plotly_chart(fig, use_container_width=True)

    # --- CARTE COMPACTE ET INFOS ---
    st.divider()
    map_col, info_col = st.columns([1, 2])
    
    with map_col:
        st.subheader("Localisation")
        map_data = pd.DataFrame({'lat': [46.36], 'lon': [4.58]})
        st.map(map_data, zoom=11)
        
    with info_col:
        st.subheader("Informations")
        st.info(f"""
        **Source :** Modèle AROME 1.3km (Météo-France) via Open-Meteo.  
        **Dernière mise à jour :** {maintenant.strftime('%H:%M')}  
        **Lieu :** Clermain (Navour-sur-Grosne)
        """)
        if st.button('🔄 Forcer l\'actualisation'):
            st.cache_data.clear()
            st.rerun()

else:
    st.error("Impossible de récupérer les données météo. Vérifiez votre connexion.")
