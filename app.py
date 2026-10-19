import io
import re
import datetime
import pytz
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Guide des Interventions",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

TZ = pytz.timezone("Africa/Tunis")
FICHIER_EXCEL = "Guide_interventions_pannes_T_2026_detaille.xlsx"
LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6q1BtDSDgVnJZFo0hOBfQJoDS6OYiub-qfQ&s"
MAINTENANCE_ICON_PATH = "unnamed.png"  # même icône que le tableau de bord réglementaire (optionnel)

COULEUR_PRESSE = {
    "Presse 4": {"principale": "#2563EB", "claire": "#DBEAFE", "fonce": "#1E3A8A"},
    "Presse 6": {"principale": "#059669", "claire": "#D1FAE5", "fonce": "#065F46"},
    "Presse 7": {"principale": "#D97706", "claire": "#FEF3C7", "fonce": "#92400E"},
}
COULEUR_DEFAUT = {"principale": "#64748B", "claire": "#F1F5F9", "fonce": "#334155"}

# Seuils de gravité (temps moyen d'arrêt, en minutes)
SEUIL_CRITIQUE = 60
SEUIL_MOYEN = 30

COL_PRESSE, COL_EQ, COL_CODE = "Presse", "Équipement", "Code"
COL_NB, COL_TPS, COL_MOY = "Nbre de pannes", "Temps d'arrêt (min)", "Temps moyen d'arrêt (min)"
COL_PANNE, COL_INTERV = "Panne", "Interventions possibles"


# ==========================================
# DONNÉES
# ==========================================
@st.cache_data(show_spinner="Chargement du guide…")
def charger_guide(chemin: str) -> pd.DataFrame:
    df = pd.read_excel(chemin, sheet_name="Guide interventions", header=3, dtype={COL_CODE: str})
    df = df.dropna(subset=[COL_PRESSE, COL_EQ, COL_PANNE]).copy()
    for c in (COL_PRESSE, COL_EQ, COL_CODE, COL_PANNE, COL_INTERV):
        df[c] = df[c].astype(str).str.strip()
    for c in (COL_NB, COL_TPS, COL_MOY):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df[COL_NB] = df[COL_NB].astype(int)
    df[COL_TPS] = df[COL_TPS].astype(int)
    return df.reset_index(drop=True)


@st.cache_data
def charger_source(chemin: str) -> str:
    """Récupère la ligne « Source / avertissement » du classeur."""
    try:
        brut = pd.read_excel(chemin, sheet_name="Guide interventions", header=None, nrows=2)
        return str(brut.iloc[1, 0])
    except Exception:
        return ""


def etapes(texte: str) -> list:
    """Découpe « 1. … \\n2. … » en liste d'étapes sans numérotation."""
    lignes = [l.strip() for l in str(texte).split("\n") if l.strip()]
    return [re.sub(r"^\d+\s*[.)]\s*", "", l) for l in lignes]


def gravite(temps_moyen: float) -> tuple:
    if temps_moyen >= SEUIL_CRITIQUE:
        return "Critique", "#DC2626", "#FEE2E2"
    if temps_moyen >= SEUIL_MOYEN:
        return "Modérée", "#D97706", "#FEF3C7"
    return "Faible", "#059669", "#D1FAE5"


def badge_presse(presse: str) -> str:
    c = COULEUR_PRESSE.get(presse, COULEUR_DEFAUT)
    return (f'<span style="background:{c["claire"]};color:{c["fonce"]};padding:2px 10px;'
            f'border-radius:999px;font-weight:700;font-size:12px;">{presse}</span>')


def fmt_duree(minutes: float) -> str:
    minutes = int(round(minutes))
    if minutes >= 60:
        return f"{minutes // 60} h {minutes % 60:02d} min"
    return f"{minutes} min"


