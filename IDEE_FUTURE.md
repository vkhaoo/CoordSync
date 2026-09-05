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

**Promemoria — FATTI, ma vanno accesi.** Ci sono due livelli: il blocco "i tuoi
prossimi 7 giorni" all'apertura dell'agenda, che funziona sempre, e l'**invio
per email**, che richiede qualcosa di sempre acceso (Render gratuito dorme dopo
15 minuti e non offre lavori programmati).

La strada scelta è una **GitHub Action schedulata**
(`.github/workflows/promemoria.yml`) che ogni quarto d'ora bussa all'endpoint
`POST /agenda/promemoria/invia`. È gratis e usa GitHub, che c'è già per i test.

**Resta da fare a mano, una volta sola:** impostare `CHIAVE_PROMEMORIA` su
Render e i due secret `CHIAVE_PROMEMORIA` e `URL_BACKEND` su GitHub. Finché non
si fa, l'endpoint risponde 503 e l'azione non manda niente senza dare errore:
inerte è meglio che aperto a chiunque.

### 5 · Notifiche in-app — FATTE

Campanella con contatore nella barra. Avvisa su tre cose: **ti hanno assegnato
un lavoro**, **qualcuno ha commentato un lavoro dove sei assegnato**, **ti hanno
messo in agenda un impegno o una riunione**.

Nessuno riceve l'avviso di un gesto suo, e gli avvisi non aggiungono
visibilità: si mandano solo a chi quella cosa la può già vedere. Il testo è
salvato composto, come fotografia di un fatto avvenuto: se il lavoro viene
cancellato l'avviso resta leggibile, perde solo il collegamento.

Cliccando un avviso si va sul lavoro citato.

### 6 · Allegati come link — FATTI

Link su **macchina, sezione, voce, progetto e lavoro**. Solo link e non file
veri: il piano gratuito di Render non ha storage persistente.

### 7 · Ricerca — FATTA

Ricerca testuale nei lavori di un progetto (titolo e descrizione) e nello
storico di una macchina (titolo e testo), più un filtro sui nomi nelle colonne
di progetti e macchine quando superano i sei elementi.

La ricerca si fa nel **database**, non nel browser: uno storico cresce per anni,
e scaricarlo tutto per filtrarlo sarebbe uno spreco che peggiora col tempo. Il
campo aspetta la fine della digitazione prima di interrogare il server, così
scrivere "valvola" non fa partire sette richieste.

I caratteri jolly di LIKE (`%` e `_`) vengono neutralizzati: cercare "50%" deve
trovare la percentuale, non restituire tutto. C'è un test apposta, e un altro
che verifica che cercare non aggiri i reparti.

**Possibile seguito:** cercare anche dentro commenti e voci di checklist, e una
ricerca unica che attraversi progetti, macchine e agenda insieme.

---

## Parcheggio (non ancora pianificate)

- **Sicurezza e GDPR.** Fatti: **limite ai tentativi di accesso** (10 in 15
  minuti, per email e per indirizzo) ed **esportazione dei propri dati** (dal
  menu del proprio nome, in JSON). Restano: **cancellazione dell'account**, che
  vuole prima una decisione su cosa succede ai lavori creati e assegnati
  (riassegnare? anonimizzare l'autore?) e quindi non si può fare senza deciderlo;
  e il **secondo fattore** (TOTP), che è un capitolo a sé. La parte legale
  (informativa, base giuridica) vuole una consulenza vera.
- **Token in cookie httpOnly** invece che in localStorage: più robusto contro
  XSS, ma è un intervento trasversale (CORS con credenziali, gestione lato
  backend). Da valutare quando ci saranno clienti.
- **Un utente in più aziende.** Oggi l'appartenenza è singola. Diventerebbe un
  molti-a-molti con il ruolo per azienda, più il concetto di "azienda attiva"
  nel token. Cambio strutturale, non un ritocco. Alternativa già adottata: due
  account separati.
- ~~**Dark mode.**~~ FATTO: interruttore nel menu del proprio nome, preferenza
  salvata in questo dispositivo (sul telefono lo si può volere scuro e sul fisso
  no). Il tema si applica prima che la pagina venga dipinta, così non c'è il
  lampo di bianco al caricamento. Resta valida la protezione dal "tema scuro
  forzato" del browser: con il sistema in scuro l'app parte comunque chiara, e
  passa a scuro solo se lo si chiede.
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
