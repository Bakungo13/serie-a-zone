from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
API_KEY = os.getenv("MIO_TOKEN_SEGRETO")

app = FastAPI(title="App Serie A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def benvenuto():
    return {"messaggio": "Server in sicurezza e funzionante!"}

# ROTTA 1: CLASSIFICA
@app.get("/classifica")
def get_classifica_vera():
    url = "https://api.football-data.org/v4/competitions/SA/standings"
    headers = {"X-Auth-Token": API_KEY}
    try:
        risposta = requests.get(url, headers=headers)
        dati_grezzi = risposta.json()
        lista_squadre = dati_grezzi["standings"][0]["table"]
        classifica_pulita = []
        for riga in lista_squadre:
            classifica_pulita.append({
                "posizione": riga["position"],
                "nome": riga["team"]["name"],
                "logo": riga["team"].get("crest", ""),
                "punti": riga["points"],
                "giocate": riga["playedGames"],
                "vittorie": riga["won"],
                "pareggi": riga["draw"],
                "sconfitte": riga["lost"]
            })
        return classifica_pulita
    except Exception as e:
        return {"errore": "Errore classifica"}

# ROTTA 2A: SCARICA LOGHI
@app.get("/squadre_serie_a")
def get_loghi_squadre():
    url = "https://api.football-data.org/v4/competitions/SA/teams"
    headers = {"X-Auth-Token": API_KEY}
    try:
        risposta = requests.get(url, headers=headers)
        dati = risposta.json()
        lista_loghi = []
        for team in dati.get("teams", []):
            lista_loghi.append({
                "id": team["id"],
                "nome": team["shortName"],
                "logo": team["crest"]
            })
        return lista_loghi
    except Exception as e:
        return {"errore": "Impossibile scaricare i loghi."}

# ROTTA 2B: CERCA ROSA
@app.get("/squadre/{id_squadra}")
def get_squadra_id(id_squadra: int):
    url_rosa = f"https://api.football-data.org/v4/teams/{id_squadra}"
    headers = {"X-Auth-Token": API_KEY}
    try:
        risposta_rosa = requests.get(url_rosa, headers=headers)
        dati_rosa = risposta_rosa.json()
        giocatori_puliti = []
        for player in dati_rosa.get("squad", []):
            giocatori_puliti.append({
                "nome": player["name"],
                "ruolo": player.get("position", "N/D"),
                "nazionalita": player.get("nationality", "N/D")
            })
        return {
            "squadra": dati_rosa.get("shortName", "Squadra"),
            "logo": dati_rosa.get("crest", ""),
            "rosa": giocatori_puliti
        }
    except Exception as e:
        return {"errore": "Errore nel caricamento della rosa."}

# --- NUOVA ROTTA: CLASSIFICA MARCATORI ---
@app.get("/marcatori")
def get_marcatori():
    url = "https://api.football-data.org/v4/competitions/SA/scorers"
    headers = {"X-Auth-Token": API_KEY}
    try:
        risposta = requests.get(url, headers=headers)
        dati = risposta.json()
        lista_marcatori = []
        
        # L'API ci restituisce i "scorers" (i marcatori)
        for scorer in dati.get("scorers", []):
            lista_marcatori.append({
                "giocatore": scorer["player"]["name"],
                "squadra": scorer["team"]["shortName"],
                "logo": scorer["team"]["crest"], # Riconosciamo la squadra dal logo!
                "gol": scorer.get("goals", 0),
                "assist": scorer.get("assists", 0) or 0, # Se non ci sono assist, mettiamo 0
                "partite": scorer.get("playedMatches", 0) or 0
            })
        return lista_marcatori
    except Exception as e:
        return {"errore": "Errore nel caricamento dei marcatori."}

# ROTTA BOT PRONOSTICI
@app.get("/pronostico/{squadra_casa}/{squadra_trasferta}")
def calcola_pronostico(squadra_casa: str, squadra_trasferta: str):
    url = "https://api.football-data.org/v4/competitions/SA/standings"
    headers = {"X-Auth-Token": API_KEY}
    try:
        risposta = requests.get(url, headers=headers)
        dati_grezzi = risposta.json()
        lista_squadre = dati_grezzi["standings"][0]["table"]
        dati_casa = None; dati_trasferta = None

        for riga in lista_squadre:
            nome = riga["team"]["name"].lower()
            short_nome = riga["team"].get("shortName", "").lower()
            if squadra_casa.lower() in nome or squadra_casa.lower() in short_nome: dati_casa = riga
            if squadra_trasferta.lower() in nome or squadra_trasferta.lower() in short_nome: dati_trasferta = riga

        if not dati_casa or not dati_trasferta:
            return {"errore": "Squadre non trovate."}

        forma_casa_str = dati_casa.get("form", "") or ""
        forma_trasferta_str = dati_trasferta.get("form", "") or ""
        bonus_forma_casa = (forma_casa_str.count('W') * 3) + (forma_casa_str.count('D') * 1)
        bonus_forma_trasferta = (forma_trasferta_str.count('W') * 3) + (forma_trasferta_str.count('D') * 1)

        punti_casa = dati_casa["points"] + 10 + bonus_forma_casa
        punti_trasferta = dati_trasferta["points"] + 10 + bonus_forma_trasferta
        forza_totale = (punti_casa * 1.2) + punti_trasferta 
        
        return {
            "match": f"{dati_casa['team']['shortName']} vs {dati_trasferta['team']['shortName']}",
            "statistiche_attuali": {
                "forma_casa_ultime_5": forma_casa_str, "bonus_forma_casa_applicato": f"+{bonus_forma_casa}",
                "forma_trasferta_ultime_5": forma_trasferta_str, "bonus_forma_trasferta_applicato": f"+{bonus_forma_trasferta}"
            },
            "pronostico_bot": {
                "1 (Vittoria Casa)": f"{round(((punti_casa * 1.2) / forza_totale) * 75.0, 1)}%",
                "X (Pareggio)": "25.0%",
                "2 (Vittoria Trasferta)": f"{round((punti_trasferta / forza_totale) * 75.0, 1)}%"
            }
        }
    except Exception as e:
        return {"errore": "Errore Bot"}