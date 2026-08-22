// api.js — il punto UNICO da cui il frontend parla col backend.
// Tenere le chiamate qui (invece che sparse nei componenti) e' come avere
// i router nel backend: ordine e un posto solo da cambiare se qualcosa cambia.

// L'indirizzo del backend. In locale usa il default; in produzione si imposta
// la variabile VITE_API_URL con l'indirizzo del backend online.
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Tiene il token in memoria dopo il login. Le chiamate protette lo allegano.
let token = null;
export function setToken(t) { token = t; }
export function getToken() { return token; }

async function richiesta(metodo, percorso, corpo) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const risposta = await fetch(BASE + percorso, {
    method: metodo,
    headers,
    body: corpo ? JSON.stringify(corpo) : undefined,
  });

  // Se il backend risponde con errore, leggo il messaggio e lo rilancio.
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
    throw new Error(dettaglio);
  }
  // 204 = nessun contenuto; altrimenti leggo il JSON.
  return risposta.status === 204 ? null : risposta.json();
}

// Le funzioni che i componenti useranno, con nomi chiari.
export const api = {
  registra: (dati) => richiesta("POST", "/auth/register", dati),
  login:    (dati) => richiesta("POST", "/auth/login", dati),
  me:       () => richiesta("GET", "/auth/me"),
  progetti: ()     => richiesta("GET", "/progetti"),
  lavori:   (progettoId) => richiesta("GET", `/lavori?progetto_id=${progettoId}`),
  creaProgetto: (dati) => richiesta("POST", "/progetti", dati),
  creaLavoro:   (dati) => richiesta("POST", "/lavori", dati),
  cambiaStato:  (lavoroId, stato) => richiesta("PATCH", `/lavori/${lavoroId}/stato`, { stato }),
  commenti:     (lavoroId) => richiesta("GET", `/lavori/${lavoroId}/commenti`),
  aggiungiCommento: (lavoroId, dati) => richiesta("POST", `/lavori/${lavoroId}/commenti`, dati),
  utenti:       () => richiesta("GET", "/utenti"),
  assegna:      (lavoroId, utenteId) => richiesta("POST", `/lavori/${lavoroId}/assegnati`, { utente_id: utenteId }),
  rimuoviAssegnato: (lavoroId, utenteId) => richiesta("DELETE", `/lavori/${lavoroId}/assegnati/${utenteId}`),
};
