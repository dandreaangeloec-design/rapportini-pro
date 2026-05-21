import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from streamlit_gsheets import GSheetsConnection
import io
import os
import base64

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Rapportini Pro - D’Andrea Angelo E.C.", page_icon="📋", layout="centered")

# --- SCHERMATA DI LOGIN (SICUREZZA PER APP PUBBLICA) ---
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

sfondo_base64 = get_base64_img("Gemini_Generated_Image_9pe1fw9pe1fw9pe1.jpeg")

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

# --- DIZIONARI DI SUPPORTO ---
MESI_DICT = {
    "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
    "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
    "Settembre": "09", "Octobre": "10", "Novembre": "11", "Dicembre": "12"
}

# --- CONNESSIONE AL DATABASE (GOOGLE SHEETS) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_database = conn.read(ttl="10s") # Aggiornamento rapido della cache
    st.session_state.rapportini = df_database.to_dict(orient="records")
except Exception as e:
    if "rapportini" not in st.session_state:
        st.session_state.rapportini = []

# Caricamento Clienti in Session State (Sempre modificabili nell'ultimo tab)
if "clienti_dict" not in st.session_state:
    st.session_state.clienti_dict = {
        "Bianchi S.r.l.": {"prezzo_ora": 45.0, "prezzo_km": 0.50},
        "Fr sangalli": {"prezzo_ora": 40.0, "prezzo_km": 0.45},
        "Rossi Costruzioni": {"prezzo_ora": 50.0, "prezzo_km": 0.60},
        "Verdi Impianti": {"prezzo_ora": 48.0, "prezzo_km": 0.55}
    }

if "editing_idx" not in st.session_state: st.session_state.editing_idx = None
if "chk_iva" not in st.session_state: st.session_state.chk_iva = False
if "chk_rev" not in st.session_state: st.session_state.chk_rev = False

def calcola_totale_rapportino(r):
    cli_info = st.session_state.clienti_dict.get(r["cliente"], {"prezzo_ora": 0, "prezzo_km": 0})
    return (float(r["ore"]) * cli_info["prezzo_ora"]) + (int(r["km"]) * cli_info["prezzo_km"]) + float(r["spese"])

def clean_txt(text):
    if not text: return ""
    return str(text).replace("€", "\x80").encode('latin-1', 'replace').decode('latin-1')

def chiudi_altro_flag(flag_modificato):
    if flag_modificato == "iva" and st.session_state.chk_iva: st.session_state.chk_rev = False
    elif flag_modificato == "reverse" and st.session_state.chk_rev: st.session_state.chk_iva = False

def salva_su_database():
    try:
        df_save = pd.DataFrame(st.session_state.rapportini)
        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_save)
    except:
        pass

# --- FUNZIONI PDF ---
def genera_pdf(dati, mese_sel, cliente_sel, imponibile, flag_iva, perc_iva, flag_reverse):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("LOGO.jpg"): pdf.image("LOGO.jpg", x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14).set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9).set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13).set_text_color(15, 23, 42)
    titolo_report = f"REPORT ATTIVITA - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo_report += f" ({cliente_sel.upper()})"
    pdf.cell(190, 10, txt=clean_txt(titolo_report), ln=True, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9).set_fill_color(241, 245, 249)
    headers = [("Data", 22), ("Cliente", 38), ("Cantiere", 35), ("Ore", 14), ("Tar. Ora", 18), ("Km", 12), ("Tar. Km", 18), ("Spese", 15), ("Totale", 18)]
    for h, w in headers: pdf.cell(w, 8, h, 1, 0, "C", True)
    pdf.ln(8); pdf.set_font("Arial", "", 8)
    
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
        
    pdf.ln(4); pdf.set_font("Arial", "", 10).cell(125, 7, "", 0, 0)
    pdf.cell(35, 7, clean_txt("Totale Imponibile:"), 0, 0, "R")
    pdf.cell(30, 7, clean_txt(f"€ {imponibile:,.2f}"), 1, 1, "R")
    
    calcolo_iva = 0.0
    if flag_reverse:
        pdf.cell(125, 7, "", 0, 0); pdf.set_font("Arial", "I", 9)
        pdf.cell(65, 7, clean_txt("Regime esenzione: Reverse Charge"), 0, 1, "R")
    elif flag_iva:
        calcolo_iva = imponibile * (perc_iva / 100)
        pdf.cell(125, 7, "", 0, 0); pdf.cell(35, 7, clean_txt(f"IVA ({perc_iva}%):"), 0, 0, "R")
        pdf.cell(30, 7, clean_txt(f"€ {calcolo_iva:,.2f}"), 1, 1, "R")
            
    totale_generale = imponibile + calcolo_iva
    pdf.ln(2); pdf.set_font("Arial", "B", 11).set_fill_color(224, 242, 254)
    pdf.cell(125, 9, "", 0, 0); pdf.cell(35, 9, clean_txt("TOTALE DOVUTO:"), 0, 0, "R")
    pdf.cell(30, 9, clean_txt(f"€ {totale_generale:,.2f}"), 1, 1, "C", True)
    return bytes(pdf.output())

