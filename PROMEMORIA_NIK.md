# Promemoria — cose che devi fare tu

Quello che non posso fare io perché richiede il pannello di Render, quello di
GitHub, o una tua decisione. Aggiornato man mano.

Legenda: **[!]** urgente o con una scadenza · **[ ]** da fare · **[?]** serve una tua risposta

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

### [ ] Promemoria dell'agenda via email

Il codice c'è ma **è inerte di proposito**: finché non fai questi passi non manda
niente e non dà errore.

1. Scegli una frase lunga e casuale (30+ caratteri) come chiave.
2. **Su Render** → backend → Environment: aggiungi `CHIAVE_PROMEMORIA` con quella
   frase. Verifica che ci sia anche `FRONTEND_URL`.
3. **Su GitHub** → Settings → Secrets and variables → Actions → New repository secret:
   - `CHIAVE_PROMEMORIA` — la stessa frase
   - `URL_BACKEND` — l'indirizzo del backend (es. `https://...onrender.com`)
4. Vai in Actions → "Promemoria agenda" → Run workflow, per provarla subito.

Istruzioni più estese in testa a `.github/workflows/promemoria.yml`.

---

## [ ] Da verificare quando hai un minuto

### [ ] Il comando di build del frontend su Render

Serve a me per poterti togliere dal repository i **2267 file di `node_modules`**
che ora sono versionati (appesantiscono tutto e sporcano ogni commit).

Vai su Render → il tuo Static Site → Settings → **Build Command** e dimmi cosa
c'è scritto. Se contiene `npm install` (o `npm ci`), posso toglierli senza
rischi. Se c'è solo `npm run build`, toglierli **spaccherebbe il deploy**.

### [ ] Controlla i log dopo un deploy con migrazione

Ogni volta che pubblico una migrazione te lo scrivo. Nei log del backend su
Render deve comparire una riga `Running upgrade ... -> ...`. Se non c'è, la
migrazione non è passata e il resto non funzionerà.

Migrazioni pubblicate finora (13). Le ultime:
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

1. Vai su sentry.io, crea un account gratuito e un progetto di tipo **Python**.
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
| Cancellazione di un account | **Anonimizza l'autore**: il lavoro resta, il nome diventa "utente eliminato" |
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
