// api.js — il punto UNICO da cui il frontend parla col backend.
// Tenere le chiamate qui (invece che sparse nei componenti) e' come avere
// i router nel backend: ordine e un posto solo da cambiare se qualcosa cambia.

// L'indirizzo del backend. In locale usa il default; in produzione si imposta
// la variabile VITE_API_URL con l'indirizzo del backend online.
//
// "localhost" e non "127.0.0.1", anche se sono la stessa macchina: per i
// cookie contano come due SITI diversi, e il cookie della sessione non
// verrebbe mai allegato. La porta invece non conta, quindi localhost:5173 che
// chiama localhost:8000 e' tutto in famiglia.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// --- La sessione ----------------------------------------------------------
// Il token NON si tiene piu' qui: sta in un cookie che il browser gestisce da
// solo e che JavaScript non puo' leggere. Da questo file, quindi, la sessione
// non si vede — ed e' esattamente il punto: quello che il codice della pagina
// non puo' leggere non puo' nemmeno essere rubato da codice ostile.
//
// Resta una cosa da fare a mano: il cookie viene allegato dal browser anche
// alle richieste che partono da un altro sito, quindi per tutto quello che
// CAMBIA qualcosa si rimanda indietro un valore che si legge da un secondo
// cookie, quello si' leggibile. Un sito estraneo non riesce a leggerlo, e
// quindi non riesce a scrivere l'header.
const CHIAVE_TOKEN = "coordsync_token";

// Il token vecchio, se c'e' ancora: chi era collegato prima del cambio deve
// poter continuare a lavorare finche' non scade. Si legge una volta sola,
// all'avvio, e non se ne salvano piu' di nuovi.
let tokenVecchio = null;
try { tokenVecchio = localStorage.getItem(CHIAVE_TOKEN); } catch { }

export function setToken(t) {
  // La sessione la apre e la chiude il server, con i cookie. Qui resta solo
  // il compito di buttare via l'eventuale token vecchio.
  tokenVecchio = null;
  // Cambiando sessione cambia anche la prova anti-CSRF: si ributta, cosi' la
  // prossima scrittura se ne fa dare una nuova.
  valoreCsrf = null;
  try { localStorage.removeItem(CHIAVE_TOKEN); } catch { }
}
export function getToken() { return tokenVecchio; }

// Il valore anti-CSRF, tenuto SOLO in memoria.
//
// Non si legge da document.cookie, e qui c'e' una lezione pagata rompendo la
// produzione: le pagine stanno su un host e il backend su un altro, e un
// documento vede solo i cookie del PROPRIO host. Il cookie parte comunque
// verso il backend (lo fa il browser), ma per questo codice e' invisibile —
// quindi l'header non partiva mai e ogni scrittura tornava 403.
// In locale non si vedeva: li' e' tutto localhost, cioe' lo stesso sito.
//
// In memoria e non in localStorage: ricaricando la pagina si richiede, e cosi'
// non resta scritto da nessuna parte piu' a lungo del necessario.
let valoreCsrf = null;
// Evita rimbalzi infiniti: il recupero della prova si tenta una volta sola.
let _giaRiprovato = false;

async function assicuraCsrf() {
  if (valoreCsrf) return valoreCsrf;
  const risposta = await fetch(BASE + "/auth/csrf", { credentials: "include" });
  if (!risposta.ok) return null;
  valoreCsrf = (await risposta.json()).csrf;
  return valoreCsrf;
}

// Quanto aspettare una risposta prima di considerarla persa. Generoso di
// proposito: sul piano gratuito il servizio si addormenta dopo 15 minuti e la
// prima richiesta dopo il risveglio puo' metterci quasi un minuto.
const ATTESA_MASSIMA = 25000;
const TENTATIVI = 3;

// Chi vuole mostrare "sto svegliando il server..." si registra qui.
let avvisaRisveglio = null;
export function quandoIlServerSiSveglia(callback) { avvisaRisveglio = callback; }

