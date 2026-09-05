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

## [?] Decisioni che aspettano te

Finché non rispondi, queste cose restano ferme. Non è pigrizia: sono scelte che
non posso prendere da solo su dati veri.

### [?] Cancellazione di un account: cosa succede al suo lavoro?

Se cancelli un utente, i lavori che aveva creato e i commenti che aveva scritto
che fine fanno? Le opzioni ragionevoli:
- **anonimizzare**: il lavoro resta, l'autore diventa "utente eliminato"
- **riassegnare**: tutto passa a un altro, che scegli al momento
- **impedire**: non si cancella un utente che ha ancora roba in giro

Serve anche decidere se è l'admin a cancellare gli altri, o ognuno se stesso
(per il GDPR conta la seconda).

### [?] Gli operatori possono organizzare riunioni?

Oggi mettere un impegno nell'agenda di un collega è riservato ad admin e
caposquadra. Va bene così, o vuoi che anche un operatore possa fissare qualcosa
con i colleghi?

### [?] Le notifiche devono arrivare anche per email?

Oggi la campanella funziona solo dentro l'app. Vuoi che assegnazioni e commenti
arrivino anche via email? (Attenzione: rischia di diventare fastidioso in fretta,
di solito si accompagna a preferenze per scegliere cosa ricevere.)

### [?] Serve una ricerca unica che attraversi tutto?

Oggi si cerca dentro un progetto o dentro una macchina. Ti servirebbe un campo
unico che cerca insieme in progetti, macchine e agenda?

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