# ==========================================
# STYLE (repris du Tableau de Bord Réglementaire)
# ==========================================
st.html("""<style>
    [data-testid="stVerticalBlockBorderBordered"]{background-color:#FFFFFF!important;border:1px solid #E2E8F0!important;border-left:5px solid #1E3A8A!important;border-radius:12px!important;box-shadow:0 4px 15px rgba(0,0,0,0.02)!important;padding:20px!important;}
    .stSelectbox label p, .stMultiSelect label p, .stTextInput label p{color:#475569!important;font-weight:600!important;font-size:13px!important;}
    div[data-baseweb="select"]{background-color:#F8FAFC!important;border:1px solid #CBD5E1!important;border-radius:8px!important;}
    div[data-baseweb="select"]>div{border:none!important;background-color:transparent!important;}
    div[data-baseweb="select"]:hover{border-color:#0EA5E9!important;background-color:#FFFFFF!important;box-shadow:0 0 0 3px rgba(14,165,233,0.12)!important;}
    div[data-testid="stTabs"] [data-baseweb="tab-list"], [data-baseweb="tab-list"], div[role="tablist"]{gap:12px!important;flex-wrap:wrap!important;border-bottom:none!important;}
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > div:not([role="tab"]),
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"]{display:none!important;height:0!important;background:transparent!important;border:none!important;}
    div[data-testid="stTabs"] button, button[data-baseweb="tab"], [role="tab"]{
        font-size:17px!important;font-weight:700!important;color:#475569!important;background-color:#FFFFFF!important;
        padding:16px 32px!important;border-radius:14px!important;border:2px solid #CBD5E1!important;
        box-shadow:0 2px 6px rgba(15,23,42,0.05)!important;transition:all 0.18s ease-in-out!important;}
    div[data-testid="stTabs"] button p, [role="tab"] p{font-size:17px!important;font-weight:700!important;color:inherit!important;}
    div[data-testid="stTabs"] button:hover, [role="tab"]:hover{color:#FFFFFF!important;background-color:#3B82F6!important;border:2px solid #1E3A8A!important;box-shadow:0 6px 14px rgba(30,58,138,0.25)!important;}
    div[data-testid="stTabs"] button[aria-selected="true"], [role="tab"][aria-selected="true"]{color:#FFFFFF!important;background-color:#1E3A8A!important;border:2px solid #1E3A8A!important;box-shadow:0 6px 16px rgba(14,165,233,0.35)!important;}
    @media (max-width: 768px){
        h1{font-size:1.7rem!important;}
        div[data-testid="stTabs"] button, [role="tab"]{font-size:13px!important;padding:10px 14px!important;}
        div[data-testid="stTabs"] button p, [role="tab"] p{font-size:13px!important;}
        div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important;}
        div[data-testid="stMetricValue"]{font-size:22px!important;}
    }
</style>""")

