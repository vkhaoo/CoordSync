import { useState, useEffect, useRef } from "react";
import { api } from "./api.js";
import { quandoRelativo } from "./date.js";

const ICONA = { assegnazione: "👤", commento: "💬", impegno: "📅" };

// Ogni quanto ricontrollare se sono arrivati avvisi nuovi.
// Un minuto e' un compromesso: abbastanza vivo da accorgersene, abbastanza
// raro da non tempestare di richieste un server che dorme dopo 15 minuti.
const OGNI = 60_000;

export default function Campanella({ onVaiAlLavoro }) {
  const [dati, setDati] = useState({ non_lette: 0, notifiche: [] });
  const [aperta, setAperta] = useState(false);
  const contenitore = useRef(null);

  async function carica() {
    try { setDati(await api.notifiche()); }
    catch { /* la campanella non deve mai rompere la pagina */ }
  }

  useEffect(() => {
    carica();
    const timer = setInterval(carica, OGNI);
    return () => clearInterval(timer);
  }, []);

  // Cliccando fuori si chiude, come ci si aspetta da un menu a tendina.
  useEffect(() => {
    if (!aperta) return;
    function fuori(e) {
      if (contenitore.current && !contenitore.current.contains(e.target)) setAperta(false);
    }
    document.addEventListener("mousedown", fuori);
    return () => document.removeEventListener("mousedown", fuori);
  }, [aperta]);

  async function apri() {
    const prossimo = !aperta;
    setAperta(prossimo);
    if (prossimo) await carica();
  }

  async function segnaTutte() {
    try { setDati(await api.segnaTutteLette()); }
    catch { /* nulla di grave */ }
  }

  async function apriAvviso(avviso) {
    if (!avviso.letta) {
      try { await api.segnaLetta(avviso.id); } catch {}
    }
    setAperta(false);
    await carica();
    if (avviso.lavoro_id && onVaiAlLavoro) onVaiAlLavoro(avviso.lavoro_id);
  }

  return (
    <div className="campanella" ref={contenitore}>
      <button className="bottone-campanella" onClick={apri}
              title={dati.non_lette ? `${dati.non_lette} avvisi da leggere` : "Nessun avviso nuovo"}>
        🔔
        {dati.non_lette > 0 && (
          <span className="pallino-avvisi">{dati.non_lette > 99 ? "99+" : dati.non_lette}</span>
        )}
      </button>

      {aperta && (
        <div className="tendina-avvisi">
          <div className="testa-avvisi">
            <span className="titolo-colonna">Avvisi</span>
            {dati.non_lette > 0 && (
              <button className="link-testo" onClick={segnaTutte}>Segna tutti letti</button>
            )}
          </div>

          {dati.notifiche.length === 0 ? (
            <p className="vuoto piccolo" style={{ padding: "0.6rem 0.9rem" }}>
              Nessun avviso. Qui arrivano i lavori che ti assegnano, i commenti
              sui tuoi lavori e gli impegni che ti mettono in agenda.
            </p>
          ) : (
            <ul className="lista-avvisi">
              {dati.notifiche.map((n) => (
                <li key={n.id} className={n.letta ? "avviso" : "avviso non-letto"}>
                  <button className="corpo-avviso" onClick={() => apriAvviso(n)}>
                    <span className="icona-avviso">{ICONA[n.tipo] ?? "•"}</span>
                    <span className="testo-avviso">
                      {n.testo}
                      <span className="quando-avviso">{quandoRelativo(n.creato_il)}</span>
                    </span>
                  </button>
                  <button className="chip-x" title="Elimina"
                          onClick={async () => { await api.eliminaNotifica(n.id); carica(); }}>×</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
