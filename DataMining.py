# dashboard_jeunes_diplomes.py
# ------------------------------------------------------------
# Dashboard interactif pour 1000 jeunes diplômés sud-africains
# - Filtres globaux connectés à tout le dashboard
# - Rafraîchissement périodique (optionnel)
# - Onglets par thème : Profil, Emploi, Compétences, Mobilité
# - Nuage de mots dynamique (sur données filtrées)
# - Export CSV des données filtrées (pas d'affichage de table)
# - Formulaire d'ajout avec mise à jour CSV + st.rerun()
# - Palette de couleurs & style personnalisés
# ------------------------------------------------------------

import os, re
from collections import Counter

import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

# Optionnels (recommandés)
try:
    from wordcloud import WordCloud
    WORDCLOUD_OK = True
except Exception:
    WORDCLOUD_OK = False

# Rafraîchissement : on tente d'utiliser streamlit-extras si présent
try:
    from streamlit_extras.st_autorefresh import st_autorefresh
    EXTRAS_OK = True
except Exception:
    EXTRAS_OK = False

st.set_page_config(page_title="Dashboard Jeunes Diplômés – Afrique du Sud", layout="wide", initial_sidebar_state="expanded")

# -------------------------------
# Palette & thème graphiques (PERSONNALISÉS)
# -------------------------------
PALETTE = [
    "#3366CC",  # bleu
    "#DC3912",  # rouge
    "#FF9900",  # orange
    "#109618",  # vert
    "#990099",  # violet
    "#0099C6",  # cyan
    "#DD4477",  # rose
    "#66AA00",  # vert clair
    "#B82E2E",  # bordeaux
    "#316395"   # bleu foncé
]
C_SCALE = [
    "#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#C6F1E7"
]

# Appliquer par défaut à tous les graphiques Plotly Express
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = PALETTE

