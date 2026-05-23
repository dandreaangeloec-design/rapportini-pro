import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from streamlit_gsheets import GSheetsConnection
import io
import os
import base64

# Prova a caricare FPDF in modo robusto
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Rapportini Pro - D’Andrea Angelo E.C.", page_icon="📋", layout="centered")

# --- SCHERMATA DI LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.markdown("""
        <style>
        .login-box {
            background-color: rgba(128, 128, 128, 0.1);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 Accesso Riservato")
    st.subheader("D'Andrea Angelo E.C. - Gestione Rapportini")
    
    with st.container():
        password = st.text_input("Inserisci la password di sblocco:", type="password")
        if st.button("Accedi all'applicazione", use_container_width=True):
            if password == "Angelo2026!": 
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password errata! Accesso negato.")
    st.stop()

# --- CARICAMENTO LOGO SFONDO ---
def get_base64_img(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

# Cerca lo sfondo provando sia maiuscole che minuscole
file_sfondo = "Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg"
sfondo_base64 = get_base64_img(file_sfondo)

# --- CSS GRAFICA E SFONDO ---
css_code = """
    <style>
    div.stButton > button:first-child {
        background-color: #4f8bf9;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .card {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.15);
        margin-bottom: 10px;
        color: var(--text-color);
    }
    .stat-val { font-size: 22px; font-weight: bold; color: var(--text-color); }
    .stat-lbl { font-size: 12px; color: var(--text-color); opacity: 0.7; }
    </style>
"""

if sfondo_base64:
    css_code = css_code.replace("</style>", f"""
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url('data:image/jpeg;base64,{sfondo_base64}');
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.05;
        z-index: -1;
        pointer-events: none;
    }}
    </style>
    """)

st.markdown(css_code, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ANAGRAFICA CLIENTI ---
if "clienti_dict" not in st.session_state:
    st.session_state.clienti_dict = {
        "Bianchi S.r.l.": {"prezzo_ora": 45.0, "prezzo_km": 0.50},
        "Fr sangalli": {"prezzo_ora": 40.0, "prezzo_km": 0.45},
        "Rossi Costruzioni": {"

