# 1. Installeren en importeren van libraries
!pip install --upgrade openai gspread google-auth tqdm

import os
import pandas as pd
from google.colab import auth
import gspread
from google.auth import default
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor  # Voor parallel verwerken
from tqdm.notebook import tqdm                     # Voor de voortgangsbalk

print("Libraries succesvol geladen!")

# 2. Authenticatie met Google
print("Log in met je Google-account...")
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
print("Succesvol ingelogd bij Google!")

# 3. Instellingen invoeren (API sleutel & Sheet URL)
OPENAI_API_KEY = input("Plak hier je OpenAI API Key: ")
client = OpenAI(api_key=OPENAI_API_KEY)

sheet_url = input("Plak hier de volledige URL van je Google Sheet: ")

# 4. Data ophalen en voorbereiden
try:
    sh = gc.open_by_url(sheet_url)
    page_title_ws = sh.worksheet("Page title")
    data_ws = sh.worksheet("Data")

    df_titles = pd.DataFrame(page_title_ws.get_all_records())
    df_data = pd.DataFrame(data_ws.get_all_records())

    df_titles.columns = df_titles.columns.str.strip()
    df_data.columns = df_data.columns.str.strip()

    # Clicks numeriek maken
    df_data['Clicks'] = pd.to_numeric(df_data['Clicks'], errors='coerce').fillna(0)

    print("Data ingeladen. Top 3 zoekwoorden per URL vooraf berekenen...")

    # SLIMME STAP: Sorteer en pak de top 3 per URL in één keer (buiten de loop)
    df_data_sorted = df_data.sort_values(by=['Page', 'Clicks'], ascending=[True, False])
    df_top3 = df_data_sorted.groupby('Page').head(3)

    # Maak een handig 'zoekboek' (dictionary) van: { 'url': [kw1, kw2, kw3] }
    kw_dict = df_top3.groupby('Page')['Query'].apply(list).to_dict()

    print(f"Succes! 'Page title' bevat {len(df_titles)} rijen.")
    print(f"GSC Data gekoppeld voor {len(kw_dict)} unieke URL's.")

except Exception as e:
    print(f"❌ Fout bij het laden van de data: {e}")

# 5. De AI-analyse & Top-3 Keywords bepalen (Inclusief Page Content)

def verwerk_pagina(row_data):
    index, row = row_data
    url = row.get('Address', '')
    current_title = row.get('Title 1', '')
    current_h1 = row.get('H1-1', '')
    page_content = row.get('Page Content', '') # Haal de gescrapte content op

    if not url:
        return ["", 0, "", "", ""]

    # Beperk de content tot de eerste 3000 karakters (veiligheid voor token-limieten)
    page_content_snipppet = str(page_content)[:3000] if page_content else "Geen specifieke pagina-inhoud beschikbaar."

    # Haal de top-3 keywords uit ons zoekboek
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
    - Kern van de pagina-inhoud (Custom Extract): {page_content_snipppet}

    RANDVOORWAARDEN:
    1. De nieuwe titel MOET extreem relevant zijn voor de intentie van de pagina (bepaald op basis van de pagina-inhoud, huidige titel, h1 en url slug).
    2. Verwerk het belangrijkste zoekwoord zo ver mogelijk vooraan in de titel.
    3. Eindig de titel ALTIJD met de merknaam, bijvoorbeeld: `| Merknaam`.
    4. De TOTALE lengte (inclusief de merknaam) MOET strikt tussen de 40 en 60 karakters lang zijn (absoluut maximaal 60 karakters).
    5. Output ALLEEN de nieuwe titel. Geen inleiding, geen uitleg, geen aanhalingstekens eromheen.
    6. Voorkom overmatig gebruik van hoofdletters. Alleen het eerster woord van de pagina titel mag een hoofdletter bevatten.
    7. Alleen het merknaam mag hoofdletters bevatten.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Je bent een accurate SEO-copywriter die zich strikt aan karakterlimieten en de geleverde pagina-content houdt."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        advies_titel = response.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        advies_titel = "Fout bij genereren"

    titel_lengte = len(advies_titel) if advies_titel != "Fout bij genereren" else 0
    return [advies_titel, titel_lengte, kw1, kw2, kw3]


# Start parallelle verwerking
print("OpenAI aanroepen in parallelle threads met pagina-content...")
rows_to_process = list(df_titles.iterrows())

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(tqdm(executor.map(verwerk_pagina, rows_to_process), total=len(df_titles)))

print("\nAlle URL's zijn succesvol verwerkt!")

# 6. Resultaten terugschrijven naar Google Sheets (Vanaf Kolom E)
print("Resultaten wegschrijven naar Google Sheets...")

try:
    # We schrijven nu naar E1:I1 omdat kolom D in gebruik is door de content
    headers = [["Title advies", "Title Length", "Keyword 1", "Keyword 2", "Keyword 3"]]
    page_title_ws.update(range_name='E1:I1', values=headers)

    start_row = 2
    end_row = start_row + len(results) - 1
    range_to_update = f"E{start_row}:I{end_row}"

    page_title_ws.update(range_name=range_to_update, values=results)

    print("🔥 KLAAR! Je Google Sheet is succesvol geüpdatet in kolom E t/m I.")

except Exception as e:
    print(f"❌ Fout bij het wegschrijven naar de sheet: {e}")
