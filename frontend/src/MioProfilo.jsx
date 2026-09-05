import { useState, useEffect, useRef } from "react";
import { api, setToken } from "./api.js";
import { temaCorrente, impostaTema } from "./tema.js";

// Il menu del proprio account, aperto cliccando il nome nella barra.
// Sta qui e non nel pannello Utenti (che e' solo per l'admin) perche'
// scaricare i propri dati e' un diritto di chiunque, non un privilegio.
export default function MioProfilo({ io, onLogout }) {
  const [aperto, setAperto] = useState(false);
  const [tema, setTema] = useState(temaCorrente);
  const [errore, setErrore] = useState(null);
  const [scaricando, setScaricando] = useState(false);
  const [aziende, setAziende] = useState([]);
  const contenitore = useRef(null);

  useEffect(() => {
    if (!aperto) return;
    function fuori(e) {
      if (contenitore.current && !contenitore.current.contains(e.target)) setAperto(false);
    }
    document.addEventListener("mousedown", fuori);
    return () => document.removeEventListener("mousedown", fuori);
  }, [aperto]);

  // Le aziende si chiedono solo all'apertura del menu: quasi tutti ne hanno
  // una sola, e non ha senso pagare una richiesta a ogni caricamento per una
  // cosa che la maggior parte delle persone non vedra' mai.
  useEffect(() => {
    if (!aperto) return;
    api.mieAziende().then(setAziende).catch(() => setAziende([]));
  }, [aperto]);

  // Cambiare azienda vuol dire ricevere un token nuovo e ricaricare tutto:
  // progetti, macchine, colleghi, permessi cambiano insieme, e ridisegnare
  // pezzo per pezzo lascerebbe per un attimo sullo schermo roba dell'altra.
  async function vaiIn(azienda) {
    setErrore(null);
    try {
      const risposta = await api.cambiaAzienda(azienda.id);
      setToken(risposta.access_token);
      window.location.reload();
    } catch (err) { setErrore(err.message); }
  }

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

  // Andarsene e' irreversibile: chiedo conferma DUE volte, e la seconda
  // obbliga a scrivere il proprio nome. Un clic distratto non deve bastare.
  async function cancellaAccount() {
    if (!window.confirm(
      "Vuoi cancellare il tuo account?\n\n" +
      "Non potrai più entrare. Quello che hai scritto (commenti, voci di " +
      "storico, lavori) resta alla squadra, ma senza il tuo nome."
    )) return;

    const scritto = window.prompt(
      `Per confermare, scrivi il tuo nome esattamente cosi': ${io.nome}`);
    if (scritto !== io.nome) {
      if (scritto !== null) setErrore("Il nome non corrisponde: non ho cancellato niente.");
      return;
    }

    setErrore(null);
    try {
      await api.cancellaMioAccount();
      onLogout();          // il token non vale piu': fuori
    } catch (err) { setErrore(err.message); }
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

            {/* Il selettore delle aziende compare SOLO a chi ne ha piu' d'una:
                chi lavora in un posto solo non deve nemmeno accorgersi che
                questa cosa esiste. */}
            {aziende.length > 1 && (
              <div className="blocco-aziende">
                <span className="etichetta-tendina">Stai lavorando in</span>
                <ul className="lista-aziende">
                  {aziende.map((az) => (
                    <li key={az.id}>
                      <button className={az.attiva ? "voce attiva" : "voce"}
                              disabled={az.attiva}
                              onClick={() => vaiIn(az)}>
                        {az.nome}
                        <span className="ruolo-azienda">{az.ruolo}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
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

            <div className="zona-pericolo">
              <p className="vuoto piccolo">
                Puoi anche andartene del tutto. Quello che hai scritto resta alla
                squadra, ma senza il tuo nome, e non potrai più entrare.
              </p>
              <button className="bottone-pericolo" onClick={cancellaAccount}>
                Cancella il mio account
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
