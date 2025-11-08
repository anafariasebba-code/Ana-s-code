# app.py
import os
import streamlit as st
import pandas as pd
from gnews import GNews
import re
from typing import List
import textwrap

# NLP & visualization
import spacy
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# For optional OpenAI or Google Gemini calls
import requests
import json

st.set_page_config(layout="wide", page_title="Monitor Político — Ana & Manuela")

# ----------------------
# Utilities
# ----------------------
@st.cache_data
def load_parlamentares(csv_path):
    df = pd.read_csv(csv_path)
    # normalize column names (lowercase, strip)
    df.columns = [c.strip().lower() for c in df.columns]
    # try to find candidate columns
    possible = [c for c in df.columns if 'nome parlamentar' in c or c == 'nome' or 'parlamentar' in c]
    if possible:
        name_col = possible[0]
    else:
        # fallback first column
        name_col = df.columns[0]
    df = df.rename(columns={name_col: 'nome'})
    return df[['nome']]

def clean_deputado_name(name: str) -> str:
    return re.sub(r'\s+', ' ', name).strip()

def fetch_news_for(name: str, max_results: int = 10) -> List[dict]:
    g = GNews(language='pt-BR', country='BR', max_results=max_results)
    query = f'"{name}"'
    items = g.get_news(query)
    # each item has title, description, url, published date
    # keep only title+description
    results = []
    for it in items:
        title = it.get('title') or ''
        desc = it.get('description') or ''
        content = f"{title}. {desc}".strip()
        results.append({
            'title': title,
            'description': desc,
            'content': content,
            'url': it.get('link') or it.get('url') or ''
        })
    return results

def build_corpus(news_items: List[dict]) -> str:
    texts = [it['content'] for it in news_items if it['content']]
    return "\n\n".join(texts)

# ----------------------
# Summarization (pluggable)
# ----------------------
def summarize_with_openai(text: str, openai_api_key: str, max_tokens: int = 300) -> str:
    """
    Usa OpenAI ChatCompletion (modo compatível). Requer OPENAI_API_KEY no ambiente.
    """
    # simple call to Chat Completions API (compatible)
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    system = "Você é um assistente que resume notícias em português focando nos fatos centrais e tópicos levantados."
    prompt = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Resuma os pontos centrais e fatos essenciais do texto abaixo em até 8 frases e liste 3 tópicos/assuntos principais:\n\n{text}"}
    ]
    payload = {
        "model": "gpt-4o-mini",  # usuário pode trocar para o modelo que tiver acesso
        "messages": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.0
    }
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro na OpenAI API: {resp.status_code} {resp.text}")
    data = resp.json()
    return data['choices'][0]['message']['content'].strip()

def summarize_with_gemini(text: str, google_api_key: str, max_output_tokens: int = 512) -> str:
    """
    Chamada simplificada para a API Generative (Gemini) do Google.
    Requer a configuração do cliente do Google ou chave em GOOGLE_API_KEY.
    Aqui fazemos uma chamada HTTP básica ao endpoint REST (exemplo).
    OBS: Dependendo da lib/versão, a forma exata pode variar — ajuste conforme sua conta.
    """
    # Este é um ponto de partida — adapte para a biblioteca oficial google.generativeai se preferir.
    url = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {google_api_key}"}
    body = {
        "prompt": {
            "text": f"Resuma os pontos centrais e fatos essenciais do texto abaixo em português em até 8 frases e liste 3 tópicos principais:\n\n{text}"
        },
        "maxOutputTokens": max_output_tokens,
        "temperature": 0.0
    }
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro Gemini API: {resp.status_code} {resp.text}")
    j = resp.json()
    # estrutura de resposta pode variar; aqui tentamos achar o texto
    if 'candidates' in j and len(j['candidates'])>0:
        return j['candidates'][0].get('content','').strip()
    # fallback: look for 'output'
    return j.get('output', {}).get('text', '').strip()

