import streamlit as st
import pandas as pd
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import time
import re

# --- PAGINA CONFIGURATIE ---
st.set_page_config(page_title="SEO Page Title Optimizer", page_icon="🚀", layout="wide")

st.title("🚀 SEO Page Title Optimizer")
st.write("Upload je huidige paginatitels en Google Search Console data om AI-geoptimaliseerde titels te genereren.")

# --- SIDEBAR: INSTELLINGEN ---
st.sidebar.header("⚙️ Instellingen")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Vind je key op platform.openai.com")
nieuwe_merknaam = st.sidebar.text_input("Nieuwe Merknaam", value="MijnMerknaam", help="De merknaam die achteraan de titel moet komen")

# Keuzemenu voor het scheidingsteken in de sidebar
scheidingsteken = st.sidebar.radio(
    "Kies scheidingsteken voor merknaam", 
    ["|", "-", "•"], 
    index=0, 
    help="Dit teken wordt tussen de paginatitel en de merknaam geplaatst"
)

# --- HOOFDPAGINA: FILE UPLOADERS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Huidige Paginatitels")
    file_titles = st.file_uploader("Upload CSV met kolommen: Address, Title 1, H1-1, Page Content", type=["csv"])

with col2:
    st.subheader("2. Google Search Console Data")
    file_data = st.file_uploader("Upload CSV met kolommen: Page, Query, Clicks", type=["csv"])

# --- DE AI VERWERKINGSFUNCTIE ---
def verwerk_pagina(row_data, kw_dict, client, scheidingsteken):
    index, row = row_data
    
    # Altijd forceren naar strings om type-fouten te voorkomen
    url = str(row.get('address', '')).strip()
    current_title = str(row.get('title 1', '')).strip()
    current_h1 = str(row.get('h1-1', '')).strip()
    page_content = str(row.get('page content', '')).strip()
    
    if not url or url == 'nan':
        return ["", 0, "", "", ""]
        
    page_content_snippet = page_content[:3000] if page_content and page_content != 'nan' else "Geen pagina-inhoud beschikbaar."
    
    # Exacte match op basis van de originele URL
    top_queries = kw_dict.get(url, [])
    
    kw1 = top_queries[0] if len(top_queries) > 0 else ""
    kw2 = top_queries[1] if len(top_queries) > 1 else ""
    kw3 = top_queries[2] if len(top_queries) > 2 else ""
    keywords_context = ", ".join(top_queries) if top_queries else "Geen zoekwoorddata bekend."
    
    prompt = f"""
    Je bent een ervaren SEO-expert. Optimaliseer de Page Title (meta title) voor de volgende pagina op basis van de data and de pagina-inhoud.
    
    BELANGRIJKE CONTEXT:
    - De NIEUWE merknaam is exact: {nieuwe_merknaam}.
    
    DATA & CONTEXT:
    - URL van de pagina: {url}
    - Huidige Titel: {current_title}
    - Huidige H1-tag: {current_h1}
    - Top 3 best presterende opgeschoonde
