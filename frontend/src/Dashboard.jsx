import { useState, useEffect } from "react";
import { api } from "./api.js";
import Lavoro from "./Lavoro.jsx";
import GestioneUtenti from "./GestioneUtenti.jsx";
import GestioneReparti from "./GestioneReparti.jsx";
import Macchine from "./Macchine.jsx";
import Agenda from "./Agenda.jsx";
import SelettoreReparti from "./SelettoreReparti.jsx";
import Allegati from "./Allegati.jsx";
import CampoRicerca from "./CampoRicerca.jsx";
import Tendina from "./Tendina.jsx";
import RicercaGlobale from "./RicercaGlobale.jsx";
import Campanella from "./Campanella.jsx";
import MioProfilo from "./MioProfilo.jsx";
import CambiaPassword from "./CambiaPassword.jsx";

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
  const [reparti, setReparti] = useState([]); // reparti dell'azienda (per la visibilità)
  const [io, setIo] = useState(null);         // l'utente loggato (per sapere il mio ruolo)
  const [vista, setVista] = useState("lavori");  // "lavori" oppure "utenti"
  const [avvisoVerifica, setAvvisoVerifica] = useState(null);  // feedback "reinvia"
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  // Campi dei form di creazione
  const [nuovoProgetto, setNuovoProgetto] = useState("");
  // Il modulo del nuovo lavoro parte chiuso: quasi sempre si apre l'app per
  // guardare come va, non per aggiungere qualcosa.
  const [creaLavoroAperto, setCreaLavoroAperto] = useState(false);
  // Quale macchina aprire quando si arriva dalla ricerca: la vista Macchine
  // ha una sua selezione interna, e questo e' il modo di dirle dove andare.
  const [macchinaDaAprire, setMacchinaDaAprire] = useState(null);
  const [nuovoTitolo, setNuovoTitolo] = useState("");
  const [nuovaPriorita, setNuovaPriorita] = useState("normale");
  const [nuovaScadenza, setNuovaScadenza] = useState("");   // "" = senza scadenza
  const [modificaLink, setModificaLink] = useState(false);   // sto modificando il link?
  const [linkBozza, setLinkBozza] = useState("");
  const [modificaNome, setModificaNome] = useState(false);   // sto rinominando il progetto?
  const [nomeBozza, setNomeBozza] = useState("");
  // Ricerca: nei lavori la fa il server, sui nomi dei progetti basta il browser.
  const [cercaLavori, setCercaLavori] = useState("");
  const [filtroProgetti, setFiltroProgetti] = useState("");

  // Funzioni di caricamento (fuori dagli useEffect, cosi' le richiamo dopo le creazioni).
  async function caricaProgetti(selezionaId) {
    const dati = await api.progetti();
    setProgetti(dati);
    // seleziono il progetto indicato, o il primo se non ne ho uno.
    if (selezionaId != null) setSelezionato(selezionaId);
    else if (selezionato == null && dati.length > 0) setSelezionato(dati[0].id);
  }

  async function caricaLavori(progettoId, cerca = cercaLavori) {
    if (progettoId == null) { setLavori([]); return; }
    setLavori(await api.lavori(progettoId, cerca));
  }

  // All'apertura: verifico chi sono. Se il token e' scaduto/invalido (401),
  // torno al login automaticamente.
  //
  // Distinguere il 401 dagli altri guasti e' importante: prima bastava che il
  // server non rispondesse (addormentato, rete assente) per essere buttati
  // fuori e dover riscrivere la password, anche se il token era valido.
  function avvia() {
    setCaricando(true);
    setErrore(null);
    api.me()
      .then((utente) => {
        setIo(utente);
        return caricaProgetti().catch((e) => setErrore(e.message));
      })
      .catch((e) => {
        if (e.stato === 401) onLogout();     // il token non vale piu'
        else setErrore(e.message);           // il server non risponde: resto qui
      })
      .finally(() => setCaricando(false));
  }

  useEffect(avvia, []);

  // Ogni volta che cambia il progetto selezionato: ricarico i suoi lavori.
  useEffect(() => {
    caricaLavori(selezionato).catch((e) => setErrore(e.message));
  }, [selezionato, cercaLavori]);

  // Colleghi e reparti si ricaricano ogni volta che torno alla vista lavori:
  // se ho appena creato un reparto o aggiunto un utente dai pannelli admin,
  // devo ritrovarmeli qui senza dover ricaricare la pagina.
  useEffect(() => {
    if (vista !== "lavori" && vista !== "macchine" && vista !== "agenda") return;
    api.utenti().then(setUtenti).catch((e) => setErrore(e.message));
    api.reparti().then(setReparti).catch((e) => setErrore(e.message));
  }, [vista]);

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

  // Cliccando un avviso si va sul lavoro citato: cerco in che progetto sta
  // e ci porto l'utente, azzerando la ricerca per non nasconderglielo.
  async function vaiAlLavoro(lavoroId) {
    setErrore(null);
    try {
      const tutti = await api.tuttiILavori();
      const trovato = tutti.find((l) => l.id === lavoroId);
      if (!trovato) return;                       // cancellato nel frattempo
      setVista("lavori");
      setCercaLavori("");
      setSelezionato(trovato.progetto_id);
    } catch (err) { setErrore(err.message); }
  }

  async function cambiaReparti(progettoId, ids) {
    setErrore(null);
    try {
      // Lista vuota = nessun reparto: progetto visibile a tutta l'azienda.
      await api.aggiornaProgetto(progettoId, { reparti_ids: ids });
      // Ricarico: togliendomi un reparto il progetto potrebbe non essere più mio da vedere.
      await caricaProgetti();
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
        data_scadenza: nuovaScadenza || null,
      });
      setNuovoTitolo("");
      setNuovaPriorita("normale");
      setNuovaScadenza("");
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

  async function salvaNome(progettoId) {
    setErrore(null);
    try {
      await api.aggiornaProgetto(progettoId, { nome: nomeBozza });
      setModificaNome(false);
      await caricaProgetti(progettoId);
    } catch (err) { setErrore(err.message); }
  }

  async function eliminaProgetto(progetto) {
    if (!window.confirm(`Eliminare il progetto "${progetto.nome}" e tutti i suoi lavori? L'azione è irreversibile.`)) return;
    setErrore(null);
    try {
      await api.eliminaProgetto(progetto.id);
      setSelezionato(null);        // nessun progetto selezionato dopo l'eliminazione
      await caricaProgetti();
    } catch (err) { setErrore(err.message); }
  }

  if (caricando) return <div className="schermata"><p>Caricamento…</p></div>;

  // Il server non ha risposto all'avvio. Non e' un motivo per buttare fuori
  // l'utente: la sessione e' ancora buona, manca solo la risposta. Gli do un
  // bottone per riprovare invece di lasciarlo davanti a una pagina vuota.
  if (!io) {
    return (
      <div className="schermata">
        <div className="card">
          <div className="marchio">CoordSync</div>
          <p className="errore">{errore || "Non riesco a contattare il server."}</p>
          <p className="vuoto piccolo">
            Se il servizio e' rimasto fermo a lungo si sta riaccendendo: puo'
            metterci qualche decina di secondi.
          </p>
          <button className="principale" onClick={avvia}>Riprova</button>
          <button type="button" className="link-testo" onClick={onLogout}>Esci</button>
        </div>
      </div>
    );
  }

  // Utente creato dall'admin al primo accesso: prima sceglie una password sua,
  // poi entra. Blocco qui (non nel login) cosi' vale anche per i token gia' salvati.
  if (io && io.deve_cambiare_password) {
    return <CambiaPassword onLogout={onLogout}
             onFatto={() => setIo({ ...io, deve_cambiare_password: false })} />;
  }

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
            <button className={vista === "agenda" ? "nav-attiva" : ""}
                    onClick={() => setVista("agenda")}>Agenda</button>
            <button className={vista === "macchine" ? "nav-attiva" : ""}
                    onClick={() => setVista("macchine")}>Macchine</button>
            {sonoAdmin && (
              <>
                <button className={vista === "utenti" ? "nav-attiva" : ""}
                        onClick={() => setVista("utenti")}>Utenti</button>
                <button className={vista === "reparti" ? "nav-attiva" : ""}
                        onClick={() => setVista("reparti")}>Reparti</button>
              </>
            )}
          </nav>
        </div>
        <div className="barra-destra">
          <RicercaGlobale
            onVaiAlLavoro={vaiAlLavoro}
            onVaiAlProgetto={(id) => { setVista("lavori"); setSelezionato(id); }}
            onVaiAllaMacchina={(id) => { setVista("macchine"); setMacchinaDaAprire(id); }}
            onVaiAllAgenda={() => setVista("agenda")} />
          <Campanella onVaiAlLavoro={vaiAlLavoro} />
          <MioProfilo io={io} onLogout={onLogout} />
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
      ) : vista === "reparti" && sonoAdmin ? (
        <div className="corpo-singolo">
          <GestioneReparti />
        </div>
      ) : vista === "macchine" ? (
        <Macchine io={io} reparti={reparti} vaiA={macchinaDaAprire} />
      ) : vista === "agenda" ? (
        <Agenda io={io} utenti={utenti} />
      ) : (
      <div className="corpo">
        <main className="area-lavori">
          {/* La scelta del progetto: un menu, non piu' una colonna sempre
              aperta. Il modulo per crearne uno sta dentro lo stesso menu:
              scegliere un progetto e farne uno nuovo sono lo stesso gesto,
              e cosi' non occupa spazio quando si sta solo guardando. */}
          <div className="barra-scelte">
            <Tendina etichetta="Progetto"
                     valore={progettoCorrente ? progettoCorrente.nome : null}
                     vuoto={progetti.length ? "Scegli un progetto" : "Nessun progetto"}>
              {(chiudi) => (
                <>
                  {progetti.length > 6 && (
                    <CampoRicerca valore={filtroProgetti} onCambia={setFiltroProgetti}
                                  segnaposto="Filtra progetti…" attesa={0} />
                  )}
                  {progetti.length === 0 && (
                    <p className="vuoto piccolo">Nessun progetto ancora.</p>
                  )}
                  <ul className="lista-progetti">
                    {progetti
                      .filter((p) => p.nome.toLowerCase().includes(filtroProgetti.toLowerCase()))
                      .map((p) => (
                        <li key={p.id}>
                          <button
                            className={p.id === selezionato ? "voce attiva" : "voce"}
                            onClick={() => { setSelezionato(p.id); chiudi(); }}
                          >{p.nome}</button>
                        </li>
                      ))}
                  </ul>

                  {puoCreare && (
                    <div className="separatore-tendina">
                      <form className="form-inline" onSubmit={async (e) => {
                        await aggiungiProgetto(e);
                        chiudi();   // il nuovo progetto e' gia' selezionato
                      }}>
                        <input placeholder="Crea progetto…" value={nuovoProgetto}
                               onChange={(e) => setNuovoProgetto(e.target.value)} required />
                        <button type="submit" className="mini">+</button>
                      </form>
                    </div>
                  )}
                </>
              )}
            </Tendina>
          </div>

          {progettoCorrente ? (
            <>
              <div className="intestazione-progetto">
                {modificaNome ? (
                  <div className="form-inline" style={{ marginTop: 0, marginBottom: "0.7rem", maxWidth: 420 }}>
                    <input value={nomeBozza} onChange={(e) => setNomeBozza(e.target.value)} />
                    <button className="mini" onClick={() => salvaNome(progettoCorrente.id)}>✓</button>
                    <button className="mini annulla" onClick={() => setModificaNome(false)}>×</button>
                  </div>
                ) : (
                  <div className="testa-progetto">
                    <h2 className="titolo-progetto">{progettoCorrente.nome}</h2>
                    {puoCreare && (
                      <div className="lavoro-azioni">
                        <button className="azione-icona" title="Rinomina progetto"
                                onClick={() => { setNomeBozza(progettoCorrente.nome); setModificaNome(true); }}>✎</button>
                        <button className="azione-icona elimina" title="Elimina progetto"
                                onClick={() => eliminaProgetto(progettoCorrente)}>🗑</button>
                      </div>
                    )}
                  </div>
                )}

                {/* Reparti: decidono chi vede questo progetto (anche piu' d'uno) */}
                <SelettoreReparti reparti={reparti}
                                  selezionati={progettoCorrente.reparti}
                                  modificabile={puoCreare}
                                  onCambia={(ids) => cambiaReparti(progettoCorrente.id, ids)} />

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

                {/* Altri link del progetto, oltre al documento principale */}
                <Allegati allegati={progettoCorrente.allegati || []}
                          onAggiungi={async (dati) => {
                            await api.allegaProgetto(progettoCorrente.id, dati);
                            await caricaProgetti(progettoCorrente.id);
                          }}
                          onElimina={async (id) => {
                            await api.eliminaAllegato(id);
                            await caricaProgetti(progettoCorrente.id);
                          }} />
              </div>

              {/* Nuovo lavoro: dietro un pulsante, non piu' sempre aperto */}
              {puoCreare && !creaLavoroAperto && (
                <button className="principale piccolo bottone-crea"
                        onClick={() => setCreaLavoroAperto(true)}>+ Nuovo lavoro</button>
              )}
              {puoCreare && creaLavoroAperto && (
                <form className="form-lavoro" onSubmit={async (e) => {
                  await aggiungiLavoro(e);
                  setCreaLavoroAperto(false);
                }}>
                  <input
                    placeholder="Titolo del lavoro…"
                    value={nuovoTitolo}
                    onChange={(e) => setNuovoTitolo(e.target.value)}
                    required
                  />
                  <select value={nuovaPriorita} onChange={(e) => setNuovaPriorita(e.target.value)}>
                    {PRIORITA.map((p) => <option key={p} value={p}>{ETICHETTA_PRIORITA[p]}</option>)}
                  </select>
                  <input type="date" title="Scadenza (facoltativa)" value={nuovaScadenza}
                         onChange={(e) => setNuovaScadenza(e.target.value)} />
                  <button type="submit" className="principale piccolo">Aggiungi</button>
                  <button type="button" className="mini annulla" title="Chiudi"
                          onClick={() => setCreaLavoroAperto(false)}>×</button>
                </form>
              )}

              {/* Ricerca nei lavori: la fa il server, cosi' regge anche
                  quando un progetto ne accumula centinaia. */}
              <CampoRicerca valore={cercaLavori} onCambia={setCercaLavori}
                            segnaposto="Cerca fra i lavori (titolo o descrizione)…" />

              {lavori.length === 0 ? (
                <p className="vuoto">{cercaLavori
                  ? `Nessun lavoro trovato per "${cercaLavori}".`
                  : "Nessun lavoro in questo progetto."}</p>
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
