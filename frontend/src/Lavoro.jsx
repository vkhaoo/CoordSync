import { useState } from "react";
import { api } from "./api.js";
import Allegati from "./Allegati.jsx";
import { dalServer } from "./date.js";

const ETICHETTA_STATO = {
  da_fare: "Da fare", in_corso: "In corso", in_attesa: "In attesa", fatto: "Fatto",
};
const ETICHETTA_PRIORITA = {
  bassa: "Bassa", normale: "Normale", alta: "Alta", urgente: "Urgente",
};
const STATI = Object.keys(ETICHETTA_STATO);
const PRIORITA = Object.keys(ETICHETTA_PRIORITA);

// "In scadenza" se mancano al massimo questi giorni. Calcolato qui (lato client):
// e' un dato derivato, non si memorizza (regola del progetto).
const GIORNI_AVVISO = 3;

function infoScadenza(lavoro) {
  if (!lavoro.data_scadenza || lavoro.stato === "fatto") return null;
  const oggi = new Date();
  oggi.setHours(0, 0, 0, 0);
  // "T00:00:00" forza la mezzanotte LOCALE (senza, la data ISO verrebbe letta come UTC).
  const scadenza = new Date(lavoro.data_scadenza + "T00:00:00");
  const giorni = Math.round((scadenza - oggi) / 86400000);
  if (giorni < 0) return { classe: "scad-ritardo", testo: "In ritardo" };
  if (giorni === 0) return { classe: "scad-vicina", testo: "Scade oggi" };
  if (giorni <= GIORNI_AVVISO) return { classe: "scad-vicina", testo: "In scadenza" };
  return null;
}

