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

# --- HOOFDPAGINA: FILE UPLOADERS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Huidige Paginatitels")
    file_titles = st.file_uploader("Upload CSV met kolommen: Address, Title 1, H1-1, Page Content", type=["csv"])

with col2:
    st.subheader("2. Google Search Console Data")
    file_data = st.file_uploader("Upload CSV met kolommen: Page, Query, Clicks", type=["csv"])

# --- DE AI VERWERKINGSFUNCTIE ---
def verwerk_pagina(row_data, kw_dict, client):
    index, row = row_data
    
    # Punt 3: Altijd forceren naar strings om type-fouten te voorkomen
    url = str(row.get('address', '')).strip()
    current_title = str(row.get('title 1', '')).strip()
    current_h1 = str(row.get('h1-1', '')).strip()
    page_content = str(row.get('page content', '')).strip()
    
    if not url or url == 'nan':
        return ["", 0, "", "", ""]
        
    page_content_snippet = page_content[:3000] if page_content and page_content != 'nan' else "Geen pagina-inhoud beschikbaar."
    top_queries = kw_dict.get(url, [])
    
    kw1 = top_queries[0] if len(top_queries) > 0 else ""
    kw2 = top_queries[1] if len(top_queries) > 1 else ""
    kw3 = top_queries[2] if len(top_queries) > 2 else ""
    keywords_context = ", ".join(top_queries) if top_queries else "Geen zoekwoorddata bekend."
    
    prompt = f"""
    Je bent een ervaren SEO-expert. Optimaliseer de Page Title (meta title) voor de volgende pagina op basis van de data en de pagina-inhoud.
    
    BELANGRIJKE CONTEXT:
    - De NIEUWE merknaam is: {nieuwe_merknaam}.
    
    DATA & CONTEXT:
    - URL van de pagina: {url}
    - Huidige Titel: {current_title}
    - Huidige H1-tag: {current_h1}
    - Top 3 best presterende opgeschoonde zoekwoorden: {keywords_context}
    - Kern van de pagina-inhoud: {page_content_snippet}
    
    RANDVOORWAARDEN:
    1. De nieuwe titel MOET extreem relevant zijn voor de intentie van de pagina.
    2. Verwerk het belangrijkste zoekwoord zo ver mogelijk vooraan in de titel.
    3. Eindig de titel ALTIJD met de merknaam, bijvoorbeeld: `| {nieuwe_merknaam}`.
    4. De TOTALE titel lengte MOET strikt tussen de 40 en 60 karakters lang zijn (absoluut maximaal 60 karakters).
    5. Output ALLEEN de nieuwe titel. Geen inleiding, geen uitleg, geen aanhalingstekens eromheen.
    6. Voorkom overmatig gebruik van hoofdletters. 
    7. Alleen het eerste woord van de pagina titel en de merknaam mag een hoofdletter bevatten. De rest van de woorden moeten volledig in kleine letters (lowercase), tenzij het een officiële eigennaam betreft.
    """
    
    advies_titel = "Fout bij genereren"
    
    # Punt 3: Retry mechanisme (maximaal 3 pogingen bij API haperingen of Rate Limits)
    for geprobeerd in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Je bent een accurate SEO-copywriter die zich strikt aan karakterlimieten en hoofdletter-restricties houdt."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6
            )
            advies_titel = response.choices[0].message.content.strip()
            
            # Punt 4: Output Schoonmaken (Sterretjes, aanhalingstekens en AI-voorvoegsels slopen)
            advies_titel = advies_titel.replace('"', '').replace("'", "").replace("**", "").replace("*", "")
            advies_titel = re.sub(r'^(hier is je titel:|nieuwe titel:|titel advies:|advies titel:)\s*', '', advies_titel, flags=re.IGNORECASE)
            break # Succes! Breek uit de retry-loop
        except Exception:
            if geprobeerd < 2:
                time.sleep(2) # Wacht 2 seconden voor de volgende poging
            else:
                advies_titel = "Fout bij genereren (API Limiet/Storing)"
        
    titel_lengte = len(advies_titel) if advies_titel not in ["Fout bij genereren", "Fout bij genereren (API Limiet/Storing)"] else 0
    return [advies_titel, titel_lengte, kw1, kw2, kw3]

