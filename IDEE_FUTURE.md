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

### 2 · Reparti e visibilità per diritti — FATTO

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

### 3 · Storico macchine — FATTO

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

**Fatto anche:** la ricerca guarda dentro i commenti e le voci di checklist, e
la **ricerca unica** dalla barra in alto (`GET /ricerca`), che attraversa
progetti, lavori, macchine, storico e agenda insieme e riporta cinque risultati
per tipo, ognuno con scritto dove sta.

*Limite noto:* si cerca il testo com'è scritto, quindi "valvola" non trova
"valvole". Andare oltre vorrebbe dire la ricerca a tutto testo di PostgreSQL,
che in locale (SQLite) non esiste: sviluppo e produzione si comporterebbero in
modo diverso e i test smetterebbero di dire la verità.

---

---

## Appunti di interfaccia (5 settembre 2026)

Raccolti da Nik usando l'app. Il filo conduttore e' uno solo: **quello che non
serve adesso non deve stare sullo schermo**. Oggi tutto e' sempre aperto, e con
tante sezioni o tanti progetti la pagina diventa un elenco infinito.

### A · Tendine al posto degli elenchi sempre aperti — FATTO

Trasformare in menu a tendina, che si aprono premendo un pulsante:

| Dove | Cosa diventa a tendina |
|---|---|
| Lavori | l'elenco dei **progetti** nella colonna |
| Lavori | **Visibile a** (i reparti) |
| Macchine | l'elenco delle **macchine** nella colonna |
| Macchine | **Visibile a** (i reparti) |
| Macchine | le **sezioni** della macchina |

L'**Agenda va bene com'e'** e non si tocca.