def summarize_text(text: str) -> str:
    """
    Wrapper: decide qual API usar com base em variáveis de ambiente.
    Prioridade: OPENAI_API_KEY > GOOGLE_API_KEY. Se nenhuma, retorna um resumo simplificado local (fallback).
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")
    if openai_key:
        return summarize_with_openai(text, openai_key)
    elif google_key:
        return summarize_with_gemini(text, google_key)
    else:
        # fallback local: heurístico simples (primeiras frases de cada notícia)
        lines = []
        for chunk in text.split("\n\n"):
            s = chunk.strip()
            if s:
                # take up to first 2 sentences per article chunk
                sentences = re.split(r'(?<=[.!?])\s+', s)
                lines.append(" ".join(sentences[:2]))
        short = "\n".join(lines[:8])
        return ("[Resumo local (fallback) — configure OPENAI_API_KEY ou GOOGLE_API_KEY para resumos gerativos]\n\n" +
                textwrap.shorten(short, width=1200, placeholder="..."))

# ----------------------
# Text processing & wordcloud
# ----------------------
@st.cache_resource
def load_spacy_model():
    try:
        nlp = spacy.load("pt_core_news_sm")
    except Exception:
        # If model not present, attempt download (user must run before)
        # Streamlit deployments may require pre-installing the model; here we try a fallback.
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "spacy", "download", "pt_core_news_sm"], check=False)
        nlp = spacy.load("pt_core_news_sm")
    return nlp

def process_text_for_wordcloud(text: str, deputado_name: str, nlp) -> str:
    doc = nlp(text)
    tokens = []
    deputy_parts = set([p.lower() for p in deputado_name.split()])
    for tok in doc:
        if tok.is_stop or tok.is_punct or tok.is_space:
            continue
        lemma = tok.lemma_.lower()
        if len(lemma) < 2:
            continue
        if lemma in deputy_parts:
            continue
        # filter numbers and urls
        if re.match(r'http[s]?://', lemma):
            continue
        tokens.append(lemma)
    return " ".join(tokens)

def make_wordcloud(tokens_text: str, max_words: int = 150):
    wc = WordCloud(width=800, height=400, collocations=False, max_words=max_words)
    wc.generate(tokens_text)
    fig, ax = plt.subplots(figsize=(10,4.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)

# ----------------------
# Streamlit layout
# ----------------------
st.title("Monitor Político — Avaliação 2 (Ana Luísa Sebba & Manuela Hime)")

st.sidebar.header("Configurações & Dados")
csv_file = st.sidebar.file_uploader("Envie CSV com lista de parlamentares (coluna 'nome parlamentar' ou 'nome')", type=["csv"])
uploaded_default = False
if csv_file is None:
    st.sidebar.info("Você pode enviar um CSV. Se não enviar, o app aceitará entrada manual do nome do deputado.")
else:
    df_parl = load_parlamentares(csv_file)
    st.sidebar.success(f"{len(df_parl)} nomes carregados.")

name_input = st.text_input("Digite o nome do deputado federal a pesquisar (ex.: João Silva)", value="")
max_news = st.slider("Número máximo de notícias a coletar", min_value=3, max_value=30, value=10)

col1, col2 = st.columns([2,1])

with col2:
    st.markdown("### Opções de sumarização")
    st.write("Se quiser usar um resumo gerativo (melhor qualidade), defina **OPENAI_API_KEY** ou **GOOGLE_API_KEY** nas variáveis de ambiente do ambiente onde rodar o app (veja README).")
    if os.environ.get("OPENAI_API_KEY"):
        st.write("- Usando OpenAI API.")
    elif os.environ.get("GOOGLE_API_KEY"):
        st.write("- Usando Google Generative (Gemini) API.")
    else:
        st.write("- Usando resumo local (fallback).")

with col1:
    st.markdown("### Resultado")

if st.button("Executar análise"):

    if not name_input.strip():
        st.error("Insira o nome do deputado.")
        st.stop()

    deputado = clean_deputado_name(name_input)
    with st.spinner("Coletando notícias — isso pode levar alguns segundos..."):
        news = fetch_news_for(deputado, max_results=max_news)

    if not news:
        st.warning("Nenhuma notícia encontrada para esse nome. Tente variações (ex.: incluir sobrenome completo).")
        st.stop()

    st.subheader("Notícias coletadas")
    for i, n in enumerate(news, start=1):
        st.markdown(f"**{i}. {n['title']}**  \n{n['description']}  \n[abrir notícia]({n['url']})")

    corpus = build_corpus(news)

    st.subheader("Resumo analítico (relatório textual)")
    try:
        summary = summarize_text(corpus)
        st.markdown(summary)
    except Exception as e:
        st.error(f"Erro ao resumir via API: {e}")
        st.markdown("Exibindo resumo local (trechos):")
        st.write(corpus[:2000])

    st.subheader("Word Cloud (relatório visual)")

    nlp = load_spacy_model()
    tokens_text = process_text_for_wordcloud(corpus, deputado, nlp)
    if tokens_text.strip():
        make_wordcloud(tokens_text)
    else:
        st.warning("Texto insuficiente para gerar word cloud (todos tokens filtrados).")

    st.info("Análise finalizada. Verifique as notícias e o resumo. Ajuste número de resultados se quiser maior cobertura.")