# -------------------------------
# Styles (CSS)
# -------------------------------
st.markdown("""
<style>
/* Fond global doux */
.stApp {
  background: linear-gradient(180deg, #0b1220 0%, #0e1526 60%, #0f172a 100%);
}
/* Section titles */
.section-title {
  margin-top: 8px;
  padding: 12px 14px;
  background: linear-gradient(90deg, #0ea5e9 0%, #6366f1 100%);
  color: #f8fafc;
  border-radius: 12px;
  font-weight: 700;
  letter-spacing: .2px;
}
/* KPI cards */
.kpi {
  background: linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(17,24,39,0.95) 100%);
  color:#e2e8f0;
  padding: 14px;
  border-radius: 14px;
  text-align:center;
  box-shadow: 0 8px 18px rgba(0,0,0,.30), inset 0 0 0 1px rgba(255,255,255,0.03);
  border: 1px solid rgba(99,102,241,0.18);
}
.kpi h3 {margin:0; font-size: 0.95rem; color:#93c5fd}
.kpi .v {font-size: 1.6rem; font-weight: 700; margin-top: 6px; color:#e5e7eb}
/* Textes et sous-titres */
h1, h2, h3, h4, h5, h6, label, .st-cf, .st-ag {
  color: #e5e7eb !important;
}
/* Panneau latéral */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
  border-right: 1px solid rgba(255,255,255,0.06);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">Dashboard – Enquête Jeunes Diplômés en recherche d\'emploi (Afrique du Sud)</div>', unsafe_allow_html=True)
st.caption("Lorsque le CSV est modifié ou qu'une réponse est ajoutée, le dashboard se recharge.")

# -------------------------------
# Paramètres & chargement
# -------------------------------
DEFAULT_PATH = "jeunes_diplomes_afrique_du_sud.csv"
csv_path = st.sidebar.text_input("Chemin du CSV (local)", value=DEFAULT_PATH)

# Rafraîchissement périodique (désactivé par défaut)
st.sidebar.header("Synchronisation")
enable_auto = st.sidebar.checkbox("Activer le rafraîchissement périodique", value=False)
interval_sec = st.sidebar.slider("Intervalle (secondes)", 5, 300, 30, help="Fréquence de synchronisation automatique.")

# Active le refresh si demandé
if enable_auto:
    if EXTRAS_OK:
        st_autorefresh(interval=interval_sec * 1000, limit=None, key="auto_refresh_key")
    else:
        st.markdown(f"<meta http-equiv='refresh' content='{interval_sec}'>", unsafe_allow_html=True)

@st.cache_data(ttl=60, show_spinner=False)
def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=cols)
    return df

def _safe_read(path: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        st.warning(f"Fichier introuvable : {path}. Placez le CSV au bon endroit.")
        st.stop()
    try:
        return _read_csv(path)
    except Exception as e:
        st.error(f"Erreur de lecture CSV : {e}")
        st.stop()

# Upload alternatif
up = st.sidebar.file_uploader("... ou déposez un CSV ici", type=["csv"])
if up is not None:
    df = pd.read_csv(up, encoding="utf-8-sig")
else:
    df = _safe_read(csv_path)

# -------------------------------
# Filtres globaux (appliqués partout)
# -------------------------------
st.sidebar.header("Filtres")
age_min, age_max = int(df["Âge"].min()), int(df["Âge"].max())
f_age = st.sidebar.slider("Âge", age_min, age_max, (age_min, age_max))
f_sexe = st.sidebar.multiselect("Sexe", sorted(df["Sexe"].dropna().unique().tolist()))
f_diplome = st.sidebar.multiselect("Diplôme", sorted(df["Diplôme"].dropna().unique().tolist()))
f_domaine = st.sidebar.multiselect("Q1 Domaine", sorted(df["Q1_Domaine"].dropna().unique().tolist()))
f_stage = st.sidebar.multiselect("Q2 Stage", sorted(df["Q2_Stage"].dropna().unique().tolist()))
f_mobilite = st.sidebar.multiselect("Q7 Mobilité", sorted(df["Q7_Mobilité"].dropna().unique().tolist()))
f_linkedin = st.sidebar.multiselect("Q10 LinkedIn", sorted(df["Q10_LinkedIn"].dropna().unique().tolist()))

# Application des filtres
mask = df["Âge"].between(f_age[0], f_age[1])
if f_sexe: mask &= df["Sexe"].isin(f_sexe)
if f_diplome: mask &= df["Diplôme"].isin(f_diplome)
if f_domaine: mask &= df["Q1_Domaine"].isin(f_domaine)
if f_stage: mask &= df["Q2_Stage"].isin(f_stage)
if f_mobilite: mask &= df["Q7_Mobilité"].isin(f_mobilite)
if f_linkedin: mask &= df["Q10_LinkedIn"].isin(f_linkedin)
dff = df[mask].copy()

# -------------------------------
# KPIs (basés sur dff)
# -------------------------------
col1, col2, col3, col4, col5, col6 = st.columns(6)

def _fmt_float(x):
    try:
        return f"{x:,.0f}".replace(",", " ")
    except Exception:
        return "0"

nb_rep = len(dff)
avg_salary = dff["Q6_Salaire_ZAR"].mean() if nb_rep else 0
stage_rate = dff["Q2_Stage"].eq("Oui").mean() * 100 if nb_rep else 0
mob_rate = dff["Q7_Mobilité"].eq("Oui").mean() * 100 if nb_rep else 0
entre_rate = dff["Q9_Entreprenariat"].eq("Oui").mean() * 100 if nb_rep else 0
li_rate = dff["Q10_LinkedIn"].eq("Oui").mean() * 100 if nb_rep else 0

col1.markdown(f'<div class="kpi"><h3>Répondants</h3><div class="v">{nb_rep}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="kpi"><h3>Rémunération moy. (ZAR)</h3><div class="v">{_fmt_float(avg_salary)}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="kpi"><h3>Taux de stage (%)</h3><div class="v">{stage_rate:.1f}%</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="kpi"><h3>Mobilité (%)</h3><div class="v">{mob_rate:.1f}%</div></div>', unsafe_allow_html=True)
col5.markdown(f'<div class="kpi"><h3>Entrepreneuriat (%)</h3><div class="v">{entre_rate:.1f}%</div></div>', unsafe_allow_html=True)
col6.markdown(f'<div class="kpi"><h3>LinkedIn (%)</h3><div class="v">{li_rate:.1f}%</div></div>', unsafe_allow_html=True)

# -------------------------------
# Onglets
# -------------------------------
tabs = st.tabs(["Profil", "Emploi", "Compétences", "Mobilité"])

# ----- Onglet Profil -----
with tabs[0]:
    st.markdown('<div class="section-title">Profil</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Répartition par diplôme")
        vc = dff["Diplôme"].value_counts().reset_index()
        if not vc.empty:
            vc.columns = ["Diplôme", "Effectif"]
            fig = px.pie(vc, names="Diplôme", values="Effectif", hole=0.35)
            # palette déjà appliquée via px.defaults
            fig.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    with c2:
        st.subheader("Répartition par sexe")
        vsex = dff["Sexe"].value_counts().reset_index()
        if not vsex.empty:
            vsex.columns = ["Sexe", "Effectif"]
            figsx = px.bar(vsex, x="Sexe", y="Effectif", text="Effectif")
            figsx.update_traces(textposition="outside")
            figsx.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(figsx, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

# ----- Onglet Emploi -----
with tabs[1]:
    st.markdown('<div class="section-title">Emploi</div>', unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        st.subheader("Top 10 domaines souhaités (Q1)")
        dom = dff["Q1_Domaine"].value_counts().head(10).reset_index()
        dom.columns = ["Domaine", "Effectif"]
        if not dom.empty:
            fig2 = px.bar(dom, x="Domaine", y="Effectif", text="Effectif")
            fig2.update_traces(textposition="outside")
            fig2.update_layout(xaxis_tickangle=-25, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    with e2:
        st.subheader("Distribution des salaires (ZAR) – Q6")
        if not dff.empty:
            fig3 = px.histogram(dff, x="Q6_Salaire_ZAR", nbins=30)
            fig3.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    st.subheader("Candidatures hebdomadaires – Q11")
    if not dff.empty:
        fig4 = px.box(dff, y="Q11_Candidatures", points="all")
        fig4.update_layout(margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Aucune donnée après filtrage.")

    st.subheader("Nuage de mots (choisir la colonne)")
    candidates = [c for c in dff.columns if dff[c].dtype == 'object']
    if candidates:
        default_idx = candidates.index("Q1_Domaine") if "Q1_Domaine" in candidates else 0
        wc_col = st.selectbox("Colonne source du nuage", options=candidates, index=default_idx, key="wc_col_emploi")

        def extract_keywords(series, min_length=3):
            stop_words = {
                "le","de","un","une","et","en","à","dans","sur","au","aux","du","des","la","les",
                "je","tu","il","elle","nous","vous","ils","elles","est","sont","être","avoir","pour",
                "ce","cet","cette","ces","qui","quoi","dont","où","comment","pourquoi","quand",
                "avec","par","plus","moins","très","tres","bien","mal","ne","pas","se","son","sa","ses"
            }
            counter = Counter()
            for t in series.dropna().astype(str):
                txt = re.sub(r"[^\w\s]", " ", t.lower())
                txt = txt.replace("’"," ").replace("'"," ")
                for w in txt.split():
                    if len(w) >= min_length and w not in stop_words:
                        counter[w] += 1
            return counter

        if WORDCLOUD_OK and not dff.empty:
            freq = extract_keywords(dff[wc_col])
            if freq:
                # WordCloud avec colormap harmonisée
                wc = WordCloud(width=1100, height=450, background_color="white",
                               max_words=150, relative_scaling=0.5, random_state=42,
                               colormap="viridis")
                wc = wc.generate_from_frequencies(freq)
                fig_wc, ax_wc = plt.subplots(figsize=(12, 5))
                ax_wc.imshow(wc, interpolation="bilinear")
                ax_wc.axis("off")
                st.pyplot(fig_wc)
            else:
                st.info("Pas assez de texte pour générer un nuage.")
        else:
            if not WORDCLOUD_OK:
                st.info("Module wordcloud non installé. Installez-le avec: pip install wordcloud")
    else:
        st.info("Aucune colonne textuelle disponible pour le nuage de mots.")

# ----- Onglet Compétences -----
with tabs[2]:
    st.markdown('<div class="section-title">Compétences</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Niveau en informatique (Q4)")
        if not dff.empty:
            vi = dff["Q4_Informatique"].value_counts().reset_index()
            vi.columns = ["Niveau", "Effectif"]
            figi = px.bar(vi, x="Niveau", y="Effectif", text="Effectif")
            figi.update_traces(textposition="outside")
            figi.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(figi, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")
    with c2:
        st.subheader("Importance de la formation continue (Q8)")
        if not dff.empty:
            figf = px.histogram(dff, x="Q8_Formation", nbins=5)
            figf.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(figf, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    st.subheader("Usage de LinkedIn (Q10)")
    if not dff.empty:
        vli = dff["Q10_LinkedIn"].value_counts().reset_index()
        vli.columns = ["LinkedIn", "Effectif"]
        figli = px.pie(vli, names="LinkedIn", values="Effectif", hole=0.35)
        figli.update_layout(margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(figli, use_container_width=True)
    else:
        st.info("Aucune donnée après filtrage.")

# ----- Onglet Mobilité -----
with tabs[3]:
    st.markdown('<div class="section-title">Mobilité</div>', unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    with m1:
        st.subheader("Mobilité (Q7)")
        if not dff.empty:
            vm = dff["Q7_Mobilité"].value_counts().reset_index()
            vm.columns = ["Mobilité", "Effectif"]
            figm = px.pie(vm, names="Mobilité", values="Effectif", hole=0.35)
            figm.update_layout(margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(figm, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    with m2:
        st.subheader("Mobilité par diplôme")
        if not dff.empty:
            grp = dff.groupby(["Diplôme", "Q7_Mobilité"]).size().reset_index(name="Effectif")
            figmm = px.bar(grp, x="Diplôme", y="Effectif", color="Q7_Mobilité", barmode="group")
            figmm.update_layout(xaxis_tickangle=-25, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(figmm, use_container_width=True)
        else:
            st.info("Aucune donnée après filtrage.")

    st.subheader("Difficultés (Q3) × Diplôme")
    ct = pd.crosstab(dff["Q3_Difficulté"], dff["Diplôme"])
    if not ct.empty:
        ct = ct.reset_index().melt(id_vars="Q3_Difficulté", var_name="Diplôme", value_name="Effectif")
        fig5 = px.density_heatmap(ct, x="Diplôme", y="Q3_Difficulté", z="Effectif",
                                  text_auto=True, color_continuous_scale=C_SCALE)
        fig5.update_layout(margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Pas assez de données après filtrage.")

# -------------------------------
# Export (sans table)
# -------------------------------
st.markdown('<div class="section-title">Export des données filtrées</div>', unsafe_allow_html=True)
st.download_button("Télécharger les données filtrées (CSV)",
                   dff.to_csv(index=False).encode("utf-8-sig"),
                   "donnees_filtrees.csv", "text/csv")

# -------------------------------
# Ajout de réponses (optionnel)
# -------------------------------
st.markdown('<div class="section-title">Ajouter une nouvelle réponse</div>', unsafe_allow_html=True)
with st.expander("Ouvrir le formulaire d'ajout"):
    _id = int((df["ID"].max() if "ID" in df.columns else 0) + 1)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("ID (auto)", value=str(_id), disabled=True)
        age = st.number_input("Âge", 18, 60, 23)
        sexe = st.selectbox("Sexe", ["M", "F"])
        dipl = st.selectbox("Diplôme", sorted(df["Diplôme"].dropna().unique().tolist()))
        domaine = st.selectbox("Q1 Domaine", sorted(df["Q1_Domaine"].dropna().unique().tolist()))
    with c2:
        stage = st.selectbox("Q2 Stage", ["Oui", "Non"])
        diff = st.selectbox("Q3 Difficulté", sorted(df["Q3_Difficulté"].dropna().unique().tolist()))
        info = st.selectbox("Q4 Informatique", ["Faible","Moyen","Avancé"])
        langues = st.selectbox("Q5 Langues", sorted(df["Q5_Langues"].dropna().unique().tolist()))
        salaire = st.number_input("Q6 Salaire (ZAR)", 0, 100000, 12000, 500)
    with c3:
        mobilite = st.selectbox("Q7 Mobilité", ["Oui","Non"])
        form = st.slider("Q8 Formation (1-5)", 1, 5, 4)
        entre = st.selectbox("Q9 Entreprenariat", ["Oui","Non"])
        li = st.selectbox("Q10 LinkedIn", ["Oui","Non"])
        candid = st.number_input("Q11 Candidatures/sem.", 0, 100, 5, 1)
        mentor = st.selectbox("Q12 Mentorat", ["Oui","Non"])

    if st.button("Ajouter"):
        new_row = {
            "ID": _id, "Âge": age, "Sexe": sexe, "Diplôme": dipl,
            "Q1_Domaine": domaine, "Q2_Stage": stage, "Q3_Difficulté": diff, "Q4_Informatique": info,
            "Q5_Langues": langues, "Q6_Salaire_ZAR": salaire, "Q7_Mobilité": mobilite,
            "Q8_Formation": form, "Q9_Entreprenariat": entre, "Q10_LinkedIn": li,
            "Q11_Candidatures": candid, "Q12_Mentorat": mentor
        }
        try:
            base = pd.read_csv(csv_path, encoding="utf-8-sig") if os.path.isfile(csv_path) else df.copy()
            base = pd.concat([base, pd.DataFrame([new_row])], ignore_index=True)
            base.to_csv(csv_path, index=False, encoding="utf-8-sig")
            st.success("Réponse ajoutée. Le fichier CSV a été mis à jour.")
            st.rerun()
        except Exception as e:
            st.error(f"Impossible d'écrire dans le CSV ({csv_path}). Erreur : {e}")
