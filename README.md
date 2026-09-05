# CoordSync

<!-- UNA FRASE che dice cosa fa l'app. Scrivila tu, tipo:
     "CoordSync è una web app per coordinare i lavori di un team tecnico:
      lista lavori con stato e priorità, organizzati per progetto, con
      commenti per comunicare e isolamento tra aziende diverse." -->
[ una frase di presentazione — scrivila tu ]

## Il problema

<!-- 2-3 frasi TUE: qual è il problema reale che risolve?
     Racconta la cosa vera: Excel condivisi per coordinarsi, chi fa cosa,
     stato dei lavori... e perché diventa scomodo. È la tua storia, ha valore. -->
[ il problema che hai vissuto e che l'app risolve ]

## Cosa fa

<!-- Elenco delle funzionalità principali. Riempi con parole tue. -->
- Registrazione azienda e login (autenticazione con token JWT)
- [ ... ]
- [ ... ]
- Isolamento multi-azienda: ogni azienda vede solo i propri dati

## Stack tecnico

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic per le migrazioni
- **Database:** SQLite (sviluppo) → PostgreSQL (produzione)
- **Autenticazione:** password con hashing bcrypt, token JWT, limite ai
  tentativi di accesso
- **Frontend:** React + Vite, senza librerie di interfaccia: CSS scritto a mano
- **Test:** pytest (246) e vitest (17) · **CI:** GitHub Actions, che a ogni
  push esegue i test, prova le migrazioni in salita e in discesa e compila il
  frontend
- **Osservabilità:** Sentry per gli errori in produzione, log per richiesta
- **In produzione:** Render (web service + static site + PostgreSQL), email via
  API HTTP Brevo, backup settimanale cifrato con una GitHub Action

## Architettura in breve

<!-- 2-4 frasi TUE su com'è organizzato: models / schemas / routers,
     il multi-tenancy (dati legati all'organizzazione), la "guardia"
     che identifica l'utente dal token. Spiegalo come lo spiegheresti
     a un collega. -->
[ come è organizzato il progetto, con parole tue ]

## Come avviarlo in locale

Backend:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head            # crea/aggiorna lo schema del database
uvicorn app.main:app --reload
```

Frontend, in un secondo terminale:

```bash
cd frontend
npm install
npm run dev
```

Documentazione API interattiva: http://127.0.0.1:8000/docs

## Test

```bash
pytest                          # backend
cd frontend && npm test         # interfaccia
```

## Stato del progetto

In produzione e usato sul campo. Backend e interfaccia sono completi per il
lavoro quotidiano: progetti e lavori con stato, priorità, scadenze, assegnazioni
e commenti; reparti con visibilità per diritti; schede macchina con storico
raggruppato per argomento; agenda con riunioni; notifiche; ricerca unica.

Quello che manca è tracciato in [IDEE_FUTURE.md](IDEE_FUTURE.md). Le cose più
grosse ancora aperte: un utente che appartiene a più aziende (oggi
l'appartenenza è singola, ed è l'assunzione su cui poggia tutto l'isolamento) e
il secondo fattore di autenticazione.

<!-- Se vuoi, aggiungi qui due righe tue su dove vuoi portarlo. -->

## Licenza

MIT — vedi il file [LICENSE](LICENSE).
