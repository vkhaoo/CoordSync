import { useState, useEffect } from "react";
import { api } from "./api.js";

// Pannello di amministrazione dei reparti. Visibile solo all'admin.
// Un reparto raggruppa colleghi e progetti: chi ne fa parte vede i progetti
// del reparto, chi non ne fa parte no.
export default function GestioneReparti() {
  const [reparti, setReparti] = useState([]);
  const [utenti, setUtenti] = useState([]);
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  const [nuovoNome, setNuovoNome] = useState("");
  const [rinominoId, setRinominoId] = useState(null);
  const [nomeBozza, setNomeBozza] = useState("");

  async function carica() {
    try {
      const [r, u] = await Promise.all([api.reparti(), api.utenti()]);
      setReparti(r);
      setUtenti(u);
    } catch (e) { setErrore(e.message); }
    finally { setCaricando(false); }
  }

  useEffect(() => { carica(); }, []);

  async function azione(fn) {
    setErrore(null);
    try { await fn(); await carica(); }
    catch (err) { setErrore(err.message); }
  }

  async function elimina(reparto) {
    if (!window.confirm(
      `Eliminare il reparto "${reparto.nome}"?\n\n` +
      `I progetti NON vengono cancellati: tornano visibili a tutta l'azienda.`
    )) return;
    await azione(() => api.eliminaReparto(reparto.id));
  }

  if (caricando) return <p className="vuoto">Caricamento…</p>;

  // Per ogni reparto, chi ne fa parte: lo ricavo dagli utenti, che portano
  // gia' con se' i propri reparti (evita una seconda chiamata per reparto).
  const membriDi = (repartoId) => utenti.filter((u) => u.reparti.some((r) => r.id === repartoId));

  return (
    <div className="gestione-utenti">
      <h2 className="titolo-progetto">Reparti</h2>
      <p className="sottotitolo">
        Chi fa parte di un reparto vede i suoi progetti. I progetti senza reparto
        restano visibili a tutta l'azienda.
      </p>

      {errore && <p className="errore">{errore}</p>}

      <p className="etichetta-form">Nuovo reparto</p>
      <form className="form-utente" onSubmit={(e) => {
        e.preventDefault();
        azione(async () => { await api.creaReparto(nuovoNome); setNuovoNome(""); });
      }}>
        <input placeholder="Nome del reparto (es. Automazione)" value={nuovoNome}
               onChange={(e) => setNuovoNome(e.target.value)} required />
        <button type="submit" className="principale piccolo">Crea reparto</button>
      </form>

      {reparti.length === 0 ? (
        <p className="vuoto">Nessun reparto. Finché non ne crei uno, tutti vedono tutto.</p>
      ) : reparti.map((r) => {
        const membri = membriDi(r.id);
        const disponibili = utenti.filter((u) => !membri.some((m) => m.id === u.id));
        return (
          <div key={r.id} className="scheda-reparto">
            <div className="testa-reparto">
              {rinominoId === r.id ? (
                <div className="form-inline" style={{ marginTop: 0, flex: 1, maxWidth: 360 }}>
                  <input value={nomeBozza} onChange={(e) => setNomeBozza(e.target.value)} />
                  <button className="mini" onClick={() => azione(async () => {
                    await api.rinominaReparto(r.id, nomeBozza);
                    setRinominoId(null);
                  })}>✓</button>
                  <button className="mini annulla" onClick={() => setRinominoId(null)}>×</button>
                </div>
              ) : (
                <>
                  <h3 className="nome-reparto">{r.nome}</h3>
                  <div className="lavoro-azioni">
                    <button className="azione-icona" title="Rinomina"
                            onClick={() => { setNomeBozza(r.nome); setRinominoId(r.id); }}>✎</button>
                    <button className="azione-icona elimina" title="Elimina"
                            onClick={() => elimina(r)}>🗑</button>
                  </div>
                </>
              )}
            </div>

            <div className="assegnazione">
              {membri.length === 0 && <span className="vuoto piccolo">Nessun membro</span>}
              {membri.map((m) => (
                <span key={m.id} className="chip">
                  {m.nome}
                  <button className="chip-x" title="Togli dal reparto"
                          onClick={() => azione(() => api.rimuoviMembro(r.id, m.id))}>×</button>
                </span>
              ))}
              {disponibili.length > 0 && (
                <select className="assegna-select" value=""
                        onChange={(e) => {
                          if (e.target.value) azione(() => api.aggiungiMembro(r.id, Number(e.target.value)));
                        }}>
                  <option value="">+ Aggiungi…</option>
                  {disponibili.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                </select>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
