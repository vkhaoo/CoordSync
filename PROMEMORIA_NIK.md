# Promemoria — cose che devi fare tu

Quello che non posso fare io perché richiede il pannello di Render, quello di
GitHub, o una tua decisione. Aggiornato man mano.

Legenda: **[!]** urgente o con una scadenza · **[ ]** da fare · **[?]** serve una tua risposta

---

## [!] Da controllare SUBITO, prima del prossimo deploy

### [!] `SECRET_KEY` deve esistere su Render

Ho aggiunto un controllo all'avvio: **se in produzione la chiave di firma è
ancora quella di esempio scritta nel codice, l'app si rifiuta di partire.**

Il motivo è serio: quella chiave firma i token di accesso ed è pubblica (sta su
GitHub). Se il backend girasse con quella, chiunque potrebbe fabbricarsi un
accesso come chiunque altro, e nessuno se ne accorgerebbe mai.

**Vai su Render → backend → Environment e verifica che `SECRET_KEY` ci sia**
(deve essere una frase lunga e casuale, non quella del codice). Se c'è, non
cambia niente e il deploy passa liscio.

Se invece il prossimo deploy fallisce con un messaggio che parla di
`SECRET_KEY`, la risposta è: non c'era, e l'app era vulnerabile fino ad ora.
Aggiungila e ripubblica. Nel frattempo resta online la versione precedente, non
vai giù.

*(Nota: cambiare la `SECRET_KEY` fa scadere tutti i token, quindi tu e i tuoi
colleghi dovrete rifare l'accesso una volta. Nient'altro.)*

---

## [!] Scadenze e cose che possono morire da sole

### [!] Il database gratuito di Render scade dopo 90 giorni

È il rischio più serio che hai, ed è silenzioso: il piano gratuito di PostgreSQL
su Render **viene cancellato** allo scadere dei 90 giorni dalla creazione. I
primi commit del progetto sono di fine agosto 2026, quindi la scadenza cade
verosimilmente **verso fine novembre 2026**.

Cosa fare, in ordine di preferenza:

1. Vai su Render → il tuo database → e **controlla la data di scadenza esatta**.
   Segnatela da qualche parte fuori da qui.
2. Prima di quella data, o passi al piano a pagamento, o fai un **dump completo**
   e lo ricrei altrove. Un dump lo fai con `pg_dump` usando l'URL esterno del
   database che Render ti mostra.
3. Anche se passi al piano a pagamento, prendi l'abitudine di un dump ogni tanto:
   un backup che non hai mai provato a ripristinare non è un backup.

### [ ] Fai un dump di prova adesso

Non aspettare la scadenza per scoprire che il comando non funziona. Fallo una
volta a freddo, apri il file, verifica che dentro ci siano i tuoi dati.

---

## [ ] Per accendere cose già consegnate

### [x] Promemoria dell'agenda via email — CHIAVE MESSA

Hai aggiunto `CHIAVE_PROMEMORIA` su Render e i due secret su GitHub. Resta solo
da **guardare che giri davvero**: GitHub → Actions → "Promemoria agenda" → Run
workflow. Deve finire verde. Se dice `503` la chiave sul backend non è arrivata
(controlla che il servizio sia stato riavviato dopo averla aggiunta); se dice
`401` le due chiavi non coincidono.

Da lì in poi parte da sola ogni quarto d'ora.

Istruzioni più estese in testa a `.github/workflows/promemoria.yml`.

---

## [ ] Da verificare quando hai un minuto

### [ ] Prova l'app "a freddo", cioè col server addormentato

Sul piano gratuito Render spegne il servizio dopo 15 minuti che nessuno lo usa,
e la prima richiesta dopo lo spegnimento puo' metterci quasi un minuto.

Ho appena cambiato il comportamento dell'app in quel momento: prima ti buttava
alla schermata di accesso (e dovevi riscrivere la password), ora resta dov'era,
mostra una striscia gialla "Il server si sta svegliando" e riprova da sola.

Per provarlo: non aprire l'app per una ventina di minuti, poi aprila e guarda.
Ti deve comparire la striscia, e dopo qualche secondo devi ritrovarti dentro
senza aver rifatto l'accesso. Se invece ti chiede di nuovo la password, dimmelo:
vuol dire che il tempo di risveglio supera i 25 secondi che ho impostato.

### [x] Il comando di build del frontend su Render — RISOLTO

