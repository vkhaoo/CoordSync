import { useState, useEffect } from "react";
import { api } from "./api.js";
import Lavoro from "./Lavoro.jsx";
import GestioneUtenti from "./GestioneUtenti.jsx";

const PRIORITA = ["bassa", "normale", "alta", "urgente"];
const ETICHETTA_PRIORITA = {
  bassa: "Bassa", normale: "Normale", alta: "Alta", urgente: "Urgente",
};

// Ordina i lavori: prima per priorità (urgente in cima), e i "Fatto" vanno in fondo.
const RANGO_PRIORITA = { urgente: 0, alta: 1, normale: 2, bassa: 3 };
function ordinaLavori(lista) {
  return [...lista].sort((a, b) => {
    const aFatto = a.stato === "fatto" ? 1 : 0;
    const bFatto = b.stato === "fatto" ? 1 : 0;
    if (aFatto !== bFatto) return aFatto - bFatto;                 // i "Fatto" dopo
    return RANGO_PRIORITA[a.priorita] - RANGO_PRIORITA[b.priorita]; // poi per priorità
  });
}

export default function Dashboard({ onLogout }) {
  const [progetti, setProgetti] = useState([]);
  const [selezionato, setSelezionato] = useState(null);
  const [lavori, setLavori] = useState([]);
  const [utenti, setUtenti] = useState([]);   // colleghi dell'azienda (per l'assegnazione)
  const [io, setIo] = useState(null);         // l'utente loggato (per sapere il mio ruolo)
  const [vista, setVista] = useState("lavori");  // "lavori" oppure "utenti"
  const [avvisoVerifica, setAvvisoVerifica] = useState(null);  // feedback "reinvia"
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  // Campi dei form di creazione
  const [nuovoProgetto, setNuovoProgetto] = useState("");
  const [nuovoTitolo, setNuovoTitolo] = useState("");
  const [nuovaPriorita, setNuovaPriorita] = useState("normale");
  const [modificaLink, setModificaLink] = useState(false);   // sto modificando il link?
  const [linkBozza, setLinkBozza] = useState("");

  // Funzioni di caricamento (fuori dagli useEffect, cosi' le richiamo dopo le creazioni).
  async function caricaProgetti(selezionaId) {
    const dati = await api.progetti();
    setProgetti(dati);
    // seleziono il progetto indicato, o il primo se non ne ho uno.
    if (selezionaId != null) setSelezionato(selezionaId);
    else if (selezionato == null && dati.length > 0) setSelezionato(dati[0].id);
  }

  async function caricaLavori(progettoId) {
    if (progettoId == null) { setLavori([]); return; }
    setLavori(await api.lavori(progettoId));
  }

  // All'apertura: verifico chi sono. Se il token e' scaduto/invalido (401),
  // torno al login automaticamente. Altrimenti carico i dati.
  useEffect(() => {
    api.me()
      .then((utente) => {
        setIo(utente);
        return Promise.all([
          caricaProgetti().catch((e) => setErrore(e.message)),
          api.utenti().then(setUtenti).catch((e) => setErrore(e.message)),
        ]);
      })
      .catch(() => onLogout())   // token non valido -> disconnetto
      .finally(() => setCaricando(false));
  }, []);

  // Ogni volta che cambia il progetto selezionato: ricarico i suoi lavori.
  useEffect(() => {
    caricaLavori(selezionato).catch((e) => setErrore(e.message));
  }, [selezionato]);

  // --- Creazioni ---

  async function aggiungiProgetto(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creato = await api.creaProgetto({ nome: nuovoProgetto });
      setNuovoProgetto("");
      await caricaProgetti(creato.id);   // ricarico e seleziono il nuovo
    } catch (err) { setErrore(err.message); }
  }

  async function aggiungiLavoro(e) {
    e.preventDefault();
    setErrore(null);
    try {
      await api.creaLavoro({
        titolo: nuovoTitolo,
        priorita: nuovaPriorita,
        progetto_id: selezionato,
      });
      setNuovoTitolo("");
      setNuovaPriorita("normale");
      await caricaLavori(selezionato);   // ricarico i lavori: il nuovo compare
    } catch (err) { setErrore(err.message); }
  }

  async function cambiaStato(lavoroId, nuovoStato) {
    setErrore(null);
    try {
      const aggiornato = await api.cambiaStato(lavoroId, nuovoStato);
      // Il backend mi restituisce il lavoro aggiornato: lo sostituisco nella lista
      // SENZA ricaricare tutto. Creo una nuova lista con quell'elemento cambiato.
      setLavori((precedenti) =>
        precedenti.map((l) => (l.id === aggiornato.id ? aggiornato : l))
      );
    } catch (err) { setErrore(err.message); }
  }

  async function reinviaVerifica() {
    setAvvisoVerifica(null);
    try {
      await api.reinviaVerifica();
      setAvvisoVerifica("Link di verifica inviato. Controlla la tua email.");
    } catch (err) { setAvvisoVerifica("Errore nell'invio: " + err.message); }
  }

  async function salvaLink(progettoId) {
    setErrore(null);
    try {
      await api.aggiornaProgetto(progettoId, { link_documento: linkBozza || null });
      setModificaLink(false);
      await caricaProgetti(progettoId);   // ricarico per vedere il link aggiornato
    } catch (err) { setErrore(err.message); }
  }

  if (caricando) return <div className="schermata"><p>Caricamento…</p></div>;

  const progettoCorrente = progetti.find((p) => p.id === selezionato);
  // Chi può creare progetti/lavori e assegnare: admin e caposquadra.
  const puoCreare = io && (io.ruolo === "admin" || io.ruolo === "caposquadra");
  const sonoAdmin = io && io.ruolo === "admin";

  return (
    <div className="app">
      <header className="barra">
        <div className="barra-sinistra">
          <span className="marchio">CoordSync</span>
          <nav className="nav-viste">
            <button className={vista === "lavori" ? "nav-attiva" : ""}
                    onClick={() => setVista("lavori")}>Lavori</button>
            {sonoAdmin && (
              <button className={vista === "utenti" ? "nav-attiva" : ""}
                      onClick={() => setVista("utenti")}>Utenti</button>
            )}
          </nav>
        </div>
        <div className="barra-destra">
          {io && <span className="mio-ruolo">{io.nome} · {io.ruolo}</span>}
          <button className="esci" onClick={onLogout}>Esci</button>
        </div>
      </header>

      {errore && <p className="errore" style={{ padding: "0 1rem" }}>{errore}</p>}

      {/* Banner: email non ancora verificata */}
      {io && !io.email_verificata && (
        <div className="banner-verifica">
          <span>
            La tua email non è ancora verificata.
            {avvisoVerifica && <strong> {avvisoVerifica}</strong>}
          </span>
          {!avvisoVerifica && (
            <button className="banner-azione" onClick={reinviaVerifica}>Reinvia link</button>
          )}
        </div>
      )}

      {vista === "utenti" && sonoAdmin ? (
        <div className="corpo-singolo">
          <GestioneUtenti io={io} />
        </div>
      ) : (
      <div className="corpo">
        <aside className="colonna-progetti">
          <h2 className="titolo-colonna">Progetti</h2>
          {progetti.length === 0 && <p className="vuoto">Nessun progetto ancora.</p>}
          <ul className="lista-progetti">
            {progetti.map((p) => (
              <li key={p.id}>
                <button
                  className={p.id === selezionato ? "voce attiva" : "voce"}
                  onClick={() => setSelezionato(p.id)}
                >{p.nome}</button>
              </li>
            ))}
          </ul>

          {/* Form: nuovo progetto — solo per chi può creare */}
          {puoCreare && (
            <form className="form-inline" onSubmit={aggiungiProgetto}>
              <input
                placeholder="Nuovo progetto…"
                value={nuovoProgetto}
                onChange={(e) => setNuovoProgetto(e.target.value)}
                required
              />
              <button type="submit" className="mini">+</button>
            </form>
          )}
        </aside>

        <main className="area-lavori">
          {progettoCorrente ? (
            <>
              <div className="intestazione-progetto">
                <h2 className="titolo-progetto">{progettoCorrente.nome}</h2>

                {/* Avanzamento: quanti lavori "fatti" su totale */}
                {lavori.length > 0 && (() => {
                  const fatti = lavori.filter((l) => l.stato === "fatto").length;
                  const perc = Math.round((fatti / lavori.length) * 100);
                  return (
                    <div className="avanzamento">
                      <div className="avanzamento-testo">{fatti}/{lavori.length} completati ({perc}%)</div>
                      <div className="barra"><div className="barra-piena" style={{ width: `${perc}%` }} /></div>
                    </div>
                  );
                })()}

                {/* Link al documento esterno (Excel/foglio) */}
                <div className="link-documento">
                  {modificaLink ? (
                    <div className="form-inline">
                      <input
                        placeholder="https://… (link a Excel/foglio)"
                        value={linkBozza}
                        onChange={(e) => setLinkBozza(e.target.value)}
                      />
                      <button className="mini" onClick={() => salvaLink(progettoCorrente.id)}>✓</button>
                      <button className="mini annulla" onClick={() => setModificaLink(false)}>×</button>
                    </div>
                  ) : (
                    <>
                      {progettoCorrente.link_documento ? (
                        <a href={progettoCorrente.link_documento} target="_blank" rel="noreferrer" className="doc-link">
                          📄 Documento collegato
                        </a>
                      ) : (
                        <span className="vuoto piccolo">Nessun documento collegato</span>
                      )}
                      {puoCreare && (
                        <button className="link-testo"
                                onClick={() => { setLinkBozza(progettoCorrente.link_documento || ""); setModificaLink(true); }}>
                          {progettoCorrente.link_documento ? "Modifica" : "Aggiungi link"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Form: nuovo lavoro — solo per chi può creare */}
              {puoCreare && (
                <form className="form-lavoro" onSubmit={aggiungiLavoro}>
                  <input
                    placeholder="Titolo del lavoro…"
                    value={nuovoTitolo}
                    onChange={(e) => setNuovoTitolo(e.target.value)}
                    required
                  />
                  <select value={nuovaPriorita} onChange={(e) => setNuovaPriorita(e.target.value)}>
                    {PRIORITA.map((p) => <option key={p} value={p}>{ETICHETTA_PRIORITA[p]}</option>)}
                  </select>
                  <button type="submit" className="principale piccolo">Aggiungi</button>
                </form>
              )}

              {lavori.length === 0 ? (
                <p className="vuoto">Nessun lavoro in questo progetto.</p>
              ) : (
                <ul className="lista-lavori">
                  {ordinaLavori(lavori).map((l) => (
                    <Lavoro
                      key={l.id}
                      lavoro={l}
                      utenti={utenti}
                      io={io}
                      onCambiaStato={cambiaStato}
                      onAssegnazioneCambiata={() => caricaLavori(selezionato)}
                    />
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="vuoto">Crea o seleziona un progetto per iniziare.</p>
          )}
        </main>
      </div>
      )}
    </div>
  );
}
