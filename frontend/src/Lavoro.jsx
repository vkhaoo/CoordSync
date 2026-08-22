import { useState } from "react";
import { api } from "./api.js";

const ETICHETTA_STATO = {
  da_fare: "Da fare", in_corso: "In corso", in_attesa: "In attesa", fatto: "Fatto",
};
const ETICHETTA_PRIORITA = {
  bassa: "Bassa", normale: "Normale", alta: "Alta", urgente: "Urgente",
};
const STATI = Object.keys(ETICHETTA_STATO);

// Una singola card lavoro. Gestisce da sola i propri commenti:
// ogni card ha il suo stato "aperto" e la sua lista di commenti.
export default function Lavoro({ lavoro, utenti, onCambiaStato, onAssegnazioneCambiata }) {
  const [aperto, setAperto] = useState(false);
  const [commenti, setCommenti] = useState([]);
  const [nuovoCommento, setNuovoCommento] = useState("");
  const [errore, setErrore] = useState(null);

  async function assegna(utenteId) {
    setErrore(null);
    try {
      await api.assegna(lavoro.id, Number(utenteId));
      onAssegnazioneCambiata();   // dico alla Dashboard di ricaricare i lavori
    } catch (err) { setErrore(err.message); }
  }

  async function rimuoviAssegnato(utenteId) {
    setErrore(null);
    try {
      await api.rimuoviAssegnato(lavoro.id, utenteId);
      onAssegnazioneCambiata();
    } catch (err) { setErrore(err.message); }
  }

  // Colleghi non ancora assegnati (per il menu "aggiungi").
  const idAssegnati = lavoro.assegnatari.map((u) => u.id);
  const disponibili = utenti.filter((u) => !idAssegnati.includes(u.id));

  async function apriChiudi() {
    const prossimo = !aperto;
    setAperto(prossimo);
    // Carico i commenti la prima volta che apro.
    if (prossimo && commenti.length === 0) {
      try { setCommenti(await api.commenti(lavoro.id)); }
      catch (e) { setErrore(e.message); }
    }
  }

  async function inviaCommento(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creato = await api.aggiungiCommento(lavoro.id, { testo: nuovoCommento });
      setCommenti((prec) => [...prec, creato]);   // aggiungo in fondo alla lista
      setNuovoCommento("");
    } catch (err) { setErrore(err.message); }
  }

  return (
    <li className={`lavoro card-${lavoro.stato}`}>
      <div className="lavoro-testa">
        <span className="lavoro-titolo">{lavoro.titolo}</span>
        <select
          className={`stato-select stato-${lavoro.stato}`}
          value={lavoro.stato}
          onChange={(e) => onCambiaStato(lavoro.id, e.target.value)}
        >
          {STATI.map((s) => <option key={s} value={s}>{ETICHETTA_STATO[s]}</option>)}
        </select>
      </div>

      <div className="lavoro-meta">
        <span className={`prio prio-${lavoro.priorita}`}>{ETICHETTA_PRIORITA[lavoro.priorita]}</span>
        <button className="link-commenti" onClick={apriChiudi}>
          {aperto ? "Nascondi commenti" : "Commenti"}
        </button>
      </div>

      {/* Assegnatari: chi ci lavora, con rimozione, e menu per aggiungere */}
      <div className="assegnazione">
        {lavoro.assegnatari.map((u) => (
          <span key={u.id} className="chip">
            {u.nome}
            <button className="chip-x" onClick={() => rimuoviAssegnato(u.id)} title="Rimuovi">×</button>
          </span>
        ))}
        {disponibili.length > 0 && (
          <select
            className="assegna-select"
            value=""
            onChange={(e) => { if (e.target.value) assegna(e.target.value); }}
          >
            <option value="">+ Assegna…</option>
            {disponibili.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
        )}
      </div>

      {aperto && (
        <div className="commenti">
          {errore && <p className="errore">{errore}</p>}
          {commenti.length === 0 ? (
            <p className="vuoto piccolo">Nessun commento.</p>
          ) : (
            <ul className="lista-commenti">
              {commenti.map((c) => (
                <li key={c.id} className="commento">
                  <span className="commento-autore">{c.autore.nome}</span>
                  <span className="commento-testo">{c.testo}</span>
                </li>
              ))}
            </ul>
          )}
          <form className="form-commento" onSubmit={inviaCommento}>
            <input
              placeholder="Scrivi un commento…"
              value={nuovoCommento}
              onChange={(e) => setNuovoCommento(e.target.value)}
              required
            />
            <button type="submit" className="mini">→</button>
          </form>
        </div>
      )}
    </li>
  );
}