# --- VERWERK KNOP & LOGICA ---
if file_titles and file_data:
    if not openai_key:
        st.warning("⚠️ Vul eerst je OpenAI API Key in de sidebar in.")
    else:
        if st.button("🚀 Start Optimalisatie", type="primary"):
            client = OpenAI(api_key=openai_key)
            
            with st.status("Data aan het verwerken...", expanded=True) as status:
                st.write("Bestanden inlezen en structuur valideren...")
                
                # Punt 1: Automatische scheidingsteken detectie (sep=None) om Excel-puntkomma fouten te voorkomen
                try:
                    df_titles = pd.read_csv(file_titles, sep=None, engine='python').fillna('')
                    df_data = pd.read_csv(file_data, sep=None, engine='python').fillna('')
                except Exception as e:
                    st.error(f"Fout bij het inlezen van de CSV-bestanden: {e}")
                    st.stop()
                
                # Punt 1: Headers opschonen naar kleine letters (lowercase & stripped)
                df_titles.columns = df_titles.columns.str.lower().str.strip()
                df_data.columns = df_data.columns.str.lower().str.strip()
                
                # Punt 1: Harde controle op verplichte kolommen
                verplichte_titels = ['address', 'title 1', 'h1-1', 'page content']
                verplichte_data = ['page', 'query', 'clicks']
                
                gemiste_titels = [col for col in verplichte_titels if col not in df_titles.columns]
                gemiste_data = [col for col in verplichte_data if col not in df_data.columns]
                
                if gemiste_titels:
                    st.error(f"❌ Kolomfout in Paginatitels CSV. Missende kolom(men): {', '.join(gemiste_titels)}")
                    st.stop()
                if gemiste_data:
                    st.error(f"❌ Kolomfout in GSC Data CSV. Missende kolom(men): {', '.join(gemiste_data)}")
                    st.stop()
                
                st.write("GSC-data verwerken...")
                df_data['clicks'] = pd.to_numeric(df_data['clicks'], errors='coerce').fillna(0)
                
                # Top 3 groeperen op basis van de opgeschoonde kleine-letter-kolommen
                df_data_sorted = df_data.sort_values(by=['page', 'clicks'], ascending=[True, False])
                df_top3 = df_data_sorted.groupby('page').head(3)
                kw_dict = df_top3.groupby('page')['query'].apply(list).to_dict()
                
                st.write(f"OpenAI aanroepen voor {len(df_titles)} pagina's...")
                rows_to_process = list(df_titles.iterrows())
                
                # Parallel verwerken
                results = []
                with ThreadPoolExecutor(max_workers=5) as executor:
                    progress_bar = st.progress(0)
                    futures = [executor.submit(verwerk_pagina, row, kw_dict, client) for row in rows_to_process]
                    
                    for i, future in enumerate(futures):
                        results.append(future.result())
                        progress_bar.progress((i + 1) / len(rows_to_process))
                
                status.update(label="AI Optimalisatie voltooid!", state="complete", expanded=False)
            
            # --- RESULTAAT TONEN & DOWNLOADEN ---
            st.success("🔥 Klaar! De titels zijn succesvol gegenereerd.")
            
            # Voeg resultaten toe aan het DataFrame
            df_results = pd.DataFrame(results, columns=["Title advies", "Title Length", "Keyword 1", "Keyword 2", "Keyword 3"])
            df_final = pd.concat([df_titles, df_results], axis=1)
            
            # Toon een preview in de app
            st.subheader("👀 Preview van de resultaten (Eerste 10 rijen)")
            st.dataframe(df_final.head(10), use_container_width=True)
            
            # Download knop maken
            csv_output = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Geoptimaliseerde CSV",
                data=csv_output,
                file_name="geoptimaliseerde_paginatitels.csv",
                mime="text/csv"
            )
else:
    st.info("💡 Upload hierboven beide CSV-bestanden om aan de slag te gaan.")
