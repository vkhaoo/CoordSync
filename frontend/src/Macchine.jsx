import { useState, useEffect } from "react";
import { api } from "./api.js";

// Etichette dei tipi di voce. "informazione" e' a parte: non e' un fatto
// avvenuto in una data, e' sapere di riferimento che resta valido.
const TIPI = {
  lavoro: "Lavoro",
  modifica: "Modifica",
  analisi: "Analisi",
  informazione: "Informazione utile",
};
const STATI = { da_fare: "Da fare", in_corso: "In corso", fatto: "Fatto" };

// Lista di link riutilizzabile: la stessa per macchina, sezione e voce.
function Allegati({ allegati, onAggiungi, onElimina }) {
  const [apri, setApri] = useState(false);
  const [url, setUrl] = useState("");
  const [titolo, setTitolo] = useState("");

  async function invia(e) {
    e.preventDefault();
    await onAggiungi({ url, titolo: titolo || null });
    setUrl(""); setTitolo(""); setApri(false);
  }

  return (
    <div className="allegati">
      {allegati.map((a) => (
        <span key={a.id} className="chip allegato">
          <a href={a.url} target="_blank" rel="noreferrer">🔗 {a.titolo || a.url}</a>
          <button className="chip-x" title="Togli il link"
                  onClick={() => onElimina(a.id)}>×</button>
        </span>
      ))}
      {apri ? (
        <form className="form-inline form-allegato" onSubmit={invia}>
          <input placeholder="https://…" value={url}
                 onChange={(e) => setUrl(e.target.value)} required />
          <input placeholder="Etichetta (facoltativa)" value={titolo}
                 onChange={(e) => setTitolo(e.target.value)} />
          <button type="submit" className="mini">✓</button>
          <button type="button" className="mini annulla" onClick={() => setApri(false)}>×</button>
        </form>
      ) : (
        <button className="assegna-select" onClick={() => setApri(true)}>+ link</button>
      )}
    </div>
  );
}