È `npm install && npm run build`, quindi ho tolto dal repository i **2267 file
di `node_modules`**: Render se li riscarica da solo a ogni pubblicazione, nelle
versioni esatte fissate da `package-lock.json`. Il progetto su GitHub è passato
da 2398 file tracciati a **131**: adesso si vede il codice, non le librerie.

**Al prossimo deploy guarda i log del frontend**: deve comparire `npm install`
che scarica i pacchetti, e poi il build. Se per qualsiasi motivo fallisse, il
sito attuale resta su fino a che il nuovo build non riesce.

### [ ] Controlla i log dopo un deploy con migrazione

Ogni volta che pubblico una migrazione te lo scrivo. Nei log del backend su
Render deve comparire una riga `Running upgrade ... -> ...`. Se non c'è, la
migrazione non è passata e il resto non funzionerà.

Migrazioni pubblicate finora (14). Le ultime:
- `cad8fe0afe14` — voci macchina raggruppate per argomento (**pubblicata oggi**:
  è quella da controllare nei log del prossimo deploy)
- `dcbc9794f0d1` — progetti e macchine su più reparti (**sposta dati**)
- `085f69855d88` — impegni con più partecipanti (**sposta dati**)
- `c9dcce1d867a` — notifiche in-app

### [ ] Prova l'app come farebbe un operatore

Io la provo sempre da admin o creando utenti finti. Entra una volta con un
account `operatore` vero e guarda se quello che vede ha senso: cosa gli manca,
cosa gli avanza, cosa non capisce.

---

## [ ] Crea l'account Sentry e passami la chiave

Hai scelto Sentry (piano gratuito) per gli errori in produzione. È l'unica cosa
che manca perché funzioni: il codice è già pronto e resta **inerte** finché la
chiave non c'è.

1. Vai su sentry.io, crea un account gratuito e un progetto **Python → FastAPI**
   (se vedi solo "Python" va bene uguale: cambia solo il frammento di codice che
   Sentry ti mostra, e quel codice noi ce l'abbiamo già in `osservabilita.py`).
2. Copia il **DSN** che ti mostra (un indirizzo lungo che inizia con `https://`).
3. Su Render → backend → Environment: aggiungi `SENTRY_DSN` con quel valore.
4. Facoltativo: imposta anche `AMBIENTE` a `produzione`, così distingui gli
   errori veri da quelli che capitano mentre provi in locale.

Da quel momento, quando l'app si rompe ti arriva un'email con la riga di codice
esatta, invece di scoprirlo perché te lo dice un collega.

---

## Decisioni prese (5 settembre 2026)

Le tengo scritte qui così non si perdono e non te le richiedo.

| Domanda | Risposta |
|---|---|
| Cancellazione di un account | **Anonimizza l'autore** — FATTA: il lavoro resta, il nome diventa "Utente eliminato" |
| Su cosa lavorare | **Robustezza e visibilità** (errori, gestione guasti, test sui casi limite) |
| Piano Render | **Non ancora deciso**: non costruisco niente che dipenda dal piano a pagamento |
| Notifiche via email | **Solo per le assegnazioni**, il resto resta nella campanella |
| Errori in produzione | **Sentry**, piano gratuito |
| Operatori e riunioni | **No**: fissare impegni ad altri resta di admin e caposquadra |
| Come pubblico il lavoro | **Diretto su main**, come finora |
| Difetti fuori tema | **Li sistemo io** se è sicuro; mi fermo se rischia la produzione |

### Ancora aperta

- **Ricerca unica su tutto** (progetti + macchine + agenda insieme): messa in
  coda dopo la robustezza. Dimmi tu se la vuoi prima.

---

## Manutenzione, ogni tanto

- **Guarda i test verdi su GitHub** dopo ogni push (pallino verde accanto al commit).
- **Rinnova la chiave `SECRET_KEY`** se sospetti sia trapelata: tutti dovranno
  rifare l'accesso, ma è l'unica cosa che protegge i token.
- **Controlla lo spazio del database** ogni tanto: il piano gratuito ha un
  limite, e lo storico macchine cresce.

---

## Cose che restano tue per scelta

- **Il README**: lo scrivi tu, io faccio da editor. È la vetrina del portfolio e
  deve avere la tua voce.
- **La parte legale del GDPR** (informativa, base giuridica): serve una
  consulenza vera, non un programmatore.
- **Dominio proprio ed email dal dominio** (SPF/DKIM/DMARC): quando vorrai che
  le email non partano più da un indirizzo Gmail.
