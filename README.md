# CoordSync

<!-- frase di presentazione -->
CoordSync, l'applicazione web per coordinare i propri team.

## Il problema

<!-- problema, causa, soluzione -->
Nell'azienda in cui lavoravo, non avevo un modo diretto per coordinarmi con i miei colleghi. Lavoravamo sugli stessi progetti, ma dovevamo scriverci via chat o utilizzare documenti come word o excel per coordinarci.
Qui, nasce CoordSync.

## Cosa fa

Grazie a quest'applicazione, possiamo coordinare più aziende, più team, su vari progetti e lavori.
Ma non ci siamo fermati lì, abbiamo integrato un'agenda ed un sistema per differenziare ed organizzare uno storico intervento delle macchine dello stabilimento.
Avete bisogno di differenziare le utenze? CoordSync ve lo permette. Grazie ad un sistema di permessi e accessi, decidete voi chi può solo visualizzare e chi invece può creare o modificare progetti e lavori.

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

Il progetto è ancora in fase di sviluppo.

## Licenza

MIT — vedi il file [LICENSE](LICENSE).
