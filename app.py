import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from streamlit_gsheets import GSheetsConnection
import io
import os
import base64

# Forziamo la presenza di FPDF per evitare che i pulsanti spariscano
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
    st.title("🔒 Accesso Riservato")
    st.subheader("D'Andrea Angelo E.C. - Gestione Rapportini")
    password = st.text_input("Inserisci la password di sblocco:", type="password")
    if st.button("Accedi all'applicazione", use_container_width=True):
        if password == "Angelo2026!": 
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata! Accesso negato.")
    st.stop()

# --- CARICAMENTO IMMAGINI SFONDO ---
def get_base64_img(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

sfondo_base64 = get_base64_img("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg")

# CSS GRAFICA E SFONDO ADATTATO
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

# --- INIZIALIZZAZIONE MEMORIA DI BACKUP ---
if "rapportini_locali" not in st.session_state:
    st.session_state.rapportini_locali = []

# --- CONNESSIONE AL DATABASE (GOOGLE SHEETS) ---
rapportini_totali = []
conn_disponibile = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_database = conn.read(ttl="2s") # Aggiornamento quasi istantaneo
    df_database = df_database.dropna(how="all") 
    rapportini_totali = df_database.to_dict(orient="records")
    conn_disponibile = True
except Exception as e:
    rapportini_totali = st.session_state.rapportini_locali

if not rapportini_totali:
    rapportini_totali = [{"cliente": "Rossi Costruzioni", "cantiere": "Nessun dato presente nel database", "data": "2026-05-21", "km": 0, "ore": 0.0, "spese": 0.0, "note": ""}]

# Anagrafica Clienti Fissa
if "clienti_dict" not in st.session_state:
    st.session_state.clienti_dict = {
        "Bianchi S.r.l.": {"prezzo_ora": 45.0, "prezzo_km": 0.50},
        "Fr sangalli": {"prezzo_ora": 40.0, "prezzo_km": 0.45},
        "Rossi Costruzioni": {"prezzo_ora": 50.0, "prezzo_km": 0.60},
        "Verdi Impianti": {"prezzo_ora": 48.0, "prezzo_km": 0.55}
    }

MESI_DICT = {
    "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
    "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
    "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
}

def calcola_totale_rapportino(r):
    cli_info = st.session_state.clienti_dict.get(r["cliente"], {"prezzo_ora": 0, "prezzo_km": 0})
    try:
        ore = float(r["ore"]) if str(r["ore"]) != "nan" else 0.0
        km = int(float(r["km"])) if str(r["km"]) != "nan" else 0
        spese = float(r["spese"]) if str(r["spese"]) != "nan" else 0.0
    except:
        ore, km, spese = 0.0, 0, 0.0
    return (ore * cli_info["prezzo_ora"]) + (km * cli_info["prezzo_km"]) + spese

def clean_txt(text):
    if not text or str(text) == "nan": return ""
    return str(text).replace("€", "\x80").encode('latin-1', 'replace').decode('latin-1')

# --- FUNZIONI PDF CORRETTE SENZA CONCATENAZIONE ---
def genera_pdf(dati, mese_sel, cliente_sel, imponibile, flag_iva, perc_iva, flag_reverse):
    pdf = FPDF()
    pdf.add_page()
    
    # Se hai caricato LOGO.jpg su GitHub, lo mette nel PDF
    if os.path.exists("LOGO.jpg"): 
        pdf.image("LOGO.jpg", x=165, y=10, w=25)
    elif os.path.exists("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg"):
        pdf.image("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg", x=165, y=10, w=25)
        
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, 37, 200, 37)
    pdf.set_y(44)
    
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(15, 23, 42)
    titolo_report = f"REPORT ATTIVITA - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo_report += f" ({cliente_sel.upper()})"
    pdf.cell(190, 10, txt=clean_txt(titolo_report), ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(241, 245, 249)
    headers = [("Data", 22), ("Cliente", 38), ("Cantiere", 35), ("Ore", 14), ("Tar. Ora", 18), ("Km", 12), ("Tar. Km", 18), ("Spese", 15), ("Totale", 18)]
    for h, w in headers: pdf.cell(w, 8, h, 1, 0, "C", True)
    pdf.ln(8)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(51, 65, 85)
    
    for r in dati:
        pdf.cell(22, 8, clean_txt(r["Data"]), 1, 0, "C")
        pdf.cell(38, 8, clean_txt(r["Cliente"])[:22], 1, 0, "L")
        pdf.cell(35, 8, clean_txt(r["Cantiere"])[:20], 1, 0, "L")
        pdf.cell(14, 8, clean_txt(r["Ore"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/h"]), 1, 0, "C")
        pdf.cell(12, 8, clean_txt(r["Km"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/Km"]), 1, 0, "C")
        pdf.cell(15, 8, clean_txt(r["Spese Extra"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Totale Lordo"]), 1, 1, "R")
        
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    pdf.cell(125, 7, "", 0, 0)
    pdf.cell(35, 7, clean_txt("Totale Imponibile:"), 0, 0, "R")
    pdf.cell(30, 7, clean_txt(f"E {imponibile:,.2f}"), 1, 1, "R")
    
    calcolo_iva = 0.0
    if flag_reverse:
        pdf.cell(125, 7, "", 0, 0)
        pdf.set_font("Arial", "I", 9)
        pdf.cell(65, 7, clean_txt("Regime esenzione: Reverse Charge"), 0, 1, "R")
        pdf.set_font("Arial", "", 10)
    elif flag_iva:
        calcolo_iva = imponibile * (perc_iva / 100)
        pdf.cell(125, 7, "", 0, 0)
        pdf.cell(35, 7, clean_txt(f"IVA ({perc_iva}%):"), 0, 0, "R")
        pdf.cell(30, 7, clean_txt(f"E {calcolo_iva:,.2f}"), 1, 1, "R")
            
    totale_generale = imponibile + calcolo_iva
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(224, 242, 254)
    pdf.cell(125, 9, "", 0, 0)
    pdf.cell(35, 9, clean_txt("TOTALE DOVUTO:"), 0, 0, "R")
    pdf.cell(30, 9, clean_txt(f"E {totale_generale:,.2f}"), 1, 1, "C", True)
    return bytes(pdf.output())

def genera_pdf_note(rapportini_filtrati, mese_sel, cliente_sel):
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists("LOGO.jpg"): 
        pdf.image("LOGO.jpg", x=165, y=10, w=25)
    elif os.path.exists("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg"):
        pdf.image("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg", x=165, y=10, w=25)

    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, 37, 200, 37)
    pdf.set_y(44)
    
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(190, 6, txt=clean_txt(f"REGISTRO NOTE INTERVENTI - {mese_sel.upper()}"), align="L")
    pdf.ln(5)
    
    for r in rapportini_filtrati:
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(190, 7, txt=clean_txt(f" DATA: {r['data']} | CLIENTE: {r['cliente']} | CANTIERE: {r['cantiere']}"), border=1, ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Arial", "", 10)
        testo_nota = r["note"].strip() if "note" in r and str(r["note"]) != "nan" and str(r["note"]).strip() else "Nessuna descrizione."
        pdf.multi_cell(190, 5, txt=clean_txt(f"Note: {testo_nota}"), border=0)
        pdf.ln(4)
    return bytes(pdf.output())

# --- NAVIGAZIONE INTERFACCIA ---
st.sidebar.title("📋 Rapportini Pro")
menu = st.sidebar.radio("Navigazione", ["Rapportini Aziendali", "Nuovo Rapportino", "Report Mensili e Clienti", "Clienti"])

if menu == "Rapportini Aziendali":
    st.title("Rapportini Aziendali")
    st.caption("D'Andrea Angelo E.C. - Gestione e Controllo Interventi")
    
    tot_rapportini = len(rapportini_totali)
    tot_km = sum(int(float(r["km"])) for r in rapportini_totali if "km" in r and str(r["km"]) != "nan")
    tot_ore = sum(float(r["ore"]) for r in rapportini_totali if "ore" in r and str(r["ore"]) != "nan")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="card"><span class="stat-val">📄 {tot_rapportini}</span><br><span class="stat-lbl">Rapportini</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="card"><span class="stat-val">🕒 {tot_ore} h</span><br><span class="stat-lbl">