// Quante richieste stanno riprovando in questo momento. E' un CONTATORE e non
// un si/no perche' la pagina lancia piu' chiamate insieme: se la prima che
// finisce spegnesse l'avviso, sparirebbe mentre le altre stanno ancora
// aspettando, e l'utente vedrebbe un lampo senza capire.
let quanteAspettano = 0;
function segnala(inPiu) {
  quanteAspettano = Math.max(0, quanteAspettano + inPiu);
  if (avvisaRisveglio) avvisaRisveglio(quanteAspettano > 0);
}

const aspetta = (ms) => new Promise((r) => setTimeout(r, ms));

async function unTentativo(metodo, percorso, corpo) {
  // AbortController: senza, una richiesta che non torna resta appesa per
  // sempre e l'utente guarda una schermata bloccata senza capire perche'.
  const stop = new AbortController();
  const timer = setTimeout(() => stop.abort(), ATTESA_MASSIMA);

  const headers = { "Content-Type": "application/json" };
  // Solo per chi ha ancora in tasca un token del vecchio modo.
  if (tokenVecchio) headers["Authorization"] = `Bearer ${tokenVecchio}`;
  // La prova anti-CSRF serve solo a quello che cambia qualcosa.
  if (metodo !== "GET") {
    const prova = await assicuraCsrf();
    if (prova) headers["X-CSRF-Token"] = prova;
  }

  try {
    return await fetch(BASE + percorso, {
      method: metodo,
      headers,
      body: corpo ? JSON.stringify(corpo) : undefined,
      // Senza questo il browser NON allega i cookie a un indirizzo diverso da
      // quello della pagina, e in produzione frontend e backend stanno su due
      // indirizzi diversi.
      credentials: "include",
      signal: stop.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function richiesta(metodo, percorso, corpo) {
  let risposta;
  let ultimoGuasto;

  // Si riprova SOLO per le letture. Ripetere una scrittura sarebbe pericoloso:
  // se la richiesta era arrivata e si e' persa solo la risposta, il secondo
  // tentativo creerebbe un doppione (due lavori, due commenti...).
  const riprovabile = metodo === "GET";
  const quanti = riprovabile ? TENTATIVI : 1;

  let hoSegnalato = false;
  try {
    for (let n = 1; n <= quanti; n++) {
      try {
        risposta = await unTentativo(metodo, percorso, corpo);
        break;
      } catch (guasto) {
        ultimoGuasto = guasto;
        if (n < quanti) {
          if (!hoSegnalato) { hoSegnalato = true; segnala(+1); }
          await aspetta(1500 * n);   // un attimo di piu' a ogni giro
        }
      }
    }
  } finally {
    // Anche se va male devo togliermi dal conto, altrimenti l'avviso resta
    // acceso per sempre.
    if (hoSegnalato) segnala(-1);
  }

  // Prova anti-CSRF scaduta: succede tutte le volte che il server rilascia una
  // sessione nuova (accesso, uscita, cambio azienda), perche' insieme rilascia
  // anche un valore nuovo e quello che ho in memoria diventa vecchio. Invece
  // di far vedere un errore incomprensibile, lo si richiede e si riprova UNA
  // volta sola.
  if (risposta && risposta.status === 403 && metodo !== "GET" && !_giaRiprovato) {
    valoreCsrf = null;
    _giaRiprovato = true;
    try {
      return await richiesta(metodo, percorso, corpo);
    } finally {
      _giaRiprovato = false;
    }
  }

  if (!risposta) {
    // Nessuna risposta: server spento, che si sta svegliando, o rete assente.
    // Il messaggio del browser ("Failed to fetch") non dice niente a nessuno.
    throw new Error(
      ultimoGuasto?.name === "AbortError"
        ? "Il server non ha risposto in tempo. Se e' rimasto fermo a lungo si sta " +
          "svegliando: riprova fra qualche secondo."
        : "Non riesco a contattare il server. Controlla la connessione e riprova."
    );
  }

  if (!risposta.ok) {
    let dettaglio = "Errore";
    try {
      const corpo = await risposta.json();
      if (typeof corpo.detail === "string") {
        dettaglio = corpo.detail;                       // errore semplice
      } else if (Array.isArray(corpo.detail)) {
        // errori di validazione (es. password debole): lista di messaggi
        dettaglio = corpo.detail.map((e) => e.msg).join("; ");
      }
    } catch {}

    // Qualche caso merita parole piu' chiare di quelle del server.
    if (risposta.status === 401 && percorso !== "/auth/login") {
      dettaglio = "La tua sessione e' scaduta: rientra per continuare.";
    } else if (risposta.status >= 500) {
      dettaglio = "Il server ha avuto un problema. Riprova fra poco; " +
                  "se continua, e' un guasto e ce ne stiamo accorgendo.";
    }
    const errore = new Error(dettaglio);
    errore.stato = risposta.status;
    throw errore;
  }
  // 204 = nessun contenuto; altrimenti leggo il JSON.
  return risposta.status === 204 ? null : risposta.json();
}

// Le funzioni che i componenti useranno, con nomi chiari.
export const api = {
  registra: (dati) => richiesta("POST", "/auth/register", dati),
  login:    (dati) => richiesta("POST", "/auth/login", dati),
  me:       () => richiesta("GET", "/auth/me"),
  // L'uscita la deve fare il server: il cookie della sessione e' HttpOnly,
  // quindi da qui non si puo' cancellare.
  esci:     () => richiesta("POST", "/auth/logout"),
  // Correggere i propri dati (diritto di rettifica).
  modificaProfilo: (nome) => richiesta("PATCH", "/auth/me", { nome }),
  cambiaEmail: (password, nuova_email) =>
    richiesta("POST", "/auth/cambia-email", { password, nuova_email }),
  confermaEmail: (token) => richiesta("POST", "/auth/conferma-email", { token }),
  reinviaVerifica: () => richiesta("POST", "/auth/reinvia-verifica"),
  richiediReset: (email) => richiesta("POST", "/auth/richiedi-reset", { email }),
  resetPassword: (token, nuova_password) => richiesta("POST", "/auth/reset-password", { token, nuova_password }),
  accettaInvito: (token, password) => richiesta("POST", "/auth/accetta-invito", { token, password }),
  esportaMieiDati: () => richiesta("GET", "/auth/me/export"),
  // Le aziende di cui faccio parte, e il passaggio dall'una all'altra.
  mieAziende: () => richiesta("GET", "/auth/aziende"),
  creaAzienda: (nome) => richiesta("POST", "/auth/aziende", { nome }),
  cambiaAzienda: (organizzazione_id) =>
    richiesta("POST", "/auth/cambia-azienda", { organizzazione_id }),
  accettaInvitoAzienda: (token) =>
    richiesta("POST", "/auth/accetta-invito-azienda", { token }),
  // Rispondere a un invito trovandolo nell'app, senza passare dall'email.
  accettaInvito: (organizzazione_id) =>
    richiesta("POST", "/auth/inviti/accetta", { organizzazione_id }),
  rifiutaInvito: (organizzazione_id) =>
    richiesta("POST", "/auth/inviti/rifiuta", { organizzazione_id }),
  cancellaMioAccount: () => richiesta("DELETE", "/auth/me"),
  eliminaUtente: (id) => richiesta("DELETE", `/utenti/${id}`),
  // Secondo fattore
  verificaDueFattori: (token, codice) =>
    richiesta("POST", "/auth/2fa/verifica", { token, codice }),
  statoDueFattori: () => richiesta("GET", "/auth/2fa/stato"),
  preparaDueFattori: () => richiesta("POST", "/auth/2fa/prepara"),
  attivaDueFattori: (codice) => richiesta("POST", "/auth/2fa/attiva", { codice }),
  disattivaDueFattori: (password) =>
    richiesta("POST", "/auth/2fa/disattiva", { password }),
  cambiaPassword: (vecchia_password, nuova_password) => richiesta("POST", "/auth/cambia-password", { vecchia_password, nuova_password }),
  // Ricerca unica: una parola, cinque tipi di risultato.
  cercaDappertutto: (q) => richiesta("GET", `/ricerca?q=${encodeURIComponent(q)}`),
  progetti: ()     => richiesta("GET", "/progetti"),
  // I filtri si sommano e li applica il SERVER: cosi' regge anche quando un
  // progetto accumula centinaia di lavori, e l'ordine resta giusto.
  lavori:   (progettoId, q = "", filtri = {}) => {
    const parti = [`progetto_id=${progettoId}`];
    if (q) parti.push(`q=${encodeURIComponent(q)}`);
    if (filtri.stato) parti.push(`stato=${filtri.stato}`);
    if (filtri.soloMiei) parti.push("solo_miei=true");
    else if (filtri.assegnatoA) parti.push(`assegnato_a=${filtri.assegnatoA}`);
    if (filtri.ordina) parti.push(`ordina=${filtri.ordina}`);
    return richiesta("GET", `/lavori?${parti.join("&")}`);
  },
  tuttiILavori: () => richiesta("GET", "/lavori"),
  creaProgetto: (dati) => richiesta("POST", "/progetti", dati),
  aggiornaProgetto: (id, dati) => richiesta("PATCH", `/progetti/${id}`, dati),
  eliminaProgetto: (id) => richiesta("DELETE", `/progetti/${id}`),
  creaLavoro:   (dati) => richiesta("POST", "/lavori", dati),
  cambiaStato:  (lavoroId, stato) => richiesta("PATCH", `/lavori/${lavoroId}/stato`, { stato }),
  modificaLavoro: (lavoroId, dati) => richiesta("PATCH", `/lavori/${lavoroId}`, dati),
  eliminaLavoro: (lavoroId) => richiesta("DELETE", `/lavori/${lavoroId}`),
  commenti:     (lavoroId) => richiesta("GET", `/lavori/${lavoroId}/commenti`),
  aggiungiCommento: (lavoroId, dati) => richiesta("POST", `/lavori/${lavoroId}/commenti`, dati),
  sottoAttivita: (lavoroId) => richiesta("GET", `/lavori/${lavoroId}/sotto-attivita`),
  creaSotto: (lavoroId, testo) => richiesta("POST", `/lavori/${lavoroId}/sotto-attivita`, { testo }),
  spuntaSotto: (sottoId, completata) => richiesta("PATCH", `/sotto-attivita/${sottoId}`, { completata }),
  eliminaSotto: (sottoId) => richiesta("DELETE", `/sotto-attivita/${sottoId}`),
  // --- Agenda (impegni con data e ora + scadenze in sovrapposizione) ---
  agenda:       (dal, al, ambito) => richiesta("GET", `/agenda?dal=${dal}&al=${al}&ambito=${ambito}`),
  prossimiImpegni: (giorni = 7) => richiesta("GET", `/agenda/prossimi?giorni=${giorni}`),
  creaImpegno:  (dati) => richiesta("POST", "/agenda", dati),
  modificaImpegno: (id, dati) => richiesta("PATCH", `/agenda/${id}`, dati),
  eliminaImpegno: (id) => richiesta("DELETE", `/agenda/${id}`),

  // --- Scheda macchina (storico dell'impianto) ---
  macchine:     () => richiesta("GET", "/macchine"),
  macchina:     (id) => richiesta("GET", `/macchine/${id}`),
  creaMacchina: (dati) => richiesta("POST", "/macchine", dati),
  modificaMacchina: (id, dati) => richiesta("PATCH", `/macchine/${id}`, dati),
  eliminaMacchina: (id) => richiesta("DELETE", `/macchine/${id}`),
  creaSezione:  (macchinaId, dati) => richiesta("POST", `/macchine/${macchinaId}/sezioni`, dati),
  modificaSezione: (id, dati) => richiesta("PATCH", `/sezioni/${id}`, dati),
  // Si manda la lista intera nell'ordine voluto, non "spostala di uno":
  // il server salva tutto insieme o niente.
  riordinaSezioni: (macchinaId, sezioni_ids) =>
    richiesta("PUT", `/macchine/${macchinaId}/sezioni/ordine`, { sezioni_ids }),
  eliminaSezione: (id) => richiesta("DELETE", `/sezioni/${id}`),
  voci:         (macchinaId, q = "") => richiesta("GET", `/macchine/${macchinaId}/voci${q}`),
  creaVoce:     (macchinaId, dati) => richiesta("POST", `/macchine/${macchinaId}/voci`, dati),
  modificaVoce: (id, dati) => richiesta("PATCH", `/voci/${id}`, dati),
  eliminaVoce:  (id) => richiesta("DELETE", `/voci/${id}`),
  // Allegati (link): un endpoint per tipo di scheda
  allegaMacchina: (id, dati) => richiesta("POST", `/macchine/${id}/allegati`, dati),
  allegaSezione: (id, dati) => richiesta("POST", `/sezioni/${id}/allegati`, dati),
  allegaVoce:   (id, dati) => richiesta("POST", `/voci/${id}/allegati`, dati),
  // Commenti e checklist di una voce di macchina. Spuntare e togliere un passo
  // passano da spuntaSotto/eliminaSotto qui sopra: l'indirizzo
  // /sotto-attivita/{id} e' lo stesso per i lavori e per le macchine.
  // Correggere e togliere valgono per tutti e due i mondi: l'indirizzo e' uno.
  correggiCommento: (id, testo) => richiesta("PATCH", `/commenti/${id}`, { testo }),
  togliCommento: (id) => richiesta("DELETE", `/commenti/${id}`),
  commentiVoce: (id) => richiesta("GET", `/voci/${id}/commenti`),
  commentaVoce: (id, testo) => richiesta("POST", `/voci/${id}/commenti`, { testo }),
  creaSottoVoce: (id, testo) => richiesta("POST", `/voci/${id}/sotto-attivita`, { testo }),
  allegaProgetto: (id, dati) => richiesta("POST", `/progetti/${id}/allegati`, dati),
  allegaLavoro: (id, dati) => richiesta("POST", `/lavori/${id}/allegati`, dati),
  eliminaAllegato: (id) => richiesta("DELETE", `/allegati/${id}`),

  // --- Avvisi in-app (campanella) ---
  notifiche:    () => richiesta("GET", "/notifiche"),
  segnaLetta:   (id) => richiesta("PATCH", `/notifiche/${id}`),
  segnaTutteLette: () => richiesta("POST", "/notifiche/segna-tutte-lette"),
  eliminaNotifica: (id) => richiesta("DELETE", `/notifiche/${id}`),

  reparti:      () => richiesta("GET", "/reparti"),
  creaReparto:  (nome) => richiesta("POST", "/reparti", { nome }),
  rinominaReparto: (id, nome) => richiesta("PATCH", `/reparti/${id}`, { nome }),
  eliminaReparto: (id) => richiesta("DELETE", `/reparti/${id}`),
  aggiungiMembro: (repartoId, utenteId) => richiesta("POST", `/reparti/${repartoId}/membri`, { utente_id: utenteId }),
  rimuoviMembro: (repartoId, utenteId) => richiesta("DELETE", `/reparti/${repartoId}/membri/${utenteId}`),
  utenti:       () => richiesta("GET", "/utenti"),
  creaUtente:   (dati) => richiesta("POST", "/utenti", dati),
  invitaUtente: (dati) => richiesta("POST", "/utenti/invita", dati),
  cambiaRuolo:  (utenteId, ruolo) => richiesta("PATCH", `/utenti/${utenteId}/ruolo`, { ruolo }),
  assegna:      (lavoroId, utenteId) => richiesta("POST", `/lavori/${lavoroId}/assegnati`, { utente_id: utenteId }),
  rimuoviAssegnato: (lavoroId, utenteId) => richiesta("DELETE", `/lavori/${lavoroId}/assegnati/${utenteId}`),
};
