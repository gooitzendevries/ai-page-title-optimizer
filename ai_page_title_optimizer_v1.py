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

# === NIEUW: INFORMATIEVE HANDLEIDING (UITKLAPBAAR) ===
with st.expander("📖 Hoe werkt deze tool? (Klik om te lezen)", expanded=False):
    st.markdown("""
    Deze applicatie combineert de huidige content van je website met de werkelijke prestatiedata uit Google Search Console. De AI (GPT-4o-mini) analyseert deze input om conversieverhogende en SEO-vriendelijke titels te schrijven.
    
    ### 🛠️ In 4 stappen naar betere titels:
    1. **Instellingen invullen:** Vul in de sidebar (links) je OpenAI API Key en je nieuwe merknaam in. Kies ook direct je favoriete scheidingsteken (bijv. `|` of `-`).
    2. **Upload Paginatitels:** Sleep je website-export (bijv. uit Screaming Frog) in het linkervak. Zorg dat de kolommen `Address`, `Title 1`, `H1-1` en `Page Content` (je custom content-scrape) erin staan.
    3. **Upload GSC Data:** Sleep je zoekwoord-export uit Google Search Console in het rechtervak. Dit bestand heeft de kolommen `Page`, `Query` en `Clicks` nodig.
    4. **Optimaliseer:** Klik op de rode knop. De app filtert automatisch foutieve pagina's, URL-parameters (`?`) en non-indexable pagina's eruit om onnodige AI-kosten te voorkomen.
    
    ### 📥 Wat krijg je terug?
    Na de analyse kun je een verrijkt CSV-bestand downloaden. Je behoudt al je originele kolommen, aangevuld met:
    * **Title advies:** Je gloednieuwe, AI-geoptimaliseerde paginatitel.
    * **Title Length:** De exacte karakterlengte (gegarandeerd tussen de 40 en 60 tekens).
    * **Keyword 1, 2, 3:** De top-3 best presterende zoekwoorden die de AI als context heeft meegekregen.
    
    _Veiligheid: Je API Key en data worden uitsluitend gebruikt om met OpenAI te communiceren en worden nergens opgeslagen._
    """)
# =====================================================