def genera_pdf_note(rapportini_filtrati, mese_sel, cliente_sel):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("LOGO.jpg"): pdf.image("LOGO.jpg", x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14).set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9).set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13).set_text_color(15, 23, 42)
    titolo = f"REGISTRO NOTE E DESCRIZIONI INTERVENTI - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo += f"\nCLIENTE: {cliente_sel.upper()}"
    pdf.multi_cell(190, 6, txt=clean_txt(titolo), align="L")
    pdf.set_draw_color(148, 163, 184); pdf.line(10, pdf.get_y() + 4, 200, pdf.get_y() + 4); pdf.ln(8)
    
    for r in rapportini_filtrati:
        pdf.set_font("Arial", "B", 10).set_text_color(30, 41, 59).set_fill_color(241, 245, 249)
        pdf.cell(190, 7, txt=clean_txt(f" DATA: {r['data']} | CLIENTE: {r['cliente']} | CANTIERE: {r['cantiere']}"), border=1, ln=True, fill=True)
        pdf.set_font("Arial", "", 10).set_text_color(51, 65, 85); pdf.ln(2)
        testo_nota = r["note"].strip() if r["note"] and str(r["note"]).strip() and str(r["note"]) != "nan" else "Nessuna nota registrata."
        pdf.multi_cell(190, 5, txt=clean_txt(f"Note: {testo_nota}"), border=0)
        pdf.ln(4); pdf.set_draw_color(226, 232, 240); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(4)
    return bytes(pdf.output())

# --- INTERFACCIA ---
st.sidebar.title("📋 Rapportini")
menu = st.sidebar.radio("Navigazione", ["Rapportini Aziendali", "Nuovo Rapportino", "Report Mensili e Clienti", "Clienti"])

