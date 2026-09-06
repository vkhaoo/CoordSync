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

// I sette giorni della settimana che contiene questa data, da lunedi'.
function celleDellaSettimana(data) {
  const sfasamento = (data.getDay() + 6) % 7;   // 0 = lunedi'
  const lunedi = new Date(data.getFullYear(), data.getMonth(), data.getDate() - sfasamento);
  return Array.from({ length: 7 }, (_, i) =>
    new Date(lunedi.getFullYear(), lunedi.getMonth(), lunedi.getDate() + i));
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
  const [vista, setVista] = useState("mese");   // "mese", "settimana" o "giorno"
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
  const [partecipanti, setPartecipanti] = useState([]);   // [] = solo io
  const [ripeti, setRipeti] = useState("");        // "" = una volta sola
  const [ripetiFino, setRipetiFino] = useState("");

  const coordino = io && (io.ruolo === "admin" || io.ruolo === "caposquadra");

  // Le celle da disegnare dipendono da come si sta guardando l'agenda.
  //
  // Il MESE serve a pianificare, la SETTIMANA a lavorare (e' l'unica in cui si
  // legge davvero cosa c'e' ogni giorno), il GIORNO a chi in cantiere vuole
  // solo sapere cosa fa adesso. La griglia e' la stessa, cambia quanti giorni
  // ci stanno dentro: nel giorno non c'e' proprio, perche' il dettaglio qui
  // sotto dice gia' tutto.
  const scelta = new Date(giornoScelto + "T00:00:00");
  const celle = vista === "mese" ? celleDelMese(anno, mese)
              : vista === "settimana" ? celleDellaSettimana(scelta)
              : [];

  async function carica() {
    setErrore(null);
    try {
      // Nel giorno non ci sono celle: si chiede quel giorno soltanto.
      const dal = celle.length ? aChiave(celle[0]) : giornoScelto;
      const al = celle.length ? aChiave(celle[celle.length - 1]) : giornoScelto;
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

  useEffect(() => { carica(); }, [anno, mese, ambito, vista, giornoScelto]);

  // Le frecce spostano di quello che si sta guardando: un mese, una settimana
  // o un giorno. Un'unica funzione, se no le tre viste si comporterebbero in
  // tre modi diversi e ci si perde.
  function sposta(delta) {
    if (vista === "mese") {
      const d = new Date(anno, mese + delta, 1);
      setAnno(d.getFullYear());
      setMese(d.getMonth());
      return;
    }
    const passo = vista === "settimana" ? 7 : 1;
    const d = new Date(scelta.getFullYear(), scelta.getMonth(),
                       scelta.getDate() + passo * delta);
    setGiornoScelto(aChiave(d));
    // Cambiando settimana si puo' finire nel mese dopo: il titolo deve
    // seguire, se no dice ancora "Marzo" mentre si guarda aprile.
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
      // Vuoto = solo io. Con altri dentro diventa una riunione: un impegno
      // solo, che compare nell'agenda di tutti.
      if (partecipanti.length > 0) corpo.partecipanti_ids = [io.id, ...partecipanti];
      if (ripeti) {
        corpo.ripeti = ripeti;
        // Il server pretende una fine, e ha ragione: senza, si genererebbero
        // righe fino alla fine dei tempi.
        corpo.ripeti_fino = `${ripetiFino}T23:59:00`;
      }
      await api.creaImpegno(corpo);
      setTitolo(""); setLuogo(""); setNote(""); setOraFine(""); setPartecipanti([]);
      setRipeti(""); setRipetiFino("");
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  async function elimina(impegno) {
    // Su un impegno che si ripete si CHIEDE cosa si vuole togliere, invece di
    // decidere per conto proprio: le due cose sono molto diverse, e una delle
    // due non si rimedia.
    let tuttaLaSerie = false;
    if (impegno.serie_id) {
      const risposta = window.prompt(
        [`"${impegno.titolo}" si ripete.`,
         "",
         "Scrivi UNO per togliere solo questo giorno,",
         "oppure TUTTI per togliere l'intera ripetizione."].join("\n"),
        "UNO");
      if (!risposta) return;
      const scelta = risposta.trim().toUpperCase();
      if (scelta !== "UNO" && scelta !== "TUTTI") return;
      tuttaLaSerie = scelta === "TUTTI";
    } else if (!window.confirm(`Eliminare "${impegno.titolo}"?`)) {
      return;
    }

    setErrore(null);
    try { await api.eliminaImpegno(impegno.id, tuttaLaSerie); await carica(); }
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
          <button className="mini annulla" onClick={() => sposta(-1)}>‹</button>
          <h2 className="titolo-progetto">
            {vista === "giorno"
              ? scelta.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })
              : vista === "settimana"
                ? `Settimana del ${celle[0].getDate()} ${MESI[celle[0].getMonth()]}`
                : `${MESI[mese]} ${anno}`}
          </h2>
          <button className="mini annulla" onClick={() => sposta(1)}>›</button>
          <button className="sez" onClick={() => {
            const o = new Date();
            setAnno(o.getFullYear()); setMese(o.getMonth()); setGiornoScelto(aChiave(o));
          }}>Oggi</button>
        </div>

        <div className="barra-sezioni">
          {[["mese", "Mese"], ["settimana", "Settimana"], ["giorno", "Giorno"]].map(([k, e]) => (
            <button key={k} className={vista === k ? "sez attiva" : "sez"}
                    onClick={() => setVista(k)}>{e}</button>
          ))}
        </div>
        <div className="barra-sezioni">
          {[["miei", "I miei"], ["reparto", "Il mio reparto"], ["azienda", "Tutta l'azienda"]].map(([k, e]) => (
            <button key={k} className={ambito === k ? "sez attiva" : "sez"}
                    onClick={() => setAmbito(k)}>{e}</button>
          ))}
        </div>
      </div>

      {celle.length > 0 && (
      <div className={vista === "settimana" ? "calendario settimana" : "calendario"}>
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
      )}

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
                {(i.organizzatore.id === io.id || coordino) && (
                  <div className="lavoro-azioni">
                    <button className="azione-icona elimina" title="Elimina impegno"
                            onClick={() => elimina(i)}>🗑</button>
                  </div>
                )}
              </div>
              <div className="lavoro-meta">
                {i.partecipanti.length > 1 ? (
                  // Riunione: mostro chi c'e', cosi' si vede a colpo d'occhio.
                  i.partecipanti.map((p) => (
                    <span key={p.id} className={p.id === io.id ? "chip piccolo tu" : "chip piccolo"}>
                      {p.nome}{p.id === io.id ? " (tu)" : ""}
                    </span>
                  ))
                ) : ambito !== "miei" ? (
                  <span className="chip piccolo">{i.partecipanti[0]?.nome ?? i.organizzatore.nome}</span>
                ) : null}
                {i.luogo && <span className="data-voce">📍 {i.luogo}</span>}
                {i.promemoria_minuti && (
                  <span className="chip piccolo">promemoria {i.promemoria_minuti} min prima</span>
                )}
                {i.serie_id && <span className="chip piccolo">si ripete</span>}
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
          </div>
          {coordino && utenti.length > 1 && (
            <div className="riga-voce piazzamento">
              <span className="etichetta-reparti">Anche in agenda a</span>
              {utenti.filter((u) => u.id !== io.id).map((u) => (
                <button type="button" key={u.id}
                        className={partecipanti.includes(u.id) ? "sez attiva" : "sez"}
                        onClick={() => setPartecipanti((p) =>
                          p.includes(u.id) ? p.filter((x) => x !== u.id) : [...p, u.id])}>
                  {u.nome}
                </button>
              ))}
            </div>
          )}
          <div className="riga-voce">
            <select value={ripeti} onChange={(e) => setRipeti(e.target.value)}
                    title="Ripetizione">
              <option value="">Una volta sola</option>
              <option value="settimanale">Ogni settimana</option>
              <option value="quindicinale">Ogni due settimane</option>
              <option value="quattro_settimane">Ogni quattro settimane</option>
              <option value="mensile">Ogni mese</option>
            </select>
            {ripeti && (
              <input type="date" value={ripetiFino} required
                     title="Fino a quando si ripete"
                     onChange={(e) => setRipetiFino(e.target.value)} />
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
