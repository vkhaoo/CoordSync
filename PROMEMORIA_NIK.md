# Promemoria — cose che devi fare tu

Quello che non posso fare io perché richiede il pannello di Render, quello di
GitHub, o una tua decisione. Aggiornato man mano.

Legenda: **[!]** urgente o con una scadenza · **[ ]** da fare · **[?]** serve una tua risposta

---

## [x] Controlli fatti — niente da fare qui

### [x] `SECRET_KEY` su Render: c'è

Ho aggiunto un controllo all'avvio: in produzione, se la chiave di firma fosse
quella di esempio scritta nel codice, l'app si rifiuterebbe di partire (con
quella chiave, che è pubblica su GitHub, chiunque potrebbe fabbricarsi un
accesso come chiunque altro).

**Verificato dall'esterno che la chiave c'è**: il deploy successivo è andato a
buon fine e il codice nuovo è online — se la variabile fosse mancata, il
servizio non sarebbe ripartito e sarebbe rimasta su la versione precedente.

Se un domani cambi la chiave, ricordati che **tutti dovranno rifare l'accesso**:
i token vecchi non valgono più. Nient'altro.

### [x] La migrazione delle voci raggruppate è passata

`cad8fe0afe14` è in produzione: lo si vede dal fatto che il backend nuovo è
partito (le migrazioni girano prima dell'avvio, quindi se fossero fallite il
servizio non sarebbe salito). Nessuna voce di storico è stata toccata: sono
tutte rimaste dove erano, come argomenti a sé stanti.

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

### [!] Accendi i backup automatici (due segreti, cinque minuti)

Ho scritto il lavoro che li fa: `.github/workflows/backup.yml`. Ogni lunedì
notte fa un dump completo del database, lo **cifra** e lo conserva su GitHub
per 90 giorni. Finché mancano i segreti non fa niente e non dà errore.

Il dump è cifrato perché **questo repository è pubblico**, e i file prodotti
dalle Actions di un repository pubblico li può scaricare chiunque: un dump in
chiaro lì dentro vorrebbe dire pubblicare i dati dei tuoi clienti.

Su GitHub → Settings → Secrets and variables → Actions:

1. `DATABASE_URL_ESTERNO` — su Render, pagina del database, voce **External
   Database URL** (quella interna funziona solo da dentro Render).
2. `CHIAVE_BACKUP` — una frase lunga a tua scelta. **Segnatela fuori da qui**,
   in un posto che non sia GitHub: senza quella i backup non si aprono più, e
   non c'è modo di recuperarla.

Poi Actions → "Backup database" → Run workflow, per vedere che giri.

### [!] Prova a RIPRISTINARE un backup, una volta

Un backup che non hai mai ripristinato non è un backup, è una speranza. Scarica
il file dalla pagina del lavoro e, sul tuo computer:

```
gpg --decrypt --batch --passphrase "la-tua-chiave" coordsync-2026-09-05.sql.gpg > ripristino.sql
psql "URL-di-un-database-vuoto" -f ripristino.sql
```

Fallo una volta a freddo, adesso che non serve. Il giorno che servirà davvero
non sarà il momento di scoprire che il comando non funziona.

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

Migrazioni pubblicate finora (15). Le ultime:
- `2bd91f251225` — appartenenze, un utente in più aziende (**sposta dati**:
  ogni utente diventa membro della sua azienda. Se nei log non compare, gli
  accessi si rompono per tutti: guardala)
- `cad8fe0afe14` — voci macchina raggruppate per argomento (**pubblicata oggi**:
  è quella da controllare nei log del prossimo deploy)
- `dcbc9794f0d1` — progetti e macchine su più reparti (**sposta dati**)
- `085f69855d88` — impegni con più partecipanti (**sposta dati**)
- `c9dcce1d867a` — notifiche in-app

### [ ] Gli avvisi di `npm audit` (solo strumenti di sviluppo)

Installando i test dell'interfaccia, `npm audit` segnala 5 vulnerabilità su
**vite** e **vitest**. Riguardano il server di sviluppo e l'interfaccia grafica
dei test: **non finiscono nel sito pubblicato**, che contiene solo il tuo
codice compilato. Il rischio pratico è per il tuo computer mentre tieni aperto
`npm run dev`.

Si chiuderebbero passando a vite 7, che però **richiede Node 20.19 o più
recente**: se quello di Render fosse più vecchio, il deploy del sito
smetterebbe di funzionare. Non l'ho fatto per non rischiare la produzione per
un problema che sta solo in locale.

Se vuoi chiuderlo: su Render → Static Site → Environment aggiungi
`NODE_VERSION` = `20.19.0` (o `22`), verifica che il deploy passi, e poi dimmelo
che aggiorno vite.

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