if menu == "Rapportini Aziendali":
    st.title("Rapportini Aziendali")
    st.caption("D'Andrea Angelo E.C. - Gestione e Controllo Interventi")
    
    tot_rapportini = len(st.session_state.rapportini)
    tot_km = sum(int(r["km"]) for r in st.session_state.rapportini if str(r["km"]) != "nan")
    tot_ore = sum(float(r["ore"]) for r in st.session_state.rapportini if str(r["ore"]) != "nan")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="card"><span class="stat-val">📄 {tot_rapportini}</span><br><span class="stat-lbl">Rapportini Totali</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="card"><span class="stat-val">🕒 {tot_ore} ore</span><br><span class="stat-lbl">Tempo Totale</span></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="card"><span class="stat-val">🚀 {tot_km} km</span><br><span class="stat-lbl">Distanza Totale</span></div>', unsafe_allow_html=True)
        
    st.subheader("Ultimi rapportini inseriti")
    for idx, r in enumerate(reversed(st.session_state.rapportini)):
        real_idx = len(st.session_state.rapportini) - 1 - idx
        importo_singolo = calcola_totale_rapportino(r)
        
        if st.session_state.editing_idx == real_idx:
            with st.form(key=f"edit_f_{real_idx}"):
                st.markdown("### ✏️ Modifica Intervento")
                e_cliente = st.selectbox("Cliente", list(st.session_state.clienti_dict.keys()), index=list(st.session_state.clienti_dict.keys()).index(r['cliente']))
                e_cantiere = st.text_input("Cantiere", value=r['cantiere'])
                e_data = st.date_input("Data", datetime.strptime(str(r['data']), "%Y-%m-%d") if '-' in str(r['data']) else datetime.now())
                e_km = st.number_input("Km", min_value=0, value=int(r['km']))
                e_ore = st.number_input("Ore", min_value=0.0, value=float(r['ore']), step=0.5)
                e_spese = st.number_input("Spese (€)", min_value=0.0, value=float(r['spese']))
                e_note = st.text_area("Note", value="" if str(r['note']) == "nan" else str(r['note']))
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 Salva"):
                    st.session_state.rapportini[real_idx] = {"cliente": e_cliente, "cantiere": e_cantiere, "data": str(e_data), "km": e_km, "ore": e_ore, "spese": e_spese, "note": e_note}
                    salva_su_database()
                    st.session_state.editing_idx = None
                    st.rerun()
                if b2.form_submit_button("❌ Annulla"):
                    st.session_state.editing_idx = None
                    st.rerun()
        else:
            nota_testo = "" if str(r["note"]) == "nan" or not r["note"] else str(r["note"])
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items: center;">
                    <strong style="color: var(--text-color); font-size: 16px;">{r['cliente']}</strong>
                    <span style="background-color:#22c55e20; color:#22c55e; font-weight:bold; padding:4px 10px; border-radius:12px; font-size:14px;">
                        € {importo_singolo:.2f}
                    </span>
                </div>
                <div style="color: var(--text-color); opacity: 0.7; font-size:13px; margin-top:5px;">📍 {r['cantiere']} | 📅 {r['data']}</div>
                <div style="margin-top:8px; font-size:13px; color: var(--text-color); opacity: 0.85;">
                    🚗 {r['km']} km  •  🕒 {r['ore']} ore  •  🧾 Spese: € {float(r['spese']):.2f}
                </div>
                {f'<div style="margin-top:8px; font-size:12px; font-style:italic; background:rgba(128,128,128,0.08); padding:6px; border-radius:6px;">📝 {nota_testo}</div>' if nota_testo else ""}
            </div>
            """, unsafe_allow_html=True)
            
            c_mod, c_del = st.columns(2)
            if c_mod.button("✏️ Modifica", key=f"ed_{real_idx}", use_container_width=True):
                st.session_state.editing_idx = real_idx
                st.rerun()
            if c_del.button("❌ Elimina", key=f"del_{real_idx}", use_container_width=True):
                st.session_state.rapportini.pop(real_idx)
                salva_su_database()
                st.rerun()

elif menu == "Nuovo Rapportino":
    st.title("Nuovo Rapportino")
    cliente = st.selectbox("Cliente *", ["Seleziona cliente"] + list(st.session_state.clienti_dict.keys()))
    if cliente != "Seleziona cliente":
        st.info(f"Tariffario: **€ {st.session_state.clienti_dict[cliente]['prezzo_ora']:.2f}/h** e **€ {st.session_state.clienti_dict[cliente]['prezzo_km']:.2f}/km**")
    cantiere = st.text_input("Cantiere *")
    data = st.date_input("Data *", datetime.now())
    col_km, col_ore = st.columns(2)
    km = col_km.number_input("Km percorsi *", min_value=0, value=0)
    ore = col_ore.number_input("Ore lavorate *", min_value=0.0, value=0.0, step=0.5)
    spese = st.number_input("Spese extra (€)", min_value=0.0, value=0.0)
    note = st.text_area("Note / Descrizione Intervento")
    
    st.write("Firma del cliente")
    st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="#000000", background_color="#ffffff", height=150, key="canvas")
    
    if st.button("💾 Salva Rapportino", use_container_width=True):
        if cliente == "Seleziona cliente" or not cantiere:
            st.error("Compila tutti i campi obbligatori!")
        else:
            nuovo = {"cliente": cliente, "cantiere": cantiere, "data": str(data), "km": int(km), "ore": float(ore), "spese": float(spese), "note": note}
            st.session_state.rapportini.append(nuovo)
            salva_su_database()
            st.success("Salvataggio completato nel Cloud!")

elif menu == "Report Mensili e Clienti":
    st.title("Generazione Report Avanzati")
    mese = st.selectbox("Seleziona Mese", list(MESI_DICT.keys()), index=4)
    cliente_selezionato = st.selectbox("Seleziona Cliente", ["Tutti i clienti"] + list(st.session_state.clienti_dict.keys()), index=0)
    
    st.markdown('<div class="card">🛠️ **Opzioni Fiscali**', unsafe_allow_html=True)
    c_iva1, c_iva2 = st.columns(2)
    attiva_iva = c_iva1.checkbox("Calcola IVA", key="chk_iva", on_change=chiudi_altro_flag, args=("iva",))
    reverse_charge = c_iva2.checkbox("Reverse Charge", key="chk_rev", on_change=chiudi_altro_flag, args=("reverse",))
    valore_aliquota = st.number_input("Aliquota IVA (%)", min_value=0, max_value=100, value=22, step=1) if attiva_iva else 22
    st.markdown('</div>', unsafe_allow_html=True)
    
    codice_mese = MESI_DICT[mese]
    rapportini_filtrati = [r for r in st.session_state.rapportini if str(r["data"]).split("-")[1] == codice_mese and (cliente_selezionato == "Tutti i clienti" or r["cliente"] == cliente_selezionato)]
            
    if rapportini_filtrati:
        dati_completi = []
        totale_imponibile = 0.0
        for r in rapportini_filtrati:
            prezzi_cli = st.session_state.clienti_dict.get(r["cliente"], {"prezzo_ora": 0, "prezzo_km": 0})
            tot_voce = calcola_totale_rapportino(r)
            totale_imponibile += tot_voce
            dati_completi.append({
                "Data": r["data"], "Cliente": r["cliente"], "Cantiere": r["cantiere"],
                "Ore": str(r["ore"]), "Tariffa/h": f"€ {prezzi_cli['prezzo_ora']:.2f}",
                "Km": str(r["km"]), "Tariffa/Km": f"€ {prezzi_cli['prezzo_km']:.2f}",
                "Spese Extra": f"€ {float(r['spese']):.2f}", "Totale Lordo": f"€ {tot_voce:.2f}"
            })
            
        st.dataframe(pd.DataFrame(dati_completi), use_container_width=True)
        st.markdown(f"**Totale Imponibile:** € {totale_imponibile:,.2f}")
        iva_calcolata = totale_imponibile * (valore_aliquota / 100) if attiva_iva and not reverse_charge else 0.0
        if reverse_charge: st.info("ℹ️ Regime applicato: Reverse Charge")
        elif attiva_iva: st.markdown(f"**IVA ({valore_aliquota}%):** € {iva_calcolata:,.2f}")
        st.markdown(f"## **Totale Dovuto:** € {totale_imponibile + iva_calcolata:,.2f}")
            
        col_pdf, col_pdf_note = st.columns(2)
        if PDF_AVAILABLE:
            col_pdf.download_button("📄 Esporta Tabella PDF", data=genera_pdf(dati_completi, mese, cliente_selezionato, totale_imponibile, attiva_iva, valore_aliquota, reverse_charge), file_name="report.pdf", mime='application/pdf', use_container_width=True)
            col_pdf_note.download_button("📝 Esporta Solo Note (PDF)", data=genera_pdf_note(rapportini_filtrati, mese, cliente_selezionato), file_name="note.pdf", mime='application/pdf', use_container_width=True)
    else:
        st.info("Nessun intervento trovato per questo filtro.")

elif menu == "Clienti":
    st.title("Gestione Clienti")
    with st.expander("➕ Aggiungi Nuovo Cliente", expanded=True):
        n_cliente = st.text_input("Nome Azienda / Cliente")
        c1, c2 = st.columns(2)
        p_ora = c1.number_input("Prezzo Orario (€/h)", min_value=0.0, value=40.0)
        p_km = c2.number_input("Prezzo Km (€/km)", min_value=0.0, value=0.50)
        if st.button("Salva in Anagrafica", use_container_width=True):
            if n_cliente and n_cliente not in st.session_state.clienti_dict:
                st.session_state.clienti_dict[n_cliente] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                st.success("Cliente aggiunto!")
                st.rerun()
                
    st.write("### Elenco Tariffe Clienti")
    for c, info in list(st.session_state.clienti_dict.items()):
        st.markdown(f'<div class="card"><strong>{c}</strong><br>🕒 Oraria: € {info["prezzo_ora"]:.2f}/h | 🚗 Km: € {info["prezzo_km"]:.2f}/km</div>', unsafe_allow_html=True)
        if st.button("Rimuovi", key=f"rm_{c}"):
            del st.session_state.clienti_dict[c]
            st.rerun()

# --- SIDEBAR AZIENDALE ---
st.sidebar.markdown("<br>" * 4 + "---", unsafe_allow_html=True)
st.sidebar.markdown('<div style="font-size: 11px; opacity: 0.65;"><strong>D\'ANDREA ANGELO E.C.</strong><br>Via Cesare Battisti, 9 - 25043 Breno (BS)<br>P. IVA: 04154960985</div>', unsafe_allow_html=True)
