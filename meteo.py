import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Météo Expert Pro", page_icon="🌤️", layout="wide")

# --- CALCUL DE L'HUMIDEX ---
def calculer_humidex(temp, humidite):
    try:
        alpha = ((17.27 * temp) / (237.7 + temp)) + math.log(humidite/100.0)
        point_rosee = (237.7 * alpha) / (17.27 - alpha)
        e = 6.11 * math.exp(5417.75 * (1/273.16 - 1/(273.16 + point_rosee)))
        h = temp + (0.5555 * (e - 10.0))
        return round(h, 1)
    except:
        return round(temp, 1)

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
    nom_clean = ville.strip().lower()
    base_locales = {
        "clermain": (46.3667, 4.5833, "Clermain, Bourgogne-Franche-Comté"),
        "navour": (46.3667, 4.5833, "Navour-sur-Grosne, Bourgogne-Franche-Comté"),
        "macon": (46.3000, 4.8333, "Mâcon, Bourgogne-Franche-Comté"),
        "tournus": (46.5667, 4.9111, "Tournus, Bourgogne-Franche-Comté"),
        "chalon": (46.7833, 4.8500, "Chalon-sur-Saône, Bourgogne-Franche-Comté"),
        "lyon": (45.7500, 4.8500, "Lyon, Auvergne-Rhône-Alpes"),
        "paris": (48.8566, 2.3522, "Paris, Île-de-France")
    }
    for cle, valeurs in base_locales.items():
        if cle in nom_clean:
            return valeurs
    try:
        url_direct = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(ville)}&format=json&limit=1"
        res = requests.get(url_direct, headers={'User-Agent': 'MeteoExpertMobile_V6'}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']
    except:
        pass
    return 46.3667, 4.5833, f"{ville} (Coordonnées : Saône-et-Loire)"

# --- RÉCUPÉRATION DES DONNÉES ---
def fetch_meteo(lati, longi, model, days):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lati}&longitude={longi}&hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m&models={model}&timezone=Europe%2FBerlin&forecast_days={days}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        
        df = pd.DataFrame({
            'Heure': pd.to_datetime(data['hourly']['time']),
            'Temp': data['hourly']['temperature_2m'],
            'Humidite': data['hourly']['relative_humidity_2m'],
            'Pluie': data['hourly']['precipitation'],
            'Vent': data['hourly']['wind_speed_10m']
        })
        df['Proba'] = data['hourly'].get('precipitation_probability', [0]*len(df))
        df['Humidex'] = df.apply(lambda r: calculer_humidex(r['Temp'], r['Humidite']), axis=1)
        return df.fillna(0)
    except:
        return None

# --- INTERFACE ---
st.title("🌤️ Météo Expert Pro")

nom_ville = st.text_input("🔍 Entrez une ville", value="Clermain")
lat, lon, nom_complet = obtenir_coordonnees(nom_ville)

df_arome = fetch_meteo(lat, lon, "arome_france_hd", 2)
df_ecmwf = fetch_meteo(lat, lon, "ecmwf_ifs025", 7)

if df_arome is not None:
    now = datetime.now()
    idx = (df_arome['Heure'] - now).abs().idxmin()
    
    t_actu = df_arome['Temp'].iloc[idx]
    h_actu = df_arome['Humidex'].iloc[idx]
    p_max = df_arome['Proba'].iloc[idx:idx+2].max()
    icone = obtenir_icone(t_actu, p_max, df_arome['Pluie'].iloc[idx])

    st.success(f"📍 **{nom_complet}**")

    # --- METRICS COMPACTES ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temp.", f"{t_actu}°C")
    c2.metric("🥵 Ressenti", f"{h_actu}°C")
    c3.metric("💨 Vent", f"{df_arome['Vent'].iloc[idx]} km/h")
    c4.metric("☔ Pluie (2h)", f"{p_max}%")

    # --- FONCTION GRAPHIQUE OPTIMISÉE POUR SMARTPHONE ---
    def make_fig(df, is_detail):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Temp'], name="Temp.", line=dict(color='#FF9800', width=3)))
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Humidex'], name="Humidex", line=dict(color='#e74c3c', width=1.5, dash='dash')))
        fig.add_trace(go.Scatter(x=df['Heure'], y=df['Vent'], name="Vent", line=dict(color='#9E9E9E', width=1.5, dash='dot')))
        fig.add_trace(go.Bar(x=df['Heure'], y=df['Pluie'], name="Pluie", marker_color='#2196F3', opacity=0.4))
        
        fig.update_layout(
            height=350, # Hauteur légèrement réduite idéale pour les écrans mobiles
            margin=dict(l=10, r=10, t=20, b=10), 
            hovermode="x unified", 
            legend=dict(
                orientation="h", 
                y=-0.2, # Déplacement de la légende en dessous pour éviter les chevauchements sur petit écran
                x=0.5,
                xanchor="center"
            )
        )
        return fig

    # --- AFFICHAGE SÉCURISÉ DES GRAPHIQUES ---
    st.divider()
    st.subheader("🎯 Zoom 48h (AROME France)")
    try:
        # Le paramètre config retire les boutons lourds de Plotly pour soulager les mobiles
        st.plotly_chart(make_fig(df_arome, True), use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.warning("Affichage simplifié du graphique 48h sur ce terminal.")
        st.line_chart(df_arome[['Heure', 'Temp', 'Humidex', 'Vent']].set_index('Heure'))

    if df_ecmwf is not None:
        st.divider()
        st.subheader("📅 Tendance 7 Jours (ECMWF)")
        try:
            st.plotly_chart(make_fig(df_ecmwf, False), use_container_width=True, config={'displayModeBar': False})
        except Exception as e:
            st.line_chart(df_ecmwf[['Heure', 'Temp', 'Humidex', 'Vent']].set_index('Heure'))
else:
    st.error("⚠️ Problème technique de synchronisation. Veuillez rafraîchir l'application.")
