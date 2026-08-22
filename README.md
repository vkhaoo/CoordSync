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

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite (sviluppo) → PostgreSQL (produzione)
- **Autenticazione:** password con hashing bcrypt, token JWT
- **Test:** pytest · **CI:** GitHub Actions
- **Frontend:** React *(in sviluppo)*

## Architettura in breve

<!-- 2-4 frasi TUE su com'è organizzato: models / schemas / routers,
     il multi-tenancy (dati legati all'organizzazione), la "guardia"
     che identifica l'utente dal token. Spiegalo come lo spiegheresti
     a un collega. -->
[ come è organizzato il progetto, con parole tue ]

## Come avviarlo in locale

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Documentazione API interattiva: http://127.0.0.1:8000/docs

## Test

```bash
pytest
```

## Stato del progetto

<!-- Onesto: cosa è fatto, cosa manca. Es: backend completo con test;
     frontend in sviluppo; squadre con isolamento pianificate. -->
[ a che punto è, cosa manca ]

## Licenza

MIT — vedi il file [LICENSE](LICENSE).
