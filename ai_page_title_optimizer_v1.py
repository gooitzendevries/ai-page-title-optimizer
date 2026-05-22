import streamlit as st
import pandas as pd
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# --- PAGINA CONFIGURATIE ---
st.set_page_config(page_title="SEO Page Title Optimizer", page_icon="🚀", layout="wide")

st.title("🚀 SEO Page Title Optimizer")
st.write("Upload je huidige paginatitels en Google Search Console data om AI-geoptimaliseerde titels te genereren.")

# --- SIDEBAR: INSTELLINGEN ---
st.sidebar.header("⚙️ Instellingen")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Vind je key op platform.openai.com")
nieuwe_merknaam = st.sidebar.text_input("Nieuwe Merknaam", value="MijnMerknaam", help="De merknaam die achteraan de titel moet komen")

st.sidebar.markdown("---")
st.sidebar.subheader("🚫 Rebranding Filter")
verboden_input = st.sidebar.text_area("Verboden woorden (komma-gescheiden)", value="oude-merknaam, oudeproductnaam", help="Zoekwoorden met deze termen worden eruit gefilterd")
verboden_woorden = [woord.strip().lower() for list_item in verboden_input.split(",") for woord in [list_item] if woord]

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
    url = row.get('Address', '')
    current_title = row.get('Title 1', '')
    current_h1 = row.get('H1-1', '')
    page_content = row.get('Page Content', '')
    
    if not url:
        return ["", 0, "", "", ""]
        
    page_content_snippet = str(page_content)[:3000] if pd.notna(page_content) else "Geen pagina-inhoud beschikbaar."
    top_queries = kw_dict.get(url, [])
    
    kw1 = top_queries[0] if len(top_queries) > 0 else ""
    kw2 = top_queries[1] if len(top_queries) > 1 else ""
    kw3 = top_queries[2] if len(top_queries) > 2 else ""
    keywords_context = ", ".join(top_queries) if top_queries else "Geen zoekwoorddata bekend."
    
    prompt = f"""
    Je bent een ervaren SEO-expert. Optimaliseer de Page Title (meta title) voor de volgende pagina op basis van de data en de pagina-inhoud.
    
    DATA & CONTEXT:
    - URL van de pagina: {url}
    - Huidige Titel: {current_title}
    - Huidige H1-tag: {current_h1}
    - Top 3 best presterende opgeschoonde zoekwoorden: {keywords_context}
    - Kern van de pagina-inhoud: {page_content_snippet}
    
    RANDVOORWAARDEN:
    1. De nieuwe titel MOET extreem relevant zijn voor de intentie van de pagina.
    2. Verwerk het belangrijkste zoekwoord zo ver mogelijk vooraan in de titel.
    3. Eindig de titel ALTIJD met de merknaam, bijvoorbeeld: `| Merknaam`.
    4. De TOTALE titel lengte MOET strikt tussen de 40 en 60 karakters lang zijn (absoluut maximaal 60 karakters).
    5. Output ALLEEN de nieuwe titel. Geen inleiding, geen uitleg, geen aanhalingstekens eromheen.
    6. Voorkom overmatig gebruik van hoofdletters. 
    7. Alleen de eerste woord van de pagina titel en het merknaam mag een hoofdletter bevatten.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Je bent een accurate SEO-copywriter die zich strikt aan karakterlimieten houdt."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        advies_titel = response.choices[0].message.content.strip().replace('"', '')
    except Exception:
        advies_titel = "Fout bij genereren"
        
    titel_lengte = len(advies_titel) if advies_titel != "Fout bij genereren" else 0
    return [advies_titel, titel_lengte, kw1, kw2, kw3]

# --- VERWERK KNOP & LOGICA ---
if file_titles and file_data:
    if not openai_key:
        st.warning("⚠️ Vul eerst je OpenAI API Key in de sidebar in.")
    else:
        if st.button("🚀 Start Optimalisatie", type="primary"):
            client = OpenAI(api_key=openai_key)
            
            with st.status("Data aan het verwerken...", expanded=True) as status:
                st.write("Bestanden inlezen...")
                df_titles = pd.read_csv(file_titles).fillna('')
                df_data = pd.read_csv(file_data).fillna('')
                
                # Kolomnamen opschonen
                df_titles.columns = df_titles.columns.str.strip()
                df_data.columns = df_data.columns.str.strip()
                
                st.write("GSC-data filteren op basis van rebranding regels...")
                df_data['Clicks'] = pd.to_numeric(df_data['Clicks'], errors='coerce').fillna(0)
                
                if verboden_woorden:
                    filter_condition = df_data['Query'].str.lower().str.contains('|'.join(verboden_woorden), na=False)
                    df_data = df_data[~filter_condition]
                
                # Top 3 groeperen
                df_data_sorted = df_data.sort_values(by=['Page', 'Clicks'], ascending=[True, False])
                df_top3 = df_data_sorted.groupby('Page').head(3)
                kw_dict = df_top3.groupby('Page')['Query'].apply(list).to_dict()
                
                st.write(f"OpenAI aanroepen voor {len(df_titles)} pagina's...")
                rows_to_process = list(df_titles.iterrows())
                
                # Parallel verwerken
                results = []
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # We gebruiken st.progress voor de visuele laadbalk
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