st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html,body,[data-testid="stAppViewContainer"],[data-testid="stSidebarView"]{font-family:'Inter',sans-serif!important;background-color:#F8FAFC!important;}
    .stButton>button, .stDownloadButton>button{background-color:#1E3A8A!important;color:white!important;border-radius:8px!important;border:none!important;font-weight:500!important;padding:10px 24px!important;white-space:nowrap!important;}
    .stDownloadButton>button:hover{background-color:#3B82F6!important;}
    div[data-testid="stTextInput"] input{background-color:#F1F5F9!important;border:1px solid #E2E8F0!important;border-radius:8px!important;padding:12px 16px!important;font-size:14px!important;color:#334155!important;}
    div[data-testid="stTextInput"] input:focus{border-color:#0EA5E9!important;box-shadow:0 0 0 3px rgba(14,165,233,0.12)!important;background-color:#FFFFFF!important;}
    div[data-testid="stMetric"]{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:14px 18px;box-shadow:0 4px 15px rgba(0,0,0,0.02);}
    div[data-testid="stExpander"]{background:#FFFFFF;border:1px solid #E2E8F0!important;border-radius:12px!important;margin-bottom:8px;}
    div[data-testid="stExpander"] summary p{font-weight:600!important;color:#0F172A!important;}
    .eq-titre{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:26px 0 10px 0;padding:12px 16px;background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid #1E3A8A;border-radius:12px;}
    .eq-titre h3{margin:0;font-size:1.1rem;font-weight:700;color:#0F172A;}
    .eq-code{font-size:12px;font-weight:700;background:#F1F5F9;color:#334155;padding:2px 10px;border-radius:6px;}
    .eq-stats{margin-left:auto;font-size:12.5px;color:#64748B;font-weight:500;}
    .chip{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700;margin-right:6px;}
    .etapes{margin:8px 0 0 0;padding:0;list-style:none;counter-reset:e;}
    .etapes li{counter-increment:e;position:relative;padding:9px 12px 9px 46px;margin-bottom:6px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;color:#1E293B;font-size:14px;line-height:1.5;}
    .etapes li::before{content:counter(e);position:absolute;left:12px;top:50%;transform:translateY(-50%);width:24px;height:24px;border-radius:50%;background:#1E3A8A;color:#fff;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center;}
    .bandeau-secu{background:#FEF3C7;border:1px solid #F59E0B;border-left:5px solid #D97706;border-radius:10px;padding:12px 16px;color:#78350F;font-size:14px;margin-bottom:14px;}
</style>""", unsafe_allow_html=True)


# ==========================================
# CHARGEMENT
# ==========================================
try:
    df = charger_guide(FICHIER_EXCEL)
except Exception as e:
    st.error(f"Impossible de lire « {FICHIER_EXCEL} » : {e}")
    st.info("Placez le fichier Excel dans le même dossier que app.py.")
    st.stop()

source_txt = charger_source(FICHIER_EXCEL)
presses = sorted(df[COL_PRESSE].unique())

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 4, 1])
    with c2:
        st.image(LOGO_URL, use_container_width=True)
    st.markdown("""<div style="text-align:center;margin-top:15px;margin-bottom:25px;">
        <h3 style="font-size:1.15rem;font-weight:700;margin-bottom:4px;color:#0F172A;">Tunisie Profilés d'Aluminium</h3>
        <p style="font-size:0.85rem;color:#64748B;margin:0;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Direction Maintenance & TN</p>
    </div>""", unsafe_allow_html=True)
    st.divider()

    st.markdown("<p style='font-weight:600;color:#334155;margin-bottom:6px;'>🔎 Filtres</p>", unsafe_allow_html=True)
    sel_presses = st.multiselect("Presse :", presses, default=presses)
    df_p = df[df[COL_PRESSE].isin(sel_presses)]

    equipements = sorted(df_p[COL_EQ].unique())
    sel_eq = st.multiselect("Équipement :", equipements, placeholder="Tous les équipements")
    recherche = st.text_input("Recherche libre :", placeholder="ex. vérin, 2463, fuite…")
    tri = st.selectbox("Trier les équipements par :", ["Temps d'arrêt total", "Nombre de pannes", "Temps moyen", "Ordre alphabétique"])
    st.divider()
    st.markdown(f"""<p style="font-size:12px;color:#64748B;text-align:center;">
        Données : arrêts 2026 · type T<br>Mis à jour le {datetime.datetime.now(TZ).strftime('%d/%m/%Y')}</p>""",
                unsafe_allow_html=True)

# Application des filtres
df_f = df_p.copy()
if sel_eq:
    df_f = df_f[df_f[COL_EQ].isin(sel_eq)]
if recherche.strip():
    mots = recherche.lower().split()
    blob = (df_f[COL_PRESSE] + " " + df_f[COL_EQ] + " " + df_f[COL_CODE] + " " + df_f[COL_PANNE] + " " + df_f[COL_INTERV]).str.lower()
    for m in mots:
        df_f = df_f[blob.loc[df_f.index].str.contains(re.escape(m), na=False)]
        blob = blob.loc[df_f.index]

# ==========================================
# EN-TÊTE
# ==========================================
col_titre, col_icone = st.columns([5, 1])
with col_titre:
    st.markdown("""<div style="width:100%;margin:10px auto 0 auto;">
    <div style="display:flex;justify-content:center;align-items:baseline;gap:8px;">
        <h1 style="font-size:2.6rem;font-weight:800;color:#0F172A;margin:0;letter-spacing:-1px;line-height:1.2;">Guide des Interventions Techniques</h1>
        <span style="font-size:0.75rem;color:#94A3B8;font-weight:400;white-space:nowrap;">v1.0.0</span>
    </div>
    <p style="text-align:center;font-size:0.85rem;color:#64748B;margin:6px auto 0 auto;line-height:1.5;max-width:800px;">Pannes de type T · Presses 4, 6 et 7 · Mégrine · 2026</p>
    <p style="text-align:center;font-size:0.75rem;color:#64748B;margin:6px auto 0 auto;">© 2026 TPR</p>
    </div>""", unsafe_allow_html=True)
with col_icone:
    try:
        st.image(MAINTENANCE_ICON_PATH, use_container_width=True)
    except Exception:
        pass

st.markdown("<br>", unsafe_allow_html=True)
onglets = st.tabs(["📖 Guide d'intervention", "📊 Synthèse & KPI", "ℹ️ Notes & sécurité"])
tab_guide, tab_kpi, tab_notes = onglets

# ==========================================
# ONGLET 1 : GUIDE
# ==========================================
with tab_guide:
    st.markdown("""<div class="bandeau-secu">⚠️ <b>Sécurité :</b> consigner (LOTO) avant toute intervention.
    Les interventions listées sont des préconisations à valider par la maintenance.</div>""", unsafe_allow_html=True)

    if df_f.empty:
        st.warning("Aucune panne ne correspond aux filtres sélectionnés.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Équipements", df_f.groupby([COL_PRESSE, COL_EQ]).ngroups)
        k2.metric("Types de pannes", len(df_f))
        k3.metric("Nombre de pannes", f"{df_f[COL_NB].sum():,}".replace(",", " "))
        k4.metric("Temps d'arrêt", fmt_duree(df_f[COL_TPS].sum()))
        st.markdown("<br>", unsafe_allow_html=True)

        # Légende de gravité
        st.markdown(f"""<p style="font-size:12.5px;color:#64748B;">Gravité selon le temps moyen d'arrêt :
            <span class="chip" style="background:#FEE2E2;color:#DC2626;">Critique ≥ {SEUIL_CRITIQUE} min</span>
            <span class="chip" style="background:#FEF3C7;color:#D97706;">Modérée ≥ {SEUIL_MOYEN} min</span>
            <span class="chip" style="background:#D1FAE5;color:#059669;">Faible</span></p>""", unsafe_allow_html=True)

        # Regroupement par (presse, équipement)
        groupes = (df_f.groupby([COL_PRESSE, COL_EQ, COL_CODE], sort=False)
                   .agg(nb=(COL_NB, "sum"), tps=(COL_TPS, "sum"), n_pannes=(COL_PANNE, "count"))
                   .reset_index())
        groupes["moy"] = (groupes["tps"] / groupes["nb"].replace(0, 1)).round(1)
        cle_tri = {"Temps d'arrêt total": ("tps", False), "Nombre de pannes": ("nb", False),
                   "Temps moyen": ("moy", False), "Ordre alphabétique": (COL_EQ, True)}[tri]
        groupes = groupes.sort_values([COL_PRESSE, cle_tri[0]], ascending=[True, cle_tri[1]])

        for presse in groupes[COL_PRESSE].unique():
            c = COULEUR_PRESSE.get(presse, COULEUR_DEFAUT)
            sous = groupes[groupes[COL_PRESSE] == presse]
            st.markdown(f"""<div style="margin:30px 0 0 0;padding:10px 18px;background:{c['fonce']};color:#fff;border-radius:12px;
                font-weight:800;font-size:1.15rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                <span>🏭 {presse}</span>
                <span style="font-weight:500;font-size:0.9rem;">{sous['nb'].sum()} pannes · {fmt_duree(sous['tps'].sum())} d'arrêt</span></div>""",
                        unsafe_allow_html=True)

            for _, g in sous.iterrows():
                st.markdown(f"""<div class="eq-titre" style="border-left-color:{c['principale']};">
                    <h3>{g[COL_EQ]}</h3><span class="eq-code">Code {g[COL_CODE]}</span>
                    <span class="eq-stats">{g['nb']} pannes · {fmt_duree(g['tps'])} · moy. {g['moy']:.0f} min</span></div>""",
                            unsafe_allow_html=True)
                lignes = df_f[(df_f[COL_PRESSE] == g[COL_PRESSE]) & (df_f[COL_EQ] == g[COL_EQ]) & (df_f[COL_CODE] == g[COL_CODE])]
                for _, r in lignes.sort_values(COL_TPS, ascending=False).iterrows():
                    lib, col_t, col_f = gravite(r[COL_MOY])
                    with st.expander(f"{r[COL_PANNE]}  —  {r[COL_NB]} × · moy. {r[COL_MOY]:.0f} min", expanded=bool(recherche.strip())):
                        st.markdown(f"""<span class="chip" style="background:{col_f};color:{col_t};">Gravité {lib}</span>
                            <span class="chip" style="background:#F1F5F9;color:#334155;">{r[COL_NB]} pannes</span>
                            <span class="chip" style="background:#F1F5F9;color:#334155;">Total {fmt_duree(r[COL_TPS])}</span>
                            <span class="chip" style="background:#F1F5F9;color:#334155;">Moyenne {r[COL_MOY]:.1f} min</span>""",
                                    unsafe_allow_html=True)
                        items = "".join(f"<li>{e}</li>" for e in etapes(r[COL_INTERV]))
                        st.markdown(f"<p style='margin:14px 0 4px 0;font-weight:700;color:#0F172A;'>🛠️ Interventions possibles</p>"
                                    f"<ol class='etapes'>{items}</ol>", unsafe_allow_html=True)

        # Export
        st.markdown("<br>", unsafe_allow_html=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            df_f.to_excel(xw, index=False, sheet_name="Guide filtré")
            ws = xw.sheets["Guide filtré"]
            for col, w in zip("ABCDEFGH", (11, 38, 14, 14, 18, 22, 42, 110)):
                ws.column_dimensions[col].width = w
        st.download_button("📥 Exporter la sélection (Excel)", buf.getvalue(),
                           file_name="guide_interventions_selection.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# ONGLET 2 : SYNTHÈSE & KPI
# ==========================================
with tab_kpi:
    d = df_p if not df_p.empty else df
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;text-align:center;'>Synthèse chiffrée des pannes techniques</p>",
                unsafe_allow_html=True)

    synth = (d.groupby(COL_PRESSE).agg(**{"Nbre de pannes": (COL_NB, "sum"), "Temps d'arrêt (min)": (COL_TPS, "sum")}).reset_index())
    synth["Temps d'arrêt (h)"] = (synth["Temps d'arrêt (min)"] / 60).round(1)
    synth["Temps moyen (min)"] = (synth["Temps d'arrêt (min)"] / synth["Nbre de pannes"]).round(1)
    synth["Part du temps d'arrêt"] = (synth["Temps d'arrêt (min)"] / synth["Temps d'arrêt (min)"].sum() * 100).round(1)

    cols = st.columns(len(synth) + 1)
    cols[0].metric("Total pannes", f"{synth['Nbre de pannes'].sum():,}".replace(",", " "))
    for col, (_, r) in zip(cols[1:], synth.iterrows()):
        col.metric(r[COL_PRESSE], f"{r['Nbre de pannes']} pannes", f"{r['Temps d\'arrêt (h)']} h d'arrêt", delta_color="off")

    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        with st.container(border=True):
            fig = px.bar(synth, x=COL_PRESSE, y="Temps d'arrêt (h)", text="Temps d'arrêt (h)",
                         color=COL_PRESSE, color_discrete_map={k: v["principale"] for k, v in COULEUR_PRESSE.items()},
                         title="Temps d'arrêt par presse (heures)")
            fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white", height=340,
                              xaxis_title=None, margin=dict(t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        with st.container(border=True):
            fig = px.pie(synth, names=COL_PRESSE, values="Temps d'arrêt (min)", hole=0.55, color=COL_PRESSE,
                         color_discrete_map={k: v["principale"] for k, v in COULEUR_PRESSE.items()},
                         title="Part du temps d'arrêt")
            fig.update_layout(height=340, paper_bgcolor="white", margin=dict(t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # Pareto des équipements
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;text-align:center;margin-top:20px;'>Équipements les plus pénalisants (Pareto)</p>",
                unsafe_allow_html=True)
    eq = (d.groupby(COL_EQ).agg(nb=(COL_NB, "sum"), tps=(COL_TPS, "sum")).reset_index().sort_values("tps", ascending=False))
    eq["moy"] = (eq["tps"] / eq["nb"]).round(1)
    eq["part"] = eq["tps"] / eq["tps"].sum()
    eq["cumul"] = eq["part"].cumsum()
    top_n = st.slider("Nombre d'équipements affichés", 5, min(25, len(eq)), min(10, len(eq)))
    top = eq.head(top_n)
    with st.container(border=True):
        fig = go.Figure()
        fig.add_bar(x=top[COL_EQ], y=top["tps"], name="Temps d'arrêt (min)", marker_color="#1E3A8A")
        fig.add_scatter(x=top[COL_EQ], y=top["cumul"] * 100, name="Cumul (%)", yaxis="y2",
                        mode="lines+markers", line=dict(color="#E34948", width=3))
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=440, margin=dict(t=20, b=10),
                          yaxis=dict(title="Minutes"), yaxis2=dict(title="Cumul (%)", overlaying="y", side="right", range=[0, 105]),
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True)
    t = top.rename(columns={COL_EQ: "Équipement", "nb": "Nbre de pannes", "tps": "Temps d'arrêt (min)", "moy": "Temps moyen (min)"})
    t.insert(0, "Rang", range(1, len(t) + 1))
    t["Part du total"] = (top["part"] * 100).round(1).astype(str) + " %"
    t["Cumul"] = (top["cumul"] * 100).round(1).astype(str) + " %"
    st.dataframe(t[["Rang", "Équipement", "Nbre de pannes", "Temps d'arrêt (min)", "Temps moyen (min)", "Part du total", "Cumul"]],
                 hide_index=True, use_container_width=True)

    # Top 10 des pannes
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;text-align:center;margin-top:20px;'>Les dix pannes qui pèsent le plus</p>",
                unsafe_allow_html=True)
    t10 = d.sort_values(COL_TPS, ascending=False).head(10).copy()
    t10["Équipement (code)"] = t10[COL_EQ] + " (" + t10[COL_CODE] + ")"
    st.dataframe(t10[[COL_PRESSE, "Équipement (code)", COL_PANNE, COL_NB, COL_TPS, COL_MOY]],
                 hide_index=True, use_container_width=True,
                 column_config={COL_TPS: st.column_config.ProgressColumn(COL_TPS, min_value=0, max_value=int(t10[COL_TPS].max()), format="%d")})

# ==========================================
# ONGLET 3 : NOTES & SÉCURITÉ
# ==========================================
with tab_notes:
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;text-align:center;'>Notes, hypothèses et consignes de sécurité</p>",
                unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### 🔒 Sécurité")
        st.markdown("- **Consigner (LOTO)** avant toute intervention.\n"
                    "- Lire et noter le défaut affiché **avant** tout réarmement.\n"
                    "- Prévenir la production avant l'arrêt d'un équipement commun (ex. compresseur).")
    with st.container(border=True):
        st.markdown("#### 📌 Source et hypothèses")
        st.markdown(source_txt or "Source : fichier « Arrêt 2026 », pannes de type T.")
        st.markdown("- Le symbole **\\*** après un code désigne un équipement **assimilé**.\n"
                    "- Les interventions sont des **préconisations** à valider par la maintenance.\n"
                    f"- Gravité : *Critique* ≥ {SEUIL_CRITIQUE} min, *Modérée* ≥ {SEUIL_MOYEN} min de temps moyen d'arrêt.")
    with st.container(border=True):
        st.markdown("#### 🗂️ Mise à jour des données")
        st.markdown(f"Remplacez le fichier **{FICHIER_EXCEL}** (feuille « Guide interventions », en-têtes en ligne 4) : "
                    "le site se met à jour automatiquement.")
