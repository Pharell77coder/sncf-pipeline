import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text
from db import engine

st.set_page_config(page_title="Observatoire TGV", page_icon="🚄", layout="wide")
st.title("🚄 Observatoire de la régularité TGV")
st.caption("Données mensuelles officielles SNCF · Comparaison par axe")

@st.cache_data(ttl=300)
def load():
    with engine().connect() as conn:
        df = pd.read_sql(text("SELECT * FROM regularity ORDER BY date, axe"), conn)
        report = conn.execute(text("SELECT report FROM ingestion_runs ORDER BY id DESC LIMIT 1")).scalar_one()
    df["date"] = pd.to_datetime(df["date"])
    return df, report

try:
    df, report = load()
except Exception:
    st.error("Données indisponibles. Vérifiez PostgreSQL et lancez le pipeline ; consultez les journaux du conteneur.")
    st.stop()

axes = st.sidebar.multiselect("Axes", sorted(df.axe.unique()), default=sorted(df.axe.unique()))
months = sorted(df.date.dt.strftime("%Y-%m").unique())
start, end = st.sidebar.select_slider("Période", options=months, value=(months[0], months[-1]))
metric = st.sidebar.selectbox("Indicateur", ["regularite_composite", "ponctualite_origine"],
    format_func=lambda x: {"regularite_composite":"Régularité composite", "ponctualite_origine":"Ponctualité à l’origine"}[x])
view = df[df.axe.isin(axes) & df.date.dt.strftime("%Y-%m").between(start, end)]
if view.empty:
    st.info("Sélectionnez au moins un axe.")
    st.stop()
latest = view.date.max()
a, b, c = st.columns(3)
a.metric("Dernier mois sélectionné", latest.strftime("%m/%Y"))
b.metric("Axes sélectionnés", len(axes))
c.metric("Observations renseignées", int(view[metric].notna().sum()))
st.plotly_chart(px.line(view, x="date", y=metric, color="axe", markers=True,
    labels={"date":"Mois", metric:"Taux (%)", "axe":"Axe"}), use_container_width=True)
st.subheader("Comparaison au dernier mois sélectionné")
st.plotly_chart(px.bar(view[view.date.eq(latest)], x="axe", y=metric,
    labels={"axe":"Axe", metric:"Taux (%)"}, range_y=[0,100]), use_container_width=True)
st.caption("Aucune moyenne nationale calculée : les volumes de trains nécessaires à une pondération ne figurent pas dans ce jeu.")
with st.expander("Données et traçabilité"):
    st.dataframe(view, hide_index=True, use_container_width=True)
    st.json(report)
st.download_button("Télécharger la sélection CSV", view.to_csv(index=False).encode("utf-8-sig"), "regularite_tgv.csv", "text/csv")
st.markdown("Source : [SNCF Open Data](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-axes/)")
st.caption("La ponctualité origine mesure les départs avec moins d’une minute de retard. La régularité composite est l’indicateur publié par SNCF ; consulter la fiche source pour sa définition et la licence.")
