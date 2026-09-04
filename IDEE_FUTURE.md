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
- Tabella ponte utente ↔ reparto: **un utente può stare in più reparti**
  (deciso: cambiare più tardi un'assunzione del genere è un refactor pesante,
  vedi la lezione del multi-azienda più sotto).
- Riferimento facoltativo al reparto sul progetto. Senza reparto = progetto
  "generale", visibile a tutta l'azienda.

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

**Scelta importante sui "lavori" dentro le sezioni.** Non creare una lista di
lavori separata: "lavori da fare" e "lavori fatti" sono già l'entità `Lavoro`
che l'app ha, con stato, assegnatari, checklist, commenti, priorità e scadenza.
Duplicarla significherebbe avere il lavoro in due posti che non si parlano.
Quindi il lavoro guadagna un collegamento facoltativo alla sezione di macchina,
e da lì si vede filtrato per stato: quelli non ancora conclusi sono i "da fare",
quelli conclusi entrano nello storico da soli, con data e autore che già
registriamo. Lo stesso lavoro resta visibile da due angolazioni: dalla commessa
e dall'impianto.

**Le altre voci non sono lavori**, sono appunti: modifiche, analisi e
informazioni utili. Servono come entità a sé, con tipo, data, autore e testo,
così si può annotare qualcosa senza dover aprire un lavoro formale.

**Le "informazioni utili" sono un caso a parte:** non sono un evento con una
data, sono conoscenza di riferimento che resta valida (il modello del PLC, una
taratura, dove sta un manuale). Vanno tenute in evidenza in cima alla sezione,
non sepolte nella cronologia.

**Lo "storico effettivo"** è la vista cronologica completa: tutto quello che è
successo su quella macchina in ordine di tempo, senza filtri.

### 4 · Agenda

**Non è un calendario delle scadenze**, è diverso: Nik vuole **inserire i propri
impegni con data e ora** per organizzarsi gli interventi. La scadenza di un
lavoro dice "entro quando", l'impegno dice "martedì alle 9 sono da questo
cliente". Serve quindi un'entità con l'orario, perché le scadenze sono solo data.

Il calendario mostra due livelli sovrapposti: gli impegni propri e, sullo
sfondo, le scadenze dei lavori che riguardano chi guarda. Con l'interruttore fra
"i miei", "il mio reparto" e "tutta l'azienda" — ed è un'altra ragione per cui i
reparti vengono prima.

**Vincolo sui promemoria, da sapere prima di partire:** il piano gratuito di
Render addormenta il servizio dopo 15 minuti e non offre lavori programmati, per
cui un promemoria a orario non parte in modo affidabile. Tre strade: calcolare
cosa è in arrivo all'apertura dell'app (gratis, ma avvisa solo quando apri);
una GitHub Action schedulata che chiama un endpoint che manda le email (gratis,
e le Actions ci sono già per i test); oppure il piano a pagamento.

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
