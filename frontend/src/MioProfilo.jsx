import { useState, useEffect, useRef } from "react";
import { api } from "./api.js";
import { temaCorrente, impostaTema } from "./tema.js";

// Il menu del proprio account, aperto cliccando il nome nella barra.
// Sta qui e non nel pannello Utenti (che e' solo per l'admin) perche'
// scaricare i propri dati e' un diritto di chiunque, non un privilegio.
export default function MioProfilo({ io }) {
  const [aperto, setAperto] = useState(false);
  const [tema, setTema] = useState(temaCorrente);
  const [errore, setErrore] = useState(null);
  const [scaricando, setScaricando] = useState(false);
  const contenitore = useRef(null);

  useEffect(() => {
    if (!aperto) return;
    function fuori(e) {
      if (contenitore.current && !contenitore.current.contains(e.target)) setAperto(false);
    }
    document.addEventListener("mousedown", fuori);
    return () => document.removeEventListener("mousedown", fuori);
  }, [aperto]);

  // Il browser scarica il file da solo: creo un indirizzo temporaneo che punta
  // al contenuto tenuto in memoria e faccio finta di cliccarlo.
  async function scarica() {
    setErrore(null);
    setScaricando(true);
    try {
      const dati = await api.esportaMieiDati();
      const blob = new Blob([JSON.stringify(dati, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `coordsync-mieidati-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) { setErrore(err.message); }
    finally { setScaricando(false); }
  }

  if (!io) return null;

  return (
    <div className="mio-profilo" ref={contenitore}>
      <button className="mio-ruolo bottone-profilo" onClick={() => setAperto((a) => !a)}
              title="Il tuo account">
        {io.nome} · {io.ruolo}
      </button>

      {aperto && (
        <div className="tendina-avvisi tendina-profilo">
          <div className="testa-avvisi">
            <span className="titolo-colonna">Il tuo account</span>
          </div>
          <div className="corpo-profilo">
            <div className="riga-tema">
              <span className="tenue">Aspetto</span>
              <button className="bottone-tema"
                      onClick={() => setTema(impostaTema(tema === "scuro" ? "chiaro" : "scuro"))}>
                {tema === "scuro" ? "🌙 Scuro" : "☀️ Chiaro"}
              </button>
            </div>
            <p className="riga-profilo"><strong>{io.nome}</strong><br />{io.email}</p>
            {io.reparti && io.reparti.length > 0 && (
              <p className="riga-profilo tenue">
                Reparti: {io.reparti.map((r) => r.nome).join(", ")}
              </p>
            )}
            {errore && <p className="errore">{errore}</p>}
            <p className="vuoto piccolo">
              Puoi portarti via tutto quello che l'app sa di te: profilo, lavori
              assegnati, commenti e voci che hai scritto, agenda e avvisi.
            </p>
            <button className="principale piccolo" onClick={scarica} disabled={scaricando}>
              {scaricando ? "Preparo il file…" : "Scarica i miei dati"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
