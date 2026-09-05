// api.js — il punto UNICO da cui il frontend parla col backend.
// Tenere le chiamate qui (invece che sparse nei componenti) e' come avere
// i router nel backend: ordine e un posto solo da cambiare se qualcosa cambia.

// L'indirizzo del backend. In locale usa il default; in produzione si imposta
// la variabile VITE_API_URL con l'indirizzo del backend online.
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Il token viene salvato nel browser (localStorage) cosi' resta anche dopo
// aver ricaricato la pagina. Al primo caricamento lo rileggo da li'.
const CHIAVE_TOKEN = "coordsync_token";
let token = localStorage.getItem(CHIAVE_TOKEN);

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem(CHIAVE_TOKEN, t);   // salvo
  else localStorage.removeItem(CHIAVE_TOKEN);       // logout: rimuovo
}
export function getToken() { return token; }

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
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    return await fetch(BASE + percorso, {
      method: metodo,
      headers,
      body: corpo ? JSON.stringify(corpo) : undefined,
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
  reinviaVerifica: () => richiesta("POST", "/auth/reinvia-verifica"),
  richiediReset: (email) => richiesta("POST", "/auth/richiedi-reset", { email }),
  resetPassword: (token, nuova_password) => richiesta("POST", "/auth/reset-password", { token, nuova_password }),
  accettaInvito: (token, password) => richiesta("POST", "/auth/accetta-invito", { token, password }),
  esportaMieiDati: () => richiesta("GET", "/auth/me/export"),
  cancellaMioAccount: () => richiesta("DELETE", "/auth/me"),
  eliminaUtente: (id) => richiesta("DELETE", `/utenti/${id}`),
  cambiaPassword: (vecchia_password, nuova_password) => richiesta("POST", "/auth/cambia-password", { vecchia_password, nuova_password }),
  progetti: ()     => richiesta("GET", "/progetti"),
  lavori:   (progettoId, q = "") => richiesta("GET",
    `/lavori?progetto_id=${progettoId}` + (q ? `&q=${encodeURIComponent(q)}` : "")),
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