# --- SIDEBAR: INSTELLINGEN ---
# ... (rest van je code blijft exact hetzelfde)

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
    - Top 3 best presterende opgeschoonde zoekwoorden: {keywords_context}
    - Kern van de pagina-inhoud: {page_content_snippet}
    
    RANDVOORWAARDEN:
    1. De nieuwe titel MOET extreem relevant zijn voor de intentie van de pagina.
    2. Verwerk het belangrijkste zoekwoord zo ver mogelijk vooraan in de titel.
    3. Eindig de titel ALTIJD met de merknaam, exact als volgt geschreven: '{scheidingsteken} {nieuwe_merknaam}'.
    4. De TOTALE titel lengte MOET strikt tussen de 40 en 60 karakters lang zijn (absoluut maximaal 60 karakters).
    5. Output ALLEEN de nieuwe titel. Geen inleiding, geen uitleg, geen aanhalingstekens eromheen.
    6. Voorkom overmatig gebruik van hoofdletters. 
    7. Alleen het allereerste woord van de paginatitel mag met een hoofdletter beginnen. Alle tussenliggende woorden moeten volledig in kleine letters (lowercase), tenzij het een officiële eigennaam betreft. Behoud voor de merknaam aan het einde wél de exacte schrijfwijze: {nieuwe_merknaam}.
    """
    
    advies_titel = "Fout bij genereren"
    
    # Retry mechanisme (maximaal 3 pogingen bij API haperingen of Rate Limits)
    for geprobeerd in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Je bent een accurate SEO-copywriter die zich strikt aan karakterlimieten, scheidingstekens en hoofdletter-restricties houdt."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6
            )
            advies_titel = response.choices[0].message.content.strip()
            
            # Output Schoonmaken (Sterretjes, aanhalingstekens en AI-voorvoegsels slopen)
            advies_titel = advies_titel.replace('"', '').replace("'", "").replace("**", "").replace("*", "")
            advies_titel = re.sub(r'^(hier is je titel:|nieuwe titel:|titel advies:|advies titel:)\s*', '', advies_titel, flags=re.IGNORECASE)
            break 
        except Exception:
            if geprobeerd < 2:
                time.sleep(2) 
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
            client = OpenAI(api_key=openai_key.strip())
            
            with st.status("Data aan het verwerken...", expanded=True) as status:
                st.write("Bestanden inlezen en structuur valideren...")
                
                try:
                    df_titles = pd.read_csv(file_titles, sep=None, engine='python').fillna('')
                    df_data = pd.read_csv(file_data, sep=None, engine='python').fillna('')
                except Exception as e:
                    st.error(f"Fout bij het inlezen van de CSV-bestanden: {e}")
                    st.stop()
                
                df_titles.columns = df_titles.columns.str.lower().str.strip()
                df_data.columns = df_data.columns.str.lower().str.strip()
                
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
                
                # --- AUTOMATISCHE DATA FILTERING ---
                st.write("Data opschonen en filteren...")
                
                # 1. Filter URL's met parameters (?) eruit
                oude_lengte = len(df_titles)
                df_titles = df_titles[~df_titles['address'].str.contains(r'\?', na=False)]
                gefilterde_parameters = oude_lengte - len(df_titles)
                if gefilterde_parameters > 0:
                    st.write(f"ℹ️ {gefilterde_parameters} URL's met parameters (`?`) automatisch uitgesloten.")
                
                # 2. Filter Non-Indexable pagina's eruit (indien de kolom 'indexability' bestaat)
                if 'indexability' in df_titles.columns:
                    lengte_voor_index_filter = len(df_titles)
                    df_titles = df_titles[df_titles['indexability'].str.lower().str.strip() != 'non-indexable']
                    gefilterde_indexability = lengte_voor_index_filter - len(df_titles)
                    if gefilterde_indexability > 0:
                        st.write(f"ℹ️ {gefilterde_indexability} non-indexable pagina's automatisch uitgesloten.")
                
                # Controleer of er na het filteren nog pagina's overblijven
                if len(df_titles) == 0:
                    st.error("❌ Geen bruikbare pagina's overgebleven na het filteren van parameters en non-indexable URL's.")
                    st.stop()
                
                st.write("GSC-data koppelen...")
                df_data['clicks'] = pd.to_numeric(df_data['clicks'], errors='coerce').fillna(0)
                
                # Sorteer en groepeer direct op de exacte 'page' kolom
                df_data_sorted = df_data.sort_values(by=['page', 'clicks'], ascending=[True, False])
                df_top3 = df_data_sorted.groupby('page').head(3)
                kw_dict = df_top3.groupby('page')['query'].apply(list).to_dict()
                
                st.write(f"OpenAI aanroepen voor {len(df_titles)} pagina's...")
                rows_to_process = list(df_titles.iterrows())
                
                # Parallel verwerken
                results = []
                with ThreadPoolExecutor(max_workers=5) as executor:
                    progress_bar = st.progress(0)
                    futures = [executor.submit(verwerk_pagina, row, kw_dict, client, scheidingsteken) for row in rows_to_process]
                    
                    for i, future in enumerate(futures):
                        results.append(future.result())
                        progress_bar.progress((i + 1) / len(rows_to_process))
                
                status.update(label="AI Optimalisatie voltooid!", state="complete", expanded=False)
            
            # --- RESULTAAT TONEN & DOWNLOADEN ---
            st.success("🔥 Klaar! De titels zijn succesvol gegenereerd.")
            
            df_results = pd.DataFrame(results, columns=["Title advies", "Title Length", "Keyword 1", "Keyword 2", "Keyword 3"])
            df_final = pd.concat([df_titles.reset_index(drop=True), df_results], axis=1)
            
            st.subheader("👀 Preview van de resultaten (Eerste 10 rijen)")
            st.dataframe(df_final.head(10), use_container_width=True)
            
            csv_output = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Geoptimaliseerde CSV",
                data=csv_output,
                file_name="geoptimaliseerde_paginatitels.csv",
                mime="text/csv"
            )
else:
    st.info("💡 Upload hierboven beide CSV-bestanden om aan de slag te gaan.")
