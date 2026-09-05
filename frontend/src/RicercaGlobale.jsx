import { useState, useEffect, useRef } from "react";
import { api } from "./api.js";
import { dalServer } from "./date.js";

// La ricerca che attraversa tutta l'app, dalla barra in alto.
//
// Le ricerche che c'erano prima sono legate a un posto: dentro i lavori di UN
// progetto, dentro lo storico di UNA macchina. Servono quando si sa gia' dove
// guardare. Questa serve quando non si sa: ci si ricorda "la valvola V7" e non
// in quale progetto, su che macchina o in che riunione se ne era parlato.
export default function RicercaGlobale({ onVaiAlLavoro, onVaiAlProgetto,
                                         onVaiAllaMacchina, onVaiAllAgenda }) {
  const [testo, setTesto] = useState("");
  const [risultati, setRisultati] = useState(null);
  const [cercando, setCercando] = useState(false);
  const contenitore = useRef(null);

  // Si aspetta la fine della digitazione: scrivere "valvola" non deve far
  // partire sette richieste, e questa ne costa cinque query al server.
  useEffect(() => {
    if (testo.trim().length < 2) { setRisultati(null); return; }
    let annullato = false;
    setCercando(true);
    const timer = setTimeout(async () => {
      try {
        const r = await api.cercaDappertutto(testo.trim());
        if (!annullato) setRisultati(r);
      } catch {
        if (!annullato) setRisultati(null);
      } finally {
        if (!annullato) setCercando(false);
      }
    }, 350);
    return () => { annullato = true; clearTimeout(timer); };
  }, [testo]);

  useEffect(() => {
    function fuori(e) {
      if (contenitore.current && !contenitore.current.contains(e.target)) setRisultati(null);
    }
    function tasto(e) { if (e.key === "Escape") { setRisultati(null); setTesto(""); } }
    document.addEventListener("mousedown", fuori);
    document.addEventListener("keydown", tasto);
    return () => {
      document.removeEventListener("mousedown", fuori);
      document.removeEventListener("keydown", tasto);
    };
  }, []);

  function vai(azione) {
    setRisultati(null);
    setTesto("");
    azione();
  }

  const quanti = risultati
    ? Object.values(risultati).reduce((somma, elenco) => somma + elenco.length, 0)
    : 0;

  return (
    <div className="ricerca-globale" ref={contenitore}>
      <input
        type="search"
        placeholder="Cerca dappertutto…"
        value={testo}
        onChange={(e) => setTesto(e.target.value)}
        aria-label="Cerca in progetti, lavori, macchine, storico e agenda"
      />

      {risultati && (
        <div className="risultati-ricerca">
          {quanti === 0 ? (
            <p className="vuoto piccolo">
              {cercando ? "Cerco…" : `Niente trovato per "${testo}".`}
            </p>
          ) : (
            <>
              <Gruppo titolo="Progetti" voci={risultati.progetti}
                      chiave={(p) => p.id} etichetta={(p) => p.nome}
                      onScegli={(p) => vai(() => onVaiAlProgetto(p.id))} />

              <Gruppo titolo="Lavori" voci={risultati.lavori}
                      chiave={(l) => l.id} etichetta={(l) => l.titolo}
                      dettaglio={(l) => l.progetto}
                      onScegli={(l) => vai(() => onVaiAlLavoro(l.id))} />

              <Gruppo titolo="Macchine" voci={risultati.macchine}
                      chiave={(m) => m.id} etichetta={(m) => m.nome}
                      onScegli={(m) => vai(() => onVaiAllaMacchina(m.id))} />

              <Gruppo titolo="Storico macchine" voci={risultati.voci}
                      chiave={(v) => v.id} etichetta={(v) => v.titolo}
                      dettaglio={(v) => v.macchina}
                      onScegli={(v) => vai(() => onVaiAllaMacchina(v.macchina_id))} />

              <Gruppo titolo="Agenda" voci={risultati.impegni}
                      chiave={(i) => i.id} etichetta={(i) => i.titolo}
                      dettaglio={(i) => dalServer(i.inizio).toLocaleDateString("it-IT")}
                      onScegli={() => vai(() => onVaiAllAgenda())} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

// Un blocco di risultati dello stesso tipo. Non si disegna se e' vuoto: uno
// schermo pieno di intestazioni senza niente sotto fa solo scorrere di piu'.
function Gruppo({ titolo, voci, chiave, etichetta, dettaglio, onScegli }) {
  if (!voci || voci.length === 0) return null;
  return (
    <div className="gruppo-risultati">
      <span className="titolo-colonna">{titolo}</span>
      <ul>
        {voci.map((v) => (
          <li key={chiave(v)}>
            <button onClick={() => onScegli(v)}>
              <span className="risultato-titolo">{etichetta(v)}</span>
              {dettaglio && dettaglio(v) && (
                <span className="risultato-dove">{dettaglio(v)}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