// Una singola card lavoro. Gestisce da sola i propri commenti:
// ogni card ha il suo stato "aperto" e la sua lista di commenti.
export default function Lavoro({ lavoro, utenti, io, onCambiaStato, onAssegnazioneCambiata }) {
  const [aperto, setAperto] = useState(false);
  const [commenti, setCommenti] = useState([]);
  const [nuovoCommento, setNuovoCommento] = useState("");
  const [errore, setErrore] = useState(null);

  // Permessi calcolati in base al mio ruolo e all'essere assegnato o meno.
  const gestisco = io && (io.ruolo === "admin" || io.ruolo === "caposquadra");
  const sonoAssegnato = io && lavoro.assegnatari.some((u) => u.id === io.id);
  const possoAggiornare = gestisco || sonoAssegnato;   // stato, commenti, spunta checklist

  // Checklist: parto dalle sotto-attivita' gia' incluse nel lavoro.
  const [sotto, setSotto] = useState(lavoro.sotto_attivita || []);
  const [nuovaVoce, setNuovaVoce] = useState("");

  async function aggiungiVoce(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creata = await api.creaSotto(lavoro.id, nuovaVoce);
      setSotto((prec) => [...prec, creata]);
      setNuovaVoce("");
      onAssegnazioneCambiata();   // ricarico i lavori (aggiorna eventuali conteggi)
    } catch (err) { setErrore(err.message); }
  }

  async function spunta(voce) {
    setErrore(null);
    try {
      const agg = await api.spuntaSotto(voce.id, !voce.completata);
      setSotto((prec) => prec.map((v) => (v.id === agg.id ? agg : v)));
    } catch (err) { setErrore(err.message); }
  }

  async function eliminaVoce(voceId) {
    setErrore(null);
    try {
      await api.eliminaSotto(voceId);
      setSotto((prec) => prec.filter((v) => v.id !== voceId));
    } catch (err) { setErrore(err.message); }
  }

  const fatteSotto = sotto.filter((v) => v.completata).length;
  const percSotto = sotto.length ? Math.round((fatteSotto / sotto.length) * 100) : 0;
  const [checklistAperta, setChecklistAperta] = useState(false);

  // Modifica titolo ed eliminazione del lavoro (solo chi gestisce).
  const [modificaTitolo, setModificaTitolo] = useState(false);
  const [titoloBozza, setTitoloBozza] = useState(lavoro.titolo);

  // Scadenza: badge per tutti, modifica per chi gestisce.
  const [modificaScadenza, setModificaScadenza] = useState(false);
  const [scadenzaBozza, setScadenzaBozza] = useState("");
  const badge = infoScadenza(lavoro);

  async function cambiaPriorita(nuova) {
    setErrore(null);
    try {
      await api.modificaLavoro(lavoro.id, { priorita: nuova });
      // Ricarico invece di aggiornare solo la card: la lista e' ordinata per
      // priorita', quindi il lavoro deve anche spostarsi al posto giusto.
      onAssegnazioneCambiata();
    } catch (err) { setErrore(err.message); }
  }

  async function salvaScadenza(valore) {
    setErrore(null);
    try {
      await api.modificaLavoro(lavoro.id, { data_scadenza: valore || null });
      setModificaScadenza(false);
      onAssegnazioneCambiata();   // ricarico i lavori (badge aggiornato)
    } catch (err) { setErrore(err.message); }
  }

  async function salvaTitolo() {
    setErrore(null);
    try {
      await api.modificaLavoro(lavoro.id, { titolo: titoloBozza });
      setModificaTitolo(false);
      onAssegnazioneCambiata();   // ricarico i lavori (mostra il titolo nuovo)
    } catch (err) { setErrore(err.message); }
  }

  async function elimina() {
    if (!window.confirm(`Eliminare il lavoro "${lavoro.titolo}"? L'azione è irreversibile.`)) return;
    setErrore(null);
    try {
      await api.eliminaLavoro(lavoro.id);
      onAssegnazioneCambiata();   // ricarico: il lavoro sparisce dalla lista
    } catch (err) { setErrore(err.message); }
  }

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
        {modificaTitolo ? (
          <div className="form-inline" style={{ flex: 1 }}>
            <input value={titoloBozza} onChange={(e) => setTitoloBozza(e.target.value)} />
            <button className="mini" onClick={salvaTitolo}>✓</button>
            <button className="mini annulla" onClick={() => { setModificaTitolo(false); setTitoloBozza(lavoro.titolo); }}>×</button>
          </div>
        ) : (
          <span className="lavoro-titolo">{lavoro.titolo}</span>
        )}
        <div className="lavoro-azioni">
          {gestisco && !modificaTitolo && (
            <>
              <button className="azione-icona" title="Rinomina"
                      onClick={() => { setTitoloBozza(lavoro.titolo); setModificaTitolo(true); }}>✎</button>
              <button className="azione-icona elimina" title="Elimina" onClick={elimina}>🗑</button>
            </>
          )}
          <select
            className={`stato-select stato-${lavoro.stato}`}
            value={lavoro.stato}
            disabled={!possoAggiornare}
            onChange={(e) => onCambiaStato(lavoro.id, e.target.value)}
          >
            {STATI.map((s) => <option key={s} value={s}>{ETICHETTA_STATO[s]}</option>)}
          </select>
        </div>
      </div>

      <div className="lavoro-meta">
        {/* Priorita': modificabile da chi gestisce, solo etichetta per gli altri */}
        {gestisco ? (
          <select className={`prio prio-select prio-${lavoro.priorita}`} value={lavoro.priorita}
                  title="Cambia priorità"
                  onChange={(e) => cambiaPriorita(e.target.value)}>
            {PRIORITA.map((p) => <option key={p} value={p}>{ETICHETTA_PRIORITA[p]}</option>)}
          </select>
        ) : (
          <span className={`prio prio-${lavoro.priorita}`}>{ETICHETTA_PRIORITA[lavoro.priorita]}</span>
        )}

        {/* Scadenza: chip informativo; chi gestisce ci clicca per modificarla */}
        {modificaScadenza ? (
          <span className="scadenza-edit">
            <input type="date" value={scadenzaBozza}
                   onChange={(e) => setScadenzaBozza(e.target.value)} />
            <button className="mini" title="Salva (vuota = togli scadenza)"
                    onClick={() => salvaScadenza(scadenzaBozza)}>✓</button>
            <button className="mini annulla" title="Annulla"
                    onClick={() => setModificaScadenza(false)}>×</button>
          </span>
        ) : lavoro.data_scadenza ? (
          <button className={`scadenza ${badge ? badge.classe : ""}`} disabled={!gestisco}
                  title={gestisco ? "Modifica scadenza" : undefined}
                  onClick={() => { setScadenzaBozza(lavoro.data_scadenza); setModificaScadenza(true); }}>
            ⏱ {new Date(lavoro.data_scadenza + "T00:00:00").toLocaleDateString("it-IT")}
            {badge && badge.testo && <> · {badge.testo}</>}
          </button>
        ) : gestisco && lavoro.stato !== "fatto" && (
          <button className="scadenza aggiungi"
                  onClick={() => { setScadenzaBozza(""); setModificaScadenza(true); }}>
            + scadenza
          </button>
        )}

        <button className="link-commenti" onClick={apriChiudi}>
          {aperto ? "Nascondi commenti" : "Commenti"}
        </button>
      </div>

      {/* Se completato: mostro quando e da chi */}
      {lavoro.stato === "fatto" && lavoro.completato_il && (
        <div className="completamento-info">
          ✓ Completato il {dalServer(lavoro.completato_il).toLocaleDateString("it-IT")}
          {lavoro.completato_da && <> da {lavoro.completato_da.nome}</>}
        </div>
      )}

      {/* Checklist (sotto-attivita') — collassabile */}
      {(sotto.length > 0 || gestisco) && (
        <div className="checklist">
          <button className="checklist-toggle" onClick={() => setChecklistAperta((a) => !a)}>
            <span className="freccia">{checklistAperta ? "▾" : "▸"}</span>
            {sotto.length > 0
              ? <>Checklist · {fatteSotto}/{sotto.length} ({percSotto}%)</>
              : <>Checklist</>}
          </button>

          {/* Barra di avanzamento: visibile anche da chiusa, per un colpo d'occhio */}
          {sotto.length > 0 && (
            <div className="barra barra-sm" style={{ maxWidth: 260, marginBottom: "0.4rem" }}>
              <div className="barra-piena" style={{ width: `${percSotto}%` }} />
            </div>
          )}

          {checklistAperta && (
            <>
              <ul className="lista-sotto">
                {sotto.map((v) => (
                  <li key={v.id} className="voce-sotto">
                    <label className={v.completata ? "spuntata" : ""}>
                      <input type="checkbox" checked={v.completata}
                             disabled={!possoAggiornare}
                             onChange={() => spunta(v)} />
                      {v.testo}
                    </label>
                    {gestisco && (
                      <button className="chip-x" onClick={() => eliminaVoce(v.id)} title="Elimina">×</button>
                    )}
                  </li>
                ))}
              </ul>
              {gestisco && (
                <form className="form-sotto" onSubmit={aggiungiVoce}>
                  <input placeholder="Aggiungi voce…" value={nuovaVoce}
                         onChange={(e) => setNuovaVoce(e.target.value)} required />
                  <button type="submit" className="mini">+</button>
                </form>
              )}
            </>
          )}
        </div>
      )}

      {/* Link appesi al lavoro (foto dal campo, schemi, documentazione) */}
      <Allegati allegati={lavoro.allegati || []}
                onAggiungi={async (dati) => {
                  await api.allegaLavoro(lavoro.id, dati);
                  onAssegnazioneCambiata();
                }}
                onElimina={async (id) => {
                  await api.eliminaAllegato(id);
                  onAssegnazioneCambiata();
                }} />

      {/* Assegnatari: visibili a tutti; modificabili solo da chi gestisce */}
      <div className="assegnazione">
        {lavoro.assegnatari.map((u) => (
          <span key={u.id} className="chip">
            {u.nome}
            {gestisco && (
              <button className="chip-x" onClick={() => rimuoviAssegnato(u.id)} title="Rimuovi">×</button>
            )}
          </span>
        ))}
        {gestisco && disponibili.length > 0 && (
          <select
            className="assegna-select"
            value=""
            onChange={(e) => { if (e.target.value) assegna(e.target.value); }}
          >
            <option value="">+ Assegna…</option>
            {disponibili.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
        )}
        {lavoro.assegnatari.length === 0 && !gestisco && (
          <span className="vuoto piccolo">Nessun assegnatario</span>
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
          {possoAggiornare ? (
            <form className="form-commento" onSubmit={inviaCommento}>
              <input
                placeholder="Scrivi un commento…"
                value={nuovoCommento}
                onChange={(e) => setNuovoCommento(e.target.value)}
                required
              />
              <button type="submit" className="mini">→</button>
            </form>
          ) : (
            <p className="vuoto piccolo">Solo chi è assegnato può commentare.</p>
          )}
        </div>
      )}
    </li>
  );
}
