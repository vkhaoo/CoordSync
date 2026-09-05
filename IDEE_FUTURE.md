# Roadmap e idee future

Documento vivo: in cima quello che è stato deciso e in che ordine, sotto il
parcheggio delle idee non ancora pianificate, in fondo quello che è già uscito.

---

## Roadmap concordata (4 settembre 2026)

L'ordine non è casuale: **i reparti vengono prima di macchine e agenda** perché
la visibilità tocca ogni query di lettura. Costruire prima le altre due
significherebbe tornare indietro a metterle in sicurezza, con più lavoro e più
rischio di lasciare un buco.

### 1 · Priorità modificabile dopo la creazione — FATTO

Il chip della priorità è diventato un menu per admin e caposquadra; per gli
operatori resta un'etichetta. Cambiandola la lista si riordina.

### 2 · Reparti e visibilità per diritti — PROSSIMO

**Il problema:** oggi l'isolamento si ferma all'azienda. Dentro
l'organizzazione tutti vedono tutto, quindi non è possibile dividere il lavoro
per reparti.

**L'impianto:**
- Nuova entità `Reparto` (appartiene all'organizzazione).
- **Tutti e tre i legami col reparto sono molti-a-molti**: un utente può stare
  in più reparti, e un progetto o una macchina possono appartenere a più
  reparti (una linea seguita sia da Automazione sia da Digitale non è di uno
  solo dei due). Senza alcun reparto = "generale", visibile a tutta l'azienda.
- Nelle query si usa `.any()` (un EXISTS) e non una join: con i legami
  multipli una join restituirebbe lo stesso progetto una volta per reparto in
  comune.

**La regola di visibilità:** l'admin vede tutta l'azienda. Gli altri vedono i
progetti dei propri reparti, più quelli generali, più quelli dove sono
assegnati a un lavoro (rete di sicurezza: non nascondere a qualcuno un lavoro
che gli è stato dato).

**Attenzione — è la modifica più delicata del progetto per la sicurezza.**
Cambia ogni query che legge dati: progetti, lavori, commenti, checklist,
assegnazioni e la lista colleghi che alimenta il menu di assegnazione. Vuole un
file di test dedicato all'isolamento fra reparti, sul modello di quello che già
protegge l'isolamento fra aziende.

**Migrazione:** deve lasciare il comportamento **identico a oggi** (nessuno
assegnato ad alcun reparto, nessun progetto con reparto), poi i reparti si
assegnano con calma dall'interfaccia. Su un'app usata sul campo, un
aggiornamento non deve far sparire progetti a nessuno senza preavviso.

### 3 · Storico macchine

**Il bisogno:** tenere traccia, per ogni macchina, di cosa è stato fatto e dei
problemi affrontati, per costruire uno storico consultabile.

**La struttura (decisa con Nik):**

```
Macchina A
└── Sezioni della macchina (Confezione, Finizione, FAZ… i nomi li decide chi la usa)
    ├── lavori da fare / lavori fatti
    ├── modifiche
    ├── analisi fatte
    └── informazioni utili
```

Le sezioni sono **create dall'utente**, testo libero: cambiano da macchina a
macchina e non possono essere un elenco fisso deciso dal codice.

**Macchina e progetto sono cose diverse** e vanno tenute separate: il progetto è
una commessa che prima o poi finisce, la macchina è un impianto che resta lì per
anni. Un lavoro può appartenere a entrambi.

**Le due parti restano separate** (deciso da Nik: "le cose non sono collegate").
Da un lato si coordina la squadra in ufficio, dall'altro si guarda la macchina e
si tiene il suo storico. Hanno vite diverse — una commessa finisce e viene
archiviata, la macchina resta lì per anni e il suo valore è la memoria che
accumula — e servono a due momenti diversi del lavoro.

Quindi la scheda macchina ha **voci proprie**, non riusa l'entità `Lavoro`. Una
voce ha un tipo (lavoro, modifica, analisi, informazione utile), e le voci di
tipo "lavoro" hanno anche uno stato (da fare / in corso / fatto). Sono
annotazioni con uno stato, non compiti da assegnare: nel momento in cui serve
assegnare qualcuno e mettere una scadenza, quello e' un lavoro di progetto.

**Ma il collegamento è possibile, non obbligatorio.** Un progetto o un lavoro può
puntare a una macchina, così la scheda mostra anche gli interventi coordinati che
l'hanno toccata. Nessuno e' costretto a collegare niente: e' un di piu' per chi
lo vuole.

**Allegati (link) su ogni scheda:** macchina, sezione, voce, progetto e lavoro
possono avere una lista di link (foto, PDF di schemi, fogli). Serve a tenere
tutto nello stesso posto.

**Le "informazioni utili" sono un caso a parte:** non sono un evento con una
data, sono conoscenza di riferimento che resta valida (il modello del PLC, una
taratura, dove sta un manuale). Vanno tenute in evidenza in cima alla sezione,
non sepolte nella cronologia.

**Lo "storico effettivo"** è la vista cronologica completa: tutto quello che è
successo su quella macchina in ordine di tempo, senza filtri.

### 4 · Agenda — FATTA

Calendario mensile con due livelli sovrapposti: gli **impegni** propri (con data
e ora, perché "martedì alle 9 sono da questo cliente" è diverso da "entro
quando") e, sullo sfondo, le **scadenze** dei lavori. Interruttore fra "i miei",
"il mio reparto" e "tutta l'azienda". Collegamenti facoltativi a lavoro e
macchina.

**Riunioni:** un impegno può avere più partecipanti, e allora è UNA cosa sola
che compare nell'agenda di tutti. Spostandola si sposta per tutti, invece di
avere copie che divergono alla prima modifica. Chi lo crea resta l'organizzatore
ed è l'unico (con chi coordina) a poterlo modificare: un invitato non deve poter
spostare la riunione agli altri. Invitare qualcuno è riservato ad admin e
caposquadra.

Le scadenze mostrate sono solo quelle dei lavori già visibili: l'agenda non è
una scorciatoia per aggirare i reparti (c'è un test apposta).

**Promemoria — resta da fare la parte che avvisa davvero.** Oggi c'è il blocco
"i tuoi prossimi 7 giorni" all'apertura dell'agenda, che funziona senza
infrastruttura, e il campo `promemoria_minuti` è già salvato sull'impegno.
Manca l'invio vero, che richiede qualcosa di sempre acceso: il piano gratuito di
Render addormenta il servizio dopo 15 minuti e non offre lavori programmati.
Due strade: una **GitHub Action schedulata** che chiama un endpoint che manda le
email (gratis, e le Actions ci sono già per i test), oppure il piano a pagamento.

### 5 · Notifiche in-app

Campanella con contatore, avviso su assegnazione e nuovo commento. Guadagna
molto se arriva dopo l'agenda, perché può avvisare anche delle scadenze vicine.

### 6 · Allegati come link

Campo link sulle voci (foto del quadro su Drive, PDF di schemi). Si sposa con lo
storico macchine, dove serve davvero. L'upload di file veri richiede uno storage
esterno: solo da prodotto maturo.

---

## Parcheggio (non ancora pianificate)

- **Sicurezza e GDPR:** cancellazione account e dati, esportazione dei propri
  dati, secondo fattore (TOTP), limite ai tentativi di accesso. Diventano
  importanti con clienti paganti veri. La parte legale (informativa, base
  giuridica) vuole una consulenza vera.
- **Token in cookie httpOnly** invece che in localStorage: più robusto contro
  XSS, ma è un intervento trasversale (CORS con credenziali, gestione lato
  backend). Da valutare quando ci saranno clienti.
- **Un utente in più aziende.** Oggi l'appartenenza è singola. Diventerebbe un
  molti-a-molti con il ruolo per azienda, più il concetto di "azienda attiva"
  nel token. Cambio strutturale, non un ritocco. Alternativa già adottata: due
  account separati.
- **Dark mode.** Tocca ogni colore. Le variabili CSS sono già pronte in `:root`,
  servirebbe un set alternativo più un interruttore che salva la preferenza.
  Nota: oggi la pagina dichiara `color-scheme: light`; quando arriverà il tema
  scuro vero quel valore diventa `light dark`.
- **Chat in tempo reale.** Richiede websocket. Rimandata: i commenti attaccati
  al singolo lavoro coordinano meglio, perché la conversazione resta legata al
  lavoro.
- **Qualità e infrastruttura:** registro errori in produzione (es. Sentry),
  backup automatici del database, gestione errori frontend più uniforme,
  dominio proprio con email dal dominio (SPF/DKIM/DMARC), piano Render a
  pagamento quando ci saranno utenti veri.

---

## Già uscite dal parcheggio

Verifica email · recupero password · servizio email reale via Brevo · gestione
utenti da interfaccia · ruoli e permessi (admin, caposquadra, operatore) ·
robustezza password · link a documento sui progetti · barra di avanzamento ·
data e autore del completamento · checklist collassabile · modifica, spostamento
ed eliminazione di lavori e progetti · restyling e responsività · inviti via
email · obbligo cambio password al primo accesso · scadenze sui lavori ·
priorità modificabile.
