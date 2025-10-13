import pandas as pd 
import streamlit as st
dataset = pd.read_csv("https://www.irdx.com.br/media/uploads/paises.csv")

st.dataframe(dataset)
import plotly.express as px
fig = px.choropleth(dataset, locations=dataset ['iso3'], color=dataset ['nome'], hover_name=dataset ['nome'])
fig.update_layout(title='Mapa Coroléptico dos paises', geo_scope='world')
fig.show()