export default function Macchine({ io, reparti }) {
  const [macchine, setMacchine] = useState([]);
  const [selezionata, setSelezionata] = useState(null);
  const [scheda, setScheda] = useState(null);      // dettaglio della macchina aperta
  const [voci, setVoci] = useState([]);
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  // Filtri dello storico
  const [filtroTipo, setFiltroTipo] = useState("");      // "" = tutti
  const [filtroSezione, setFiltroSezione] = useState("");  // "" = tutta la macchina

  // Form
  const [nuovaMacchina, setNuovaMacchina] = useState("");
  const [nuovaSezione, setNuovaSezione] = useState("");
  const [vTipo, setVTipo] = useState("lavoro");
  const [vTitolo, setVTitolo] = useState("");
  const [vTesto, setVTesto] = useState("");
  const [vStato, setVStato] = useState("da_fare");
  const [vGenerale, setVGenerale] = useState(true);
  const [vSezioni, setVSezioni] = useState([]);

  const gestisco = io && (io.ruolo === "admin" || io.ruolo === "caposquadra");

  async function caricaMacchine(selezionaId) {
    const dati = await api.macchine();
    setMacchine(dati);
    if (selezionaId != null) setSelezionata(selezionaId);
    else if (selezionata == null && dati.length > 0) setSelezionata(dati[0].id);
  }

  async function caricaScheda(id) {
    if (id == null) { setScheda(null); setVoci([]); return; }
    const q = [];
    if (filtroTipo) q.push(`tipo=${filtroTipo}`);
    if (filtroSezione) q.push(`sezione_id=${filtroSezione}`);
    const [s, v] = await Promise.all([
      api.macchina(id),
      api.voci(id, q.length ? `?${q.join("&")}` : ""),
    ]);
    setScheda(s);
    setVoci(v);
  }

  useEffect(() => {
    caricaMacchine().catch((e) => setErrore(e.message)).finally(() => setCaricando(false));
  }, []);

  useEffect(() => {
    caricaScheda(selezionata).catch((e) => setErrore(e.message));
  }, [selezionata, filtroTipo, filtroSezione]);

  async function azione(fn) {
    setErrore(null);
    try { await fn(); await caricaScheda(selezionata); }
    catch (err) { setErrore(err.message); }
  }

  async function aggiungiMacchina(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creata = await api.creaMacchina({ nome: nuovaMacchina });
      setNuovaMacchina("");
      await caricaMacchine(creata.id);
    } catch (err) { setErrore(err.message); }
  }

  async function eliminaMacchina() {
    if (!window.confirm(
      `Eliminare la macchina "${scheda.nome}"?\n\n` +
      `Spariscono le sue sezioni, le voci dello storico e i link.\n` +
      `Progetti e lavori collegati NON vengono cancellati.`
    )) return;
    setErrore(null);
    try {
      await api.eliminaMacchina(scheda.id);
      setSelezionata(null);
      await caricaMacchine();
    } catch (err) { setErrore(err.message); }
  }

  async function aggiungiVoce(e) {
    e.preventDefault();
    await azione(async () => {
      await api.creaVoce(selezionata, {
        tipo: vTipo,
        titolo: vTitolo,
        testo: vTesto || null,
        stato: vTipo === "lavoro" ? vStato : null,
        in_generale: vGenerale,
        sezioni_ids: vSezioni,
      });
      setVTitolo(""); setVTesto(""); setVSezioni([]); setVGenerale(true);
    });
  }

  function alternaSezioneNuovaVoce(id) {
    setVSezioni((prec) => prec.includes(id) ? prec.filter((x) => x !== id) : [...prec, id]);
  }

  if (caricando) return <p className="vuoto">Caricamento…</p>;

  // Le informazioni utili restano in evidenza: sono sapere di riferimento,
  // non fatti accaduti, quindi non hanno senso sepolte nella cronologia.
  const info = voci.filter((v) => v.tipo === "informazione");
  const cronologia = voci.filter((v) => v.tipo !== "informazione");

  return (
    <div className="corpo">
      <aside className="colonna-progetti">
        <h2 className="titolo-colonna">Macchine</h2>
        {macchine.length === 0 && <p className="vuoto">Nessuna macchina ancora.</p>}
        <ul className="lista-progetti">
          {macchine.map((m) => (
            <li key={m.id}>
              <button className={m.id === selezionata ? "voce attiva" : "voce"}
                      onClick={() => setSelezionata(m.id)}>{m.nome}</button>
            </li>
          ))}
        </ul>
        {gestisco && (
          <form className="form-inline" onSubmit={aggiungiMacchina}>
            <input placeholder="Nuova macchina…" value={nuovaMacchina}
                   onChange={(e) => setNuovaMacchina(e.target.value)} required />
            <button type="submit" className="mini">+</button>
          </form>
        )}
      </aside>

      <main className="area-lavori">
        {errore && <p className="errore">{errore}</p>}

        {!scheda ? (
          <p className="vuoto">Seleziona una macchina, o creane una.</p>
        ) : (
          <>
            <div className="intestazione-progetto">
              <div className="testa-progetto">
                <h2 className="titolo-progetto">{scheda.nome}</h2>
                {gestisco && (
                  <div className="lavoro-azioni">
                    <button className="azione-icona elimina" title="Elimina macchina"
                            onClick={eliminaMacchina}>🗑</button>
                  </div>
                )}
              </div>

              {gestisco ? (
                <input className="descrizione-macchina"
                       placeholder="Modello, matricola, note d'impianto…"
                       defaultValue={scheda.descrizione || ""}
                       onBlur={(e) => {
                         if (e.target.value !== (scheda.descrizione || "")) {
                           azione(() => api.modificaMacchina(scheda.id, { descrizione: e.target.value }));
                         }
                       }} />
              ) : scheda.descrizione && (
                <p className="sottotitolo">{scheda.descrizione}</p>
              )}

              {reparti.length > 0 && (
                <div className="riga-reparto">
                  {gestisco ? (
                    <select className="reparto-select" value={scheda.reparto_id ?? ""}
                            title="Chi vede questa macchina"
                            onChange={(e) => azione(() => api.modificaMacchina(scheda.id, {
                              reparto_id: e.target.value === "" ? null : Number(e.target.value),
                            }))}>
                      <option value="">Tutta l'azienda</option>
                      {reparti.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}
                    </select>
                  ) : (
                    <span className="reparto-chip">
                      {reparti.find((r) => r.id === scheda.reparto_id)?.nome ?? "Tutta l'azienda"}
                    </span>
                  )}
                </div>
              )}

              <Allegati allegati={scheda.allegati}
                        onAggiungi={(d) => azione(() => api.allegaMacchina(scheda.id, d))}
                        onElimina={(id) => azione(() => api.eliminaAllegato(id))} />
            </div>

            {/* Sezioni della macchina: fanno anche da filtro */}
            <div className="barra-sezioni">
              <button className={filtroSezione === "" ? "sez attiva" : "sez"}
                      onClick={() => setFiltroSezione("")}>Tutta la macchina</button>
              {scheda.sezioni.map((s) => (
                <span key={s.id} className="sez-gruppo">
                  <button className={String(filtroSezione) === String(s.id) ? "sez attiva" : "sez"}
                          onClick={() => setFiltroSezione(s.id)}>{s.nome}</button>
                  {gestisco && (
                    <button className="chip-x" title="Elimina sezione (le voci restano)"
                            onClick={() => {
                              if (window.confirm(`Eliminare la sezione "${s.nome}"? Le voci restano nella macchina.`))
                                azione(() => api.eliminaSezione(s.id));
                            }}>×</button>
                  )}
                </span>
              ))}
              {gestisco && (
                <form className="form-inline form-sezione" onSubmit={(e) => {
                  e.preventDefault();
                  azione(async () => { await api.creaSezione(scheda.id, { nome: nuovaSezione, ordine: scheda.sezioni.length }); setNuovaSezione(""); });
                }}>
                  <input placeholder="Nuova sezione…" value={nuovaSezione}
                         onChange={(e) => setNuovaSezione(e.target.value)} required />
                  <button type="submit" className="mini">+</button>
                </form>
              )}
            </div>

            {/* Filtro per tipo */}
            <div className="barra-sezioni">
              <button className={filtroTipo === "" ? "sez attiva" : "sez"}
                      onClick={() => setFiltroTipo("")}>Storico completo</button>
              {Object.entries(TIPI).map(([k, etichetta]) => (
                <button key={k} className={filtroTipo === k ? "sez attiva" : "sez"}
                        onClick={() => setFiltroTipo(k)}>{etichetta}</button>
              ))}
            </div>

            {/* Informazioni utili in evidenza */}
            {info.length > 0 && filtroTipo === "" && (
              <div className="blocco-info">
                <h3 className="titolo-colonna">Informazioni utili</h3>
                {info.map((v) => <VoceCard key={v.id} voce={v} io={io} gestisco={gestisco} azione={azione} />)}
              </div>
            )}

            {/* Nuova voce */}
            <form className="form-voce" onSubmit={aggiungiVoce}>
              <div className="riga-voce">
                <select value={vTipo} onChange={(e) => setVTipo(e.target.value)}>
                  {Object.entries(TIPI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                {vTipo === "lavoro" && (
                  <select value={vStato} onChange={(e) => setVStato(e.target.value)}>
                    {Object.entries(STATI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                )}
                <input placeholder="Titolo…" value={vTitolo}
                       onChange={(e) => setVTitolo(e.target.value)} required />
              </div>
              <textarea placeholder="Descrizione (facoltativa)…" rows={2} value={vTesto}
                        onChange={(e) => setVTesto(e.target.value)} />
              <div className="riga-voce piazzamento">
                <label className="spunta">
                  <input type="checkbox" checked={vGenerale}
                         onChange={(e) => setVGenerale(e.target.checked)} />
                  Nella parte generale
                </label>
                {scheda.sezioni.map((s) => (
                  <label key={s.id} className="spunta">
                    <input type="checkbox" checked={vSezioni.includes(s.id)}
                           onChange={() => alternaSezioneNuovaVoce(s.id)} />
                    {s.nome}
                  </label>
                ))}
                <button type="submit" className="principale piccolo">Aggiungi</button>
              </div>
            </form>

            {/* Storico */}
            {cronologia.length === 0 ? (
              <p className="vuoto">Niente da mostrare con questi filtri.</p>
            ) : (
              <ul className="lista-lavori">
                {cronologia.map((v) => (
                  <VoceCard key={v.id} voce={v} io={io} gestisco={gestisco} azione={azione} />
                ))}
              </ul>
            )}
          </>
        )}
      </main>
    </div>
  );
}

// Una riga dello storico.
function VoceCard({ voce, io, gestisco, azione }) {
  const mia = io && voce.autore && voce.autore.id === io.id;
  const posso = mia || gestisco;

  return (
    <li className={`lavoro voce-macchina tipo-${voce.tipo}`}>
      <div className="lavoro-testa">
        <span className="lavoro-titolo">{voce.titolo}</span>
        <div className="lavoro-azioni">
          {voce.tipo === "lavoro" && (
            <select className={`stato-select stato-${voce.stato}`} value={voce.stato || "da_fare"}
                    disabled={!posso}
                    onChange={(e) => azione(() => api.modificaVoce(voce.id, { stato: e.target.value }))}>
              {Object.entries(STATI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          )}
          {posso && (
            <button className="azione-icona elimina" title="Elimina voce"
                    onClick={() => {
                      if (window.confirm(`Eliminare "${voce.titolo}"?`))
                        azione(() => api.eliminaVoce(voce.id));
                    }}>🗑</button>
          )}
        </div>
      </div>

      <div className="lavoro-meta">
        <span className={`prio tipo-badge-${voce.tipo}`}>{TIPI[voce.tipo]}</span>
        <span className="data-voce">
          {new Date(voce.creato_il).toLocaleDateString("it-IT")}
          {voce.autore && <> · {voce.autore.nome}</>}
        </span>
        {voce.in_generale && <span className="chip piccolo">generale</span>}
        {voce.sezioni.map((s) => <span key={s.id} className="chip piccolo">{s.nome}</span>)}
      </div>

      {voce.testo && <p className="testo-voce">{voce.testo}</p>}

      <Allegati allegati={voce.allegati}
                onAggiungi={(d) => azione(() => api.allegaVoce(voce.id, d))}
                onElimina={(id) => azione(() => api.eliminaAllegato(id))} />
    </li>
  );
}
