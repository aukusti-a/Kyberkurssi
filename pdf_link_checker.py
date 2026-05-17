# -*- coding: utf-8 -*-
"""
PDF Link Checker
Tämä skripti etsii PDF-tiedostoista kaikki linkit (sekä klikattavat linkit että tekstinä olevat URL-osoitteet),
tarkistaa niiden toimivuuden ja kirjoittaa raportin TXT-tiedostoon.

Asennusohje tarvittaville kirjastoille:
pip install pypdf requests
"""

import os
import re
import pypdf
import requests

def extract_links_from_pdf(pdf_path):
    """Poimii PDF-tiedostosta sekä klikattavat linkit että tekstimuotoiset URL-osoitteet."""
    links = set()
    
    try:
        reader = pypdf.PdfReader(pdf_path)
        
        for page_num, page in enumerate(reader.pages, 1):
            # 1. Poimitaan klikattavat hyper-linkit (PDF-annotaatiot)
            if "/Annots" in page:
                annots = page["/Annots"]
                if hasattr(annots, "get_object"):
                    annots = annots.get_object()
                
                for annot in annots:
                    obj = annot.get_object()
                    if obj.get("/Subtype") == "/Link" and "/A" in obj:
                        action = obj["/A"].get_object()
                        if "/URI" in action:
                            uri = action["/URI"]
                            # Varmistetaan, että kyseessä on web-linkki
                            if uri.startswith(("http://", "https://")):
                                links.add(uri)
                            
            # 2. Poimitaan tekstin seassa olevat URL-osoitteet (Regex-haku suojaksi)
            text = page.extract_text()
            if text:
                url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
                found_urls = re.findall(url_pattern, text)
                for url in found_urls:
                    # Siivotaan mahdolliset loppuvälimerkit, jotka tarttuivat mukaan
                    url = url.rstrip('.,;)][')
                    if url.startswith('www.'):
                        url = 'http://' + url
                    links.add(url)
                    
    except Exception as e:
        print(f"Virhe avattaessa tai luettaessa tiedostoa {pdf_path}: {e}")
        
    return sorted(list(links))

def check_link_status(url):
    """Tarkistaa antamasi URL-osoitteen toimivuuden HTTP-pyynnöllä."""
    # Lisätään yleinen User-Agent otsikko, jotta palvelimet eivät blokkaa pyyntöä bottina
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Käytetään ensin HEAD-pyyntöä, joka on huomattavasti nopeampi (ei lataa sivun sisältöä)
        response = requests.head(url, headers=headers, timeout=7, allow_redirects=True)
        
        # Jotkut palvelimet palauttavat HEAD-pyynnölle virheen (esim. 405 Method Not Allowed).
        # Jos näin käy, varmistetaan tilanne perinteisellä GET-pyynnöllä.
        if response.status_code >= 400:
            response = requests.get(url, headers=headers, timeout=7, allow_redirects=True)
            
        if response.status_code == 200:
            return True, f"Toimii (Status: {response.status_code})"
        else:
            return False, f"Virhekoodi (Status: {response.status_code})"
            
    except requests.exceptions.Timeout:
        return False, "Virhe: Aikakatkaisu (Timeout - sivusto ei vastannut ajoissa)"
    except requests.exceptions.ConnectionError:
        return False, "Virhe: Yhteysvirhe (Ei saatu yhteyttä palvelimeen)"
    except Exception as e:
        return False, f"Virhe: {str(e)}"

def process_pdfs_in_folder(folder_path, output_txt_path):
    """Käy läpi kansion PDF-tiedostot, kerää linkit, tarkistaa ne ja kirjoittaa raportin."""
    if not os.path.exists(folder_path):
        print(f"Virhe: Kansiota '{folder_path}' ei ole olemassa.")
        return
        
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"Huomio: Kansiosta '{folder_path}' ei löytynyt yhtään .pdf -tiedostoa.")
        return
        
    print(f"Löydettiin {len(pdf_files)} PDF-tiedostoa. Aloitetaan linkkien analysointi...")
    
    with open(output_txt_path, 'w', encoding='utf-8') as f_out:
        f_out.write("==================================================")
        f_out.write("\n          PDF LINKKIEN TARKISTUSRAPORTTI          ")
        f_out.write("\n==================================================")
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            pdf_path = os.path.join(folder_path, pdf_file)
            print(f"[{idx}/{len(pdf_files)}] Käsitellään tiedostoa: {pdf_file}")
            
            f_out.write(f"\nTiedosto: {pdf_file}")
            f_out.write("-" * (10 + len(pdf_file)) + "")
            
            links = extract_links_from_pdf(pdf_path)
            
            if not links:
                print("  - Ei löytyneitä linkkejä.")
                f_out.write("  (Ei löytyneitä linkkejä tällekään tiedostolle)")
                continue
                
            print(f"  - Löytyi {len(links)} yksilöllistä linkkiä. Tarkistetaan toimivuus...")
            
            ok_count = 0
            error_count = 0
            
            for link in links:
                is_working, status_msg = check_link_status(link)
                if is_working:
                    ok_count += 1
                    status_str = "[OK]"
                else:
                    error_count += 1
                    status_str = "[VIRHE]"
                
                f_out.write(f"  {status_str} {link} -> {status_msg}")
            
            f_out.write(f"\nYhteenveto tiedostolle {pdf_file}:")
            f_out.write(f"\n  - Toimivia linkkejä: {ok_count}")
            f_out.write(f"\n  - Rikkinäisiä/virheellisiä: {error_count}")
            f_out.write("\n" + "="*40 + "")
            
    print(f"Valmis! Raportti on tallennettu tiedostoon: {output_txt_path}")

if __name__ == "__main__":
    # KANSIO: Voit muuttaa tähän polun kansioon, jossa PDF-tiedostot sijaitsevat.
    # '.' tarkoittaa samaa kansiota, jossa tämä skripti suoritetaan.
    MÄÄRITETTY_KANSIO = "C:/Koulu/tarkistettavat_pdf"
    
    # TXT-tiedoston nimi, johon tulokset tallennetaan
    RAPORTTI_TIEDOSTO = "linkkien_tarkistusraportti.txt"
    
    process_pdfs_in_folder(MÄÄRITETTY_KANSIO, RAPORTTI_TIEDOSTO)
