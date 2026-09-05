import { useState, useEffect } from "react";
import { api } from "./api.js";
import SelettoreReparti from "./SelettoreReparti.jsx";
import Allegati from "./Allegati.jsx";
import CampoRicerca from "./CampoRicerca.jsx";
import Tendina from "./Tendina.jsx";
import { dalServer } from "./date.js";

// Etichette dei tipi di voce. "informazione" e' a parte: non e' un fatto
// avvenuto in una data, e' sapere di riferimento che resta valido.
const TIPI = {
  lavoro: "Lavoro",
  modifica: "Modifica",
  analisi: "Analisi",
  informazione: "Informazione utile",
};
const STATI = { da_fare: "Da fare", in_corso: "In corso", fatto: "Fatto" };

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
  const [cerca, setCerca] = useState("");                  // ricerca nello storico
  const [filtroMacchine, setFiltroMacchine] = useState(""); // filtro sui nomi, in locale

  // Form
  const [nuovaMacchina, setNuovaMacchina] = useState("");
  const [nuovaSezione, setNuovaSezione] = useState("");
  // Anche qui: si apre la scheda per leggere lo storico, non per scriverci.
  const [creaVoceAperta, setCreaVoceAperta] = useState(false);
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
    if (cerca) q.push(`q=${encodeURIComponent(cerca)}`);
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
  }, [selezionata, filtroTipo, filtroSezione, cerca]);

  async function azione(fn) {
    setErrore(null);
    try { await fn(); await caricaScheda(selezionata); }
    catch (err) { setErrore(err.message); }
  }

  // Sposta una sezione di un posto a sinistra (-1) o a destra (+1).
  // Costruisco la lista nuova per intero e la mando cosi': il server la
  // accetta tutta o la rifiuta tutta, senza ordini salvati a meta'.
  function spostaSezione(indice, verso) {
    const ids = scheda.sezioni.map((s) => s.id);
    const arrivo = indice + verso;
    if (arrivo < 0 || arrivo >= ids.length) return;
    [ids[indice], ids[arrivo]] = [ids[arrivo], ids[indice]];
    azione(() => api.riordinaSezioni(scheda.id, ids));
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
      <main className="area-lavori">
        {errore && <p className="errore">{errore}</p>}

        {/* Scelta della macchina: un menu, con dentro anche il modo di
            aggiungerne una. Prima era una colonna sempre aperta. */}
        <div className="barra-scelte">
          <Tendina etichetta="Macchina"
                   valore={scheda ? scheda.nome : null}
                   vuoto={macchine.length ? "Scegli una macchina" : "Nessuna macchina"}>
            {(chiudi) => (
              <>
                {macchine.length > 6 && (
                  <CampoRicerca valore={filtroMacchine} onCambia={setFiltroMacchine}
                                segnaposto="Filtra macchine…" attesa={0} />
                )}
                {macchine.length === 0 && (
                  <p className="vuoto piccolo">Nessuna macchina ancora.</p>
                )}
                <ul className="lista-progetti">
                  {macchine
                    .filter((m) => m.nome.toLowerCase().includes(filtroMacchine.toLowerCase()))
                    .map((m) => (
                      <li key={m.id}>
                        <button className={m.id === selezionata ? "voce attiva" : "voce"}
                                onClick={() => { setSelezionata(m.id); chiudi(); }}>{m.nome}</button>
                      </li>
                    ))}
                </ul>
                {gestisco && (
                  <div className="separatore-tendina">
                    <form className="form-inline" onSubmit={async (e) => {
                      await aggiungiMacchina(e);
                      chiudi();
                    }}>
                      <input placeholder="Crea macchina…" value={nuovaMacchina}
                             onChange={(e) => setNuovaMacchina(e.target.value)} required />
                      <button type="submit" className="mini">+</button>
                    </form>
                  </div>
                )}
              </>
            )}
          </Tendina>
        </div>

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

              <SelettoreReparti reparti={reparti}
                                selezionati={scheda.reparti}
                                modificabile={gestisco}
                                onCambia={(ids) => azione(async () => {
                                  await api.modificaMacchina(scheda.id, { reparti_ids: ids });
                                  await caricaMacchine();   // potrei non vederla piu'
                                })} />

              <Allegati allegati={scheda.allegati}
                        onAggiungi={(d) => azione(() => api.allegaMacchina(scheda.id, d))}
                        onElimina={(id) => azione(() => api.eliminaAllegato(id))} />
            </div>

            {/* Sezioni della macchina: sono anche il filtro dello storico.
                Dentro lo stesso menu c'e' tutto quello che le riguarda:
                sceglierne una, spostarle, crearne una, eliminarne una. */}
            <div className="barra-scelte">
              <Tendina etichetta="Sezione"
                       valore={filtroSezione === ""
                         ? "Tutta la macchina"
                         : (scheda.sezioni.find((s) => String(s.id) === String(filtroSezione)) || {}).nome}>
                {(chiudi) => (
                  <>
                    <ul className="lista-progetti">
                      <li>
                        <button className={filtroSezione === "" ? "voce attiva" : "voce"}
                                onClick={() => { setFiltroSezione(""); chiudi(); }}>
                          Tutta la macchina
                        </button>
                      </li>
                      {scheda.sezioni.map((s, i) => (
                        <li key={s.id} className="riga-sezione">
                          <button className={String(filtroSezione) === String(s.id) ? "voce attiva" : "voce"}
                                  onClick={() => { setFiltroSezione(s.id); chiudi(); }}>{s.nome}</button>
                          {gestisco && (
                            <span className="comandi-sezione">
                              {scheda.sezioni.length > 1 && (
                                <>
                                  <button className="chip-sposta" title="Sposta prima"
                                          disabled={i === 0}
                                          onClick={() => spostaSezione(i, -1)}>‹</button>
                                  <button className="chip-sposta" title="Sposta dopo"
                                          disabled={i === scheda.sezioni.length - 1}
                                          onClick={() => spostaSezione(i, +1)}>›</button>
                                </>
                              )}
                              <button className="chip-x" title="Elimina sezione (le voci restano)"
                                      onClick={() => {
                                        if (window.confirm(`Eliminare la sezione "${s.nome}"? Le voci restano nella macchina.`)) {
                                          if (String(filtroSezione) === String(s.id)) setFiltroSezione("");
                                          azione(() => api.eliminaSezione(s.id));
                                        }
                                      }}>×</button>
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>

                    {gestisco && (
                      <div className="separatore-tendina">
                        <form className="form-inline" onSubmit={(e) => {
                          e.preventDefault();
                          azione(async () => {
                            await api.creaSezione(scheda.id, { nome: nuovaSezione });
                            setNuovaSezione("");
                          });
                          // Il menu resta aperto: le sezioni si creano quasi
                          // sempre a raffica, una dietro l'altra.
                        }}>
                          <input placeholder="Crea sezione…" value={nuovaSezione}
                                 onChange={(e) => setNuovaSezione(e.target.value)} required />
                          <button type="submit" className="mini">+</button>
                        </form>
                      </div>
                    )}
                  </>
                )}
              </Tendina>
            </div>

            {/* Quando sono dentro una sezione: i link di QUELLA sezione.
                Prima non c'era modo di appenderli, pur essendo previsti. */}
            {filtroSezione !== "" && (() => {
              const sez = scheda.sezioni.find((s) => String(s.id) === String(filtroSezione));
              if (!sez) return null;
              return (
                <div className="pannello-sezione">
                  <span className="etichetta-reparti">Link della sezione {sez.nome}</span>
                  <Allegati allegati={sez.allegati}
                            onAggiungi={(d) => azione(() => api.allegaSezione(sez.id, d))}
                            onElimina={(id) => azione(() => api.eliminaAllegato(id))} />
                </div>
              );
            })()}

            {/* Ricerca nello storico: con anni di voci e' l'unico modo pratico
                di ritrovare quella volta che si era rotta la valvola. */}
            <CampoRicerca valore={cerca} onCambia={setCerca}
                          segnaposto="Cerca nello storico (titolo o descrizione)…" />

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

            {/* Nuova voce: dietro un pulsante, era il blocco piu' ingombrante
                della pagina e stava aperto anche quando si leggeva soltanto. */}
            {!creaVoceAperta && (
              <button className="principale piccolo bottone-crea"
                      onClick={() => setCreaVoceAperta(true)}>+ Nuova voce</button>
            )}
            {creaVoceAperta && (
            <form className="form-voce" onSubmit={async (e) => {
              await aggiungiVoce(e);
              setCreaVoceAperta(false);
            }}>
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
                <button type="button" className="mini annulla" title="Chiudi"
                        onClick={() => setCreaVoceAperta(false)}>×</button>
              </div>
            </form>
            )}

            {/* Storico */}
            {cronologia.length === 0 ? (
              <p className="vuoto">{cerca
                ? `Niente trovato per "${cerca}".`
                : "Niente da mostrare con questi filtri."}</p>
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
          {dalServer(voce.creato_il).toLocaleDateString("it-IT")}
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
