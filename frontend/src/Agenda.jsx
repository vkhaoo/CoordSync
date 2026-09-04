import { useState, useEffect } from "react";
import { api } from "./api.js";

const GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];
const MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
              "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];

// Le date viaggiano come "AAAA-MM-GG": le costruisco a mano invece di usare
// toISOString(), che converte in UTC e nei fusi a est fa slittare il giorno.
function aChiave(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Le celle del mese, allineate a lunedì e completate con i giorni "spalla"
// del mese precedente e successivo, così la griglia resta rettangolare.
function celleDelMese(anno, mese) {
  const primo = new Date(anno, mese, 1);
  // getDay(): 0 = domenica. Lo riporto a 0 = lunedì.
  const sfasamento = (primo.getDay() + 6) % 7;
  const inizio = new Date(anno, mese, 1 - sfasamento);
  return Array.from({ length: 42 }, (_, i) =>
    new Date(inizio.getFullYear(), inizio.getMonth(), inizio.getDate() + i));
}

function oraDi(iso) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export default function Agenda({ io, utenti }) {
  const oggi = new Date();
  const [anno, setAnno] = useState(oggi.getFullYear());
  const [mese, setMese] = useState(oggi.getMonth());
  const [ambito, setAmbito] = useState("miei");
  const [giornoScelto, setGiornoScelto] = useState(aChiave(oggi));

  const [impegni, setImpegni] = useState([]);
  const [scadenze, setScadenze] = useState([]);
  const [prossimi, setProssimi] = useState([]);
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  // Form nuovo impegno
  const [titolo, setTitolo] = useState("");
  const [ora, setOra] = useState("09:00");
  const [oraFine, setOraFine] = useState("");
  const [luogo, setLuogo] = useState("");
  const [note, setNote] = useState("");
  const [promemoria, setPromemoria] = useState("");
  const [perChi, setPerChi] = useState("");

  const coordino = io && (io.ruolo === "admin" || io.ruolo === "caposquadra");
  const celle = celleDelMese(anno, mese);

  async function carica() {
    setErrore(null);
    try {
      const dal = aChiave(celle[0]);
      const al = aChiave(celle[celle.length - 1]);
      const [dati, p] = await Promise.all([
        api.agenda(dal, al, ambito),
        api.prossimiImpegni(7),
      ]);
      setImpegni(dati.impegni);
      setScadenze(dati.scadenze);
      setProssimi(p);
    } catch (e) { setErrore(e.message); }
    finally { setCaricando(false); }
  }

  useEffect(() => { carica(); }, [anno, mese, ambito]);

  function cambiaMese(delta) {
    const d = new Date(anno, mese + delta, 1);
    setAnno(d.getFullYear());
    setMese(d.getMonth());
  }

  // Raggruppo per giorno una volta sola, invece di rifiltrare in ogni cella.
  const perGiorno = {};
  for (const i of impegni) {
    const k = aChiave(new Date(i.inizio));
    (perGiorno[k] ??= { impegni: [], scadenze: [] }).impegni.push(i);
  }
  for (const s of scadenze) {
    (perGiorno[s.data_scadenza] ??= { impegni: [], scadenze: [] }).scadenze.push(s);
  }

  const delGiorno = perGiorno[giornoScelto] ?? { impegni: [], scadenze: [] };

  async function aggiungi(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const corpo = {
        titolo,
        inizio: `${giornoScelto}T${ora}:00`,
        fine: oraFine ? `${giornoScelto}T${oraFine}:00` : null,
        luogo: luogo || null,
        note: note || null,
        promemoria_minuti: promemoria ? Number(promemoria) : null,
      };
      if (perChi) corpo.utente_id = Number(perChi);
      await api.creaImpegno(corpo);
      setTitolo(""); setLuogo(""); setNote(""); setOraFine(""); setPerChi("");
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  async function elimina(id) {
    setErrore(null);
    try { await api.eliminaImpegno(id); await carica(); }
    catch (err) { setErrore(err.message); }
  }

  if (caricando) return <p className="vuoto" style={{ padding: "1.5rem" }}>Caricamento…</p>;

  return (
    <div className="corpo-singolo agenda">
      {errore && <p className="errore">{errore}</p>}

      {/* Promemoria che funziona senza servizi esterni: cosa ho in arrivo */}
      {prossimi.length > 0 && (
        <div className="blocco-info prossimi">
          <h3 className="titolo-colonna">I tuoi prossimi 7 giorni</h3>
          <ul className="lista-prossimi">
            {prossimi.map((i) => (
              <li key={i.id}>
                <strong>{new Date(i.inizio).toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "short" })}</strong>
                {" "}alle {oraDi(i.inizio)} · {i.titolo}
                {i.luogo && <span className="tenue"> — {i.luogo}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="testa-agenda">
        <div className="navigazione-mese">
          <button className="mini annulla" onClick={() => cambiaMese(-1)}>‹</button>
          <h2 className="titolo-progetto">{MESI[mese]} {anno}</h2>
          <button className="mini annulla" onClick={() => cambiaMese(1)}>›</button>
          <button className="sez" onClick={() => {
            const o = new Date();
            setAnno(o.getFullYear()); setMese(o.getMonth()); setGiornoScelto(aChiave(o));
          }}>Oggi</button>
        </div>
        <div className="barra-sezioni">
          {[["miei", "I miei"], ["reparto", "Il mio reparto"], ["azienda", "Tutta l'azienda"]].map(([k, e]) => (
            <button key={k} className={ambito === k ? "sez attiva" : "sez"}
                    onClick={() => setAmbito(k)}>{e}</button>
          ))}
        </div>
      </div>

      <div className="calendario">
        {GIORNI.map((g) => <div key={g} className="intestazione-giorno">{g}</div>)}
        {celle.map((d) => {
          const k = aChiave(d);
          const dati = perGiorno[k] ?? { impegni: [], scadenze: [] };
          const fuoriMese = d.getMonth() !== mese;
          const eOggi = k === aChiave(oggi);
          return (
            <button key={k}
                    className={`cella${fuoriMese ? " fuori" : ""}${eOggi ? " oggi" : ""}${k === giornoScelto ? " scelto" : ""}`}
                    onClick={() => setGiornoScelto(k)}>
              <span className="numero-giorno">{d.getDate()}</span>
              {dati.impegni.slice(0, 2).map((i) => (
                <span key={i.id} className="pillola impegno">{oraDi(i.inizio)} {i.titolo}</span>
              ))}
              {dati.impegni.length > 2 && (
                <span className="pillola altro">+{dati.impegni.length - 2}</span>
              )}
              {dati.scadenze.map((s) => (
                <span key={s.lavoro_id} className="pillola scadenza-pillola">⏱ {s.titolo}</span>
              ))}
            </button>
          );
        })}
      </div>

      {/* Dettaglio del giorno scelto */}
      <div className="dettaglio-giorno">
        <h3 className="titolo-colonna">
          {new Date(giornoScelto + "T00:00:00").toLocaleDateString("it-IT",
            { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </h3>

        {delGiorno.impegni.length === 0 && delGiorno.scadenze.length === 0 && (
          <p className="vuoto">Niente in programma.</p>
        )}

        <ul className="lista-lavori">
          {delGiorno.impegni.map((i) => (
            <li key={i.id} className="lavoro impegno-card">
              <div className="lavoro-testa">
                <span className="lavoro-titolo">
                  <span className="ora">{oraDi(i.inizio)}{i.fine && `–${oraDi(i.fine)}`}</span>
                  {" "}{i.titolo}
                </span>
                {(i.utente.id === io.id || coordino) && (
                  <div className="lavoro-azioni">
                    <button className="azione-icona elimina" title="Elimina impegno"
                            onClick={() => { if (window.confirm(`Eliminare "${i.titolo}"?`)) elimina(i.id); }}>🗑</button>
                  </div>
                )}
              </div>
              <div className="lavoro-meta">
                {ambito !== "miei" && <span className="chip piccolo">{i.utente.nome}</span>}
                {i.luogo && <span className="data-voce">📍 {i.luogo}</span>}
                {i.promemoria_minuti && (
                  <span className="chip piccolo">promemoria {i.promemoria_minuti} min prima</span>
                )}
              </div>
              {i.note && <p className="testo-voce">{i.note}</p>}
            </li>
          ))}

          {delGiorno.scadenze.map((s) => (
            <li key={`s${s.lavoro_id}`} className="lavoro scadenza-card">
              <div className="lavoro-testa">
                <span className="lavoro-titolo">⏱ {s.titolo}</span>
              </div>
              <div className="lavoro-meta">
                <span className="chip piccolo">scadenza · {s.progetto}</span>
                {s.mia && <span className="chip piccolo">assegnata a te</span>}
              </div>
            </li>
          ))}
        </ul>

        <form className="form-voce" onSubmit={aggiungi}>
          <div className="riga-voce">
            <input type="time" value={ora} onChange={(e) => setOra(e.target.value)} required />
            <input type="time" value={oraFine} title="Fine (facoltativa)"
                   onChange={(e) => setOraFine(e.target.value)} />
            <input placeholder="Cosa devi fare…" value={titolo}
                   onChange={(e) => setTitolo(e.target.value)} required />
          </div>
          <div className="riga-voce">
            <input placeholder="Dove (facoltativo)…" value={luogo}
                   onChange={(e) => setLuogo(e.target.value)} />
            <select value={promemoria} onChange={(e) => setPromemoria(e.target.value)}
                    title="Promemoria">
              <option value="">Nessun promemoria</option>
              <option value="30">30 minuti prima</option>
              <option value="60">1 ora prima</option>
              <option value="180">3 ore prima</option>
              <option value="1440">Il giorno prima</option>
            </select>
            {coordino && (
              <select value={perChi} onChange={(e) => setPerChi(e.target.value)}
                      title="In agenda a chi">
                <option value="">Nella mia agenda</option>
                {utenti.filter((u) => u.id !== io.id).map((u) => (
                  <option key={u.id} value={u.id}>Agenda di {u.nome}</option>
                ))}
              </select>
            )}
          </div>
          <textarea placeholder="Note (facoltative)…" rows={2} value={note}
                    onChange={(e) => setNote(e.target.value)} />
          <div className="riga-voce">
            <button type="submit" className="principale piccolo">Aggiungi impegno</button>
          </div>
        </form>
      </div>
    </div>
  );
}