*Fatto il 5 settembre 2026* con un componente solo, `Tendina.jsx`, usato in
tutti e cinque i punti. Si chiude cliccando fuori o con Esc. Il contenuto
riceve una funzione `chiudi`, così chi lo usa decide quali gesti chiudono il
menu: scegliere un progetto sì, spuntare un reparto no (quasi sempre se ne
tocca più d'uno di fila). La tendina delle sezioni raccoglie anche il riordino
e l'eliminazione: tutto quello che riguarda le sezioni sta in un posto solo.

### B · I moduli di creazione stanno dietro un pulsante — FATTO

Oggi "nuovo progetto", "nuovo lavoro" e "nuova sezione" sono sempre lì, anche
quando si sta solo guardando. Diventano voci che aprono il modulo di adesso:

- **Crea progetto** — dentro la tendina dei progetti
- **Crea lavoro** — nella schermata dei lavori
- **Crea sezione** — dentro la tendina delle sezioni, così quel menu contiene
  sia la scelta della sezione sia il modo di aggiungerne una

*Fatto il 5 settembre 2026.* Aggiunto anche il modulo della **nuova voce** di
storico, che era il blocco più ingombrante della scheda macchina e stava aperto
anche quando si leggeva soltanto. Ogni modulo ha la × per richiudersi.

### C · Ordinare le sezioni della macchina a mano — FATTO

Ogni sezione ha due frecce (‹ ›) visibili a chi gestisce la macchina; la prima
non può andare a sinistra e l'ultima a destra. Si manda al server la lista
completa degli id già riordinata, non "spostane una di uno": così il riordino è
un'operazione sola, e se i numeri d'ordine erano incasinati (tutti zero, buchi,
doppioni) il salvataggio li rimette a posto da solo. Se la lista non
corrisponde esattamente alle sezioni di quella macchina si rifiuta tutto:
meglio nessun cambiamento che un ordine salvato a metà.

Anche la creazione è cambiata: l'ordine lo decide il server e la sezione nuova
va in fondo. Prima il browser contava le sezioni per scegliere il posto, e
sbagliava appena se ne cancellava una.

### D · Raggruppare le voci per argomento — FATTO

> "Per Modifiche, Lavori, Analisi ecc. sarebbe meglio mettere tutto quello che ha
> a che fare con un argomento sotto lo stesso punto, come se fosse Progetto e
> Lavoro iniziale."

Oggi lo storico di una macchina e' un elenco piatto: l'analisi di un problema, la
modifica che l'ha risolto e il lavoro che e' servito stanno su tre righe separate
che non si sanno collegate. L'idea e' che una **voce possa contenerne altre**,
come un progetto contiene i lavori: un argomento in cima ("perdita d'aria sulla
FAZ") e sotto tutto quello che lo riguarda, in ordine di tempo.

**Fatto il 5 settembre 2026.** Le domande aperte sono state chiuse così:

| Domanda | Risposta |
|---|---|
| Quanti livelli? | **Uno solo.** Chi sta sotto qualcuno non può avere roba sotto, e chi ha già roba sotto non può diventare figlio. È la forma di progetto/lavoro, già familiare, e non diventa un labirinto |
| Una voce può cambiare argomento? | **Sì**, e può anche staccarsi e tornare da sola |
| Se si cancella l'argomento? | **Le voci sotto restano**, sciolte (`ON DELETE SET NULL`). Buttare via lo storico con un gesto solo sarebbe il danno peggiore in una scheda che vive per anni |
| L'argomento può essere di un'altra macchina? | **No** |

La migrazione aggiunge una colonna che nasce vuota: tutte le voci esistenti
restano dove sono, come argomenti a sé stanti.

### E · Piu' aziende: la schermata di scelta — FATTO

Quando arrivera' il multi-azienda (oggi in parcheggio), all'apertura dell'app
compare una **fila orizzontale scorrevole di riquadri arrotondati**, uno per
azienda, e in fondo un riquadro con il **+** per unirsi a una nuova.

E cambia anche il funzionamento degli **inviti**: se si invita un indirizzo che
ha gia' un account, invece di creare un utente nuovo gli arriva un avviso in
questa schermata; premendo il **+** puo' **accettare o rifiutare**.

*Fatto il 5 settembre 2026:* invitare un'email già registrata non dà più un
errore di conflitto — parte un invito che quella persona accetta con un clic
dalla sua casella, e allora l'azienda si aggiunge alle sue. Il cambio azienda
c'è, nel menu del proprio nome.

**Fatti anche gli inviti in attesa** (5 settembre 2026): l'invito non vive più
solo dentro un link email — è scritto, si trova nel menu del proprio nome e si
accetta o si rifiuta da lì. Finché non si accetta non apre niente e non si
compare fra i colleghi.

**Fatta anche la schermata** (5 settembre 2026), e con lei è cambiato il primo
accesso: **iscriversi e aprire un'azienda sono due gesti separati**. La
registrazione crea solo l'account; poi si apre la schermata dei riquadri, che a
chi non ha niente mostra **solo il +**. Chi arriva per invito non crea nessuna
azienda: accetta e basta.

Quando compare: sempre a chi non ha ancora un'azienda, e a richiesta dal menu
del proprio nome ("Vedi tutte a riquadri"). Chi ne ha una sola non la vede mai
— entrare dritti dentro è la cosa giusta per il 99% dei giorni.

### Come lo affronterei

Dal meno rischioso al piu' impegnativo, cosi' ogni pezzo si puo' provare da solo:

1. ~~**C** — ordinare le sezioni.~~ FATTO il 5 settembre 2026.
2. ~~**A e B insieme** — tendine e moduli nascosti.~~ FATTI il 5 settembre 2026.
3. ~~**D** — raggruppamento per argomento.~~ FATTO il 5 settembre 2026.
4. **E** — arriva da se' quando si fara' il multi-azienda.

## Parcheggio (non ancora pianificate)

- **Sicurezza e GDPR.** Fatti: **limite ai tentativi di accesso** (10 in 15
  minuti, per email e per indirizzo) ed **esportazione dei propri dati** (dal
  menu del proprio nome, in JSON). Fatta anche la **cancellazione dell'account** (deciso: anonimizzare — il lavoro
  resta alla squadra, l'identità sparisce). ~~Resta il **secondo fattore** (TOTP).~~ **FATTO** il 5 settembre 2026:
  facoltativo e spento di default, con otto codici di recupero mostrati una
  volta sola (chi perde il telefono deve avere una via d'uscita). Non si
  accende senza prima aver dimostrato che il telefono genera codici giusti. La parte legale
  (informativa, base giuridica) vuole una consulenza vera.
- **Token in cookie httpOnly** invece che in localStorage: più robusto contro
  XSS, ma è un intervento trasversale (CORS con credenziali, gestione lato
  backend) che può rompere l'accesso in produzione. È rimasta l'ultima voce
  grossa del parcheggio: da fare con calma, e con te che guardi.
- ~~**Un utente in più aziende.**~~ FATTO il 5 settembre 2026, in tre strati:
  la tessera di appartenenza (con il travaso dei dati, a comportamento
  invariato), poi l'azienda attiva nel token con il cambio azienda, poi
  l'invito a chi ha già un account. Il ruolo vale per azienda. Il selettore
  compare solo a chi ne ha più d'una.
- ~~**Dark mode.**~~ FATTO: interruttore nel menu del proprio nome, preferenza
  salvata in questo dispositivo (sul telefono lo si può volere scuro e sul fisso
  no). Il tema si applica prima che la pagina venga dipinta, così non c'è il
  lampo di bianco al caricamento. Resta valida la protezione dal "tema scuro
  forzato" del browser: con il sistema in scuro l'app parte comunque chiara, e
  passa a scuro solo se lo si chiede.
- **Chat in tempo reale.** Richiede websocket. Rimandata: i commenti attaccati
  al singolo lavoro coordinano meglio, perché la conversazione resta legata al
  lavoro.
- **Qualità e infrastruttura.** Fatti: **registro errori in produzione**
  (Sentry, inerte finché non arriva il DSN), **gestione uniforme dei guasti nel
  frontend** (attesa massima, tentativi ripetuti sulle sole letture, striscia
  "il server si sta svegliando" e nessun logout quando è solo la rete a
  mancare), **controlli in CI su migrazioni e compilazione del frontend**,
  **guardia sulla SECRET_KEY** all'avvio in produzione. Restano: **backup
  automatici del database** (oggi non ce n'è nessuno, ed è il rischio più
  serio), dominio proprio con email dal dominio (SPF/DKIM/DMARC), piano Render
  a pagamento quando ci saranno utenti veri.
- **Test del frontend.** Il backend ha 224 test, l'interfaccia zero: le
  regressioni lì si scoprono usando l'app. Servirebbe almeno una manciata di
  prove sui pezzi che fanno ragionamento (`api.js`, il calcolo delle date).

---

## Già uscite dal parcheggio

Verifica email · recupero password · servizio email reale via Brevo · gestione
utenti da interfaccia · ruoli e permessi (admin, caposquadra, operatore) ·
robustezza password · link a documento sui progetti · barra di avanzamento ·
data e autore del completamento · checklist collassabile · modifica, spostamento
ed eliminazione di lavori e progetti · restyling e responsività · inviti via
email · obbligo cambio password al primo accesso · scadenze sui lavori ·
priorità modificabile · reparti e visibilità per diritti · scheda macchina con
sezioni, voci e allegati · agenda con impegni, scadenze e riunioni · notifiche
in-app · ricerca nei lavori e nello storico · limite ai tentativi di accesso ·
esportazione dei propri dati · tema scuro · cancellazione dell'account con
anonimizzazione · email di avviso sulle assegnazioni · riordino delle sezioni
macchina · robustezza al risveglio del server.
