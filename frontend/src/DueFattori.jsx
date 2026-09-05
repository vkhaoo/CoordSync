import { useState, useEffect } from "react";
import { api } from "./api.js";

// Accendere e spegnere il secondo fattore, dal menu del proprio nome.
//
// Il percorso e' in tre passi di proposito: si genera il segreto, lo si mette
// nell'app del telefono, e si dimostra che funziona scrivendo un codice.
// Accenderlo prima della prova vorrebbe dire rischiare di chiudersi fuori da
// soli per un telefono configurato male.
export default function DueFattori() {
  const [stato, setStato] = useState(null);      // { attivo, codici_recupero_rimasti }
  const [passo, setPasso] = useState("fermo");   // fermo | configuro | fatto | spengo
  const [preparato, setPreparato] = useState(null);
  const [codice, setCodice] = useState("");
  const [password, setPassword] = useState("");
  const [codiciRecupero, setCodiciRecupero] = useState(null);
  const [errore, setErrore] = useState(null);

  useEffect(() => {
    api.statoDueFattori().then(setStato).catch(() => setStato(null));
  }, []);

  async function prepara() {
    setErrore(null);
    try {
      setPreparato(await api.preparaDueFattori());
      setPasso("configuro");
    } catch (err) { setErrore(err.message); }
  }

  async function attiva(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const r = await api.attivaDueFattori(codice);
      setCodiciRecupero(r.codici);
      setCodice("");
      setPasso("fatto");
      setStato(await api.statoDueFattori());
    } catch (err) { setErrore(err.message); }
  }

  async function spegni(e) {
    e.preventDefault();
    setErrore(null);
    try {
      await api.disattivaDueFattori(password);
      setPassword("");
      setPasso("fermo");
      setPreparato(null);
      setStato(await api.statoDueFattori());
    } catch (err) { setErrore(err.message); }
  }

  if (!stato) return null;

  return (
    <div className="blocco-2fa">
      <span className="etichetta-tendina">Accesso in due passi</span>

      {errore && <p className="errore">{errore}</p>}

      {/* --- I codici di recupero, mostrati UNA volta sola --- */}
      {codiciRecupero && (
        <div className="codici-recupero">
          <p className="vuoto piccolo">
            <strong>Segnati questi codici adesso.</strong> Sono l'unico modo di
            rientrare se perdi il telefono, ognuno vale una volta sola, e non
            potrai piu' rivederli: nel database restano solo le loro impronte.
          </p>
          <ul>
            {codiciRecupero.map((c) => <li key={c}>{c}</li>)}
          </ul>
          <button className="principale piccolo"
                  onClick={() => setCodiciRecupero(null)}>Li ho salvati</button>
        </div>
      )}

      {/* --- Acceso --- */}
      {!codiciRecupero && stato.attivo && passo !== "spengo" && (
        <>
          <p className="vuoto piccolo">
            Acceso. Per entrare servono la password e il codice del telefono.
            Ti restano <strong>{stato.codici_recupero_rimasti}</strong> codici
            di recupero.
          </p>
          <button className="link-testo" onClick={() => setPasso("spengo")}>
            Spegni il secondo fattore
          </button>
        </>
      )}

      {/* --- Spegnerlo: serve la password --- */}
      {passo === "spengo" && (
        <form className="form-inline" onSubmit={spegni}>
          <input type="password" placeholder="La tua password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit" className="mini">✓</button>
          <button type="button" className="mini annulla"
                  onClick={() => { setPasso("fermo"); setPassword(""); }}>×</button>
        </form>
      )}

      {/* --- Spento: si puo' accendere --- */}
      {!codiciRecupero && !stato.attivo && passo === "fermo" && (
        <>
          <p className="vuoto piccolo">
            Spento. Accendendolo, per entrare non bastera' piu' la password:
            servira' anche il codice che cambia ogni 30 secondi sul tuo
            telefono.
          </p>
          <button className="principale piccolo" onClick={prepara}>
            Accendi il secondo fattore
          </button>
        </>
      )}

      {/* --- Configurazione --- */}
      {passo === "configuro" && preparato && (
        <>
          <p className="vuoto piccolo">
            Apri la tua app di autenticazione e aggiungi questo codice a mano,
            oppure tocca il collegamento se sei da telefono.
          </p>
          <code className="segreto-2fa">{preparato.segreto}</code>
          <p>
            <a href={preparato.uri} className="doc-link">Apri nell'app dei codici</a>
          </p>
          <form className="form-inline" onSubmit={attiva}>
            <input placeholder="Le sei cifre" value={codice} inputMode="numeric"
                   onChange={(e) => setCodice(e.target.value)} required />
            <button type="submit" className="mini">✓</button>
            <button type="button" className="mini annulla"
                    onClick={() => { setPasso("fermo"); setCodice(""); }}>×</button>
          </form>
        </>
      )}
    </div>
  );
}
