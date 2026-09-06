import { useState, useEffect } from "react";
import { api } from "./api.js";
import Lavoro, { ETICHETTA_STATO } from "./Lavoro.jsx";
import GestioneUtenti from "./GestioneUtenti.jsx";
import GestioneReparti from "./GestioneReparti.jsx";
import Macchine from "./Macchine.jsx";
import Agenda from "./Agenda.jsx";
import SelettoreReparti from "./SelettoreReparti.jsx";
import Allegati from "./Allegati.jsx";
import CampoRicerca from "./CampoRicerca.jsx";
import Tendina from "./Tendina.jsx";
import RicercaGlobale from "./RicercaGlobale.jsx";
import SceltaAzienda from "./SceltaAzienda.jsx";
import { linkSicuro } from "./link.js";
import Campanella from "./Campanella.jsx";
import MioProfilo from "./MioProfilo.jsx";
import CambiaPassword from "./CambiaPassword.jsx";

const PRIORITA = ["bassa", "normale", "alta", "urgente"];
const ETICHETTA_PRIORITA = {
  bassa: "Bassa", normale: "Normale", alta: "Alta", urgente: "Urgente",
};

// L'ordine dei lavori lo decide il SERVER, anche quello predefinito (conclusi
// in fondo, poi per priorita'). Prima lo faceva questa funzione sulla lista
// gia' scaricata: funziona finche' i lavori arrivano tutti, ma il giorno in
// cui arriveranno a pagine riordinare quella che si ha in mano darebbe un
// ordine sbagliato.

export default function Dashboard({ onLogout, apriMacchina = null }) {
  const [progetti, setProgetti] = useState([]);
  const [selezionato, setSelezionato] = useState(null);
  const [lavori, setLavori] = useState([]);
  // Quanti ce ne sono in tutto, non solo in questa pagina: serve a sapere se
  // ha senso mostrare "mostra altri".
  const [totaleLavori, setTotaleLavori] = useState(0);
  const [utenti, setUtenti] = useState([]);   // colleghi dell'azienda (per l'assegnazione)
  const [reparti, setReparti] = useState([]); // reparti dell'azienda (per la visibilità)
  const [io, setIo] = useState(null);         // l'utente loggato (per sapere il mio ruolo)
  // Arrivando dal QR di una macchina si parte gia' dentro la sua scheda,
  // invece di far ricominciare dall'elenco dei lavori chi ha appena inquadrato
  // un impianto preciso.
  const [vista, setVista] = useState(apriMacchina ? "macchine" : "lavori");
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
  const [macchinaDaAprire, setMacchinaDaAprire] = useState(apriMacchina);
  // Vero quando si vuole vedere la schermata dei riquadri: sempre a chi non
  // ha ancora nessuna azienda, a richiesta per gli altri.
  const [scegliAzienda, setScegliAzienda] = useState(false);
  // Inviti a cui non ho ancora risposto. Chi lavora gia' da qualche parte non
  // passa dalla schermata dei riquadri, quindi senza questo avviso l'invito
  // si vedrebbe solo nell'email — e le email si perdono.
  const [invitiInSospeso, setInvitiInSospeso] = useState([]);
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
  // Filtri dell'elenco lavori. Li applica il server (vedi api.lavori): sono
  // tutti nello stesso oggetto cosi' l'effetto che ricarica li guarda insieme.
  const [filtri, setFiltri] = useState({
    stato: "", soloMiei: false, assegnatoA: "", ordina: "",
  });
  const filtriAttivi = filtri.stato || filtri.soloMiei || filtri.assegnatoA || filtri.ordina;

  function cambiaFiltro(campo, valore) {
    setFiltri((prec) => ({ ...prec, [campo]: valore }));
  }

  // Funzioni di caricamento (fuori dagli useEffect, cosi' le richiamo dopo le creazioni).
  async function caricaProgetti(selezionaId) {
    const dati = await api.progetti();
    setProgetti(dati);
    // seleziono il progetto indicato, o il primo se non ne ho uno.
    if (selezionaId != null) setSelezionato(selezionaId);
    else if (selezionato == null && dati.length > 0) setSelezionato(dati[0].id);
  }

  async function caricaLavori(progettoId, cerca = cercaLavori, quali = filtri) {
    if (progettoId == null) { setLavori([]); setTotaleLavori(0); return; }
    const { elementi, totale } = await api.lavori(progettoId, cerca, quali);
    setLavori(elementi);
    setTotaleLavori(totale);
  }

  // "Mostra altri": si CHIEDE il seguito e lo si accoda, invece di ricaricare
  // tutto da capo. Il punto da cui ripartire e' quanti ne ho gia' in mano.
  async function altriLavori() {
    setErrore(null);
    try {
      const { elementi, totale } = await api.lavori(
        selezionato, cercaLavori, filtri, lavori.length);
      setLavori((prec) => [...prec, ...elementi]);
      setTotaleLavori(totale);
    } catch (err) { setErrore(err.message); }
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

  // Gli inviti si guardano all'apertura e quando si torna alla vista lavori:
  // basta e avanza per una cosa che capita una volta ogni tanto.
  useEffect(() => {
    if (!io) return;
    api.mieAziende()
      .then((elenco) => setInvitiInSospeso(elenco.filter((a) => a.invito)))
      .catch(() => setInvitiInSospeso([]));
  }, [io, vista]);

  async function rispondiInvito(azienda, accetto) {
    setErrore(null);
    try {
      if (accetto) await api.accettaInvito(azienda.id);
      else await api.rifiutaInvito(azienda.id);
      setInvitiInSospeso((prec) => prec.filter((a) => a.id !== azienda.id));
    } catch (err) { setErrore(err.message); }
  }

  // Ogni volta che cambia il progetto selezionato: ricarico i suoi lavori.
  useEffect(() => {
    caricaLavori(selezionato).catch((e) => setErrore(e.message));
  }, [selezionato, cercaLavori, filtri]);

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

  async function duplicaProgetto(progetto) {
    // Il nome lo si chiede sempre: "Copia di Linea 3" fra sei mesi non
    // distingue niente da niente, e un progetto vero ha un nome che dice la
    // commessa, il cliente o l'anno.
    const nome = window.prompt(
      ["Come si chiama il progetto nuovo?",
       "",
       "Si copiano i lavori con le loro checklist e i link.",
       "Non si copiano stati, scadenze, commenti e assegnazioni."].join("\n"),
      progetto.nome);
    if (!nome || !nome.trim()) return;

    setErrore(null);
    try {
      const copia = await api.duplicaProgetto(progetto.id, nome.trim());
      await caricaProgetti(copia.id);   // mi porto subito dentro quello nuovo
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

  // Primo accesso: l'account c'e' ma non appartiene ancora a niente. Si apre
  // la schermata di scelta, che in quel momento contiene solo il riquadro
  // col + — e gli eventuali inviti ricevuti.
  if ((io && !io.organizzazione_id) || scegliAzienda) {
    return <SceltaAzienda
             onEntrato={() => window.location.reload()}
             onAnnulla={io && io.organizzazione_id ? () => setScegliAzienda(false) : null} />;
  }

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
          <Campanella onVaiAlLavoro={vaiAlLavoro}
                      onVaiAllaMacchina={(id) => { setVista("macchine"); setMacchinaDaAprire(id); }} />
          <MioProfilo io={io} onLogout={onLogout}
                      onCambiaAzienda={() => setScegliAzienda(true)}
                      onDatiCambiati={(aggiornato) => setIo(aggiornato)} />
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

      {/* Inviti ricevuti: si accettano o si rifiutano da qui, senza andare a
          cercare l'email. Uno per riga, perche' ognuno e' una decisione. */}
      {invitiInSospeso.map((az) => (
        <div key={az.id} className="banner-verifica banner-invito">
          <span>
            <strong>{az.nome}</strong> ti ha invitato a lavorare con loro,
            come {az.ruolo}.
          </span>
          <span className="azioni-invito">
            <button className="banner-azione"
                    onClick={() => rispondiInvito(az, true)}>Accetto</button>
            <button className="banner-azione secondaria"
                    onClick={() => rispondiInvito(az, false)}>No, grazie</button>
          </span>
        </div>
      ))}

      {vista === "utenti" && sonoAdmin ? (
        <div className="corpo-singolo">
          <GestioneUtenti io={io} />
        </div>
      ) : vista === "reparti" && sonoAdmin ? (
        <div className="corpo-singolo">
          <GestioneReparti />
        </div>
      ) : vista === "macchine" ? (
        <Macchine io={io} reparti={reparti} utenti={utenti} vaiA={macchinaDaAprire} />
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
                        <button className="azione-icona" title="Duplica come modello"
                                onClick={() => duplicaProgetto(progettoCorrente)}>⧉</button>
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
                  // I lavori ANNULLATI escono dal conto, sopra e sotto la
                  // riga: non sono lavoro fatto, ma nemmeno lavoro che resta
                  // da fare. Lasciandoli al denominatore un progetto finito
                  // non arriverebbe mai al 100%.
                  const contati = lavori.filter((l) => l.stato !== "annullato");
                  const fatti = contati.filter((l) => l.stato === "fatto").length;
                  const perc = contati.length
                    ? Math.round((fatti / contati.length) * 100) : 0;
                  return (
                    <div className="avanzamento">
                      <div className="avanzamento-testo">
                        {fatti}/{contati.length} completati ({perc}%)
                        {lavori.length > contati.length && (
                          <> · {lavori.length - contati.length} annullati</>
                        )}
                      </div>
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
                        <a href={linkSicuro(progettoCorrente.link_documento) || undefined}
                           target="_blank" rel="noreferrer" className="doc-link">
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

              {/* Filtri e ordinamento. Si sommano fra loro e con la ricerca:
                  restringono, non allargano. */}
              <div className="barra-filtri">
                <label className="spunta">
                  <input type="checkbox" checked={filtri.soloMiei}
                         onChange={(e) => cambiaFiltro("soloMiei", e.target.checked)} />
                  Solo i miei
                </label>

                <select value={filtri.stato}
                        onChange={(e) => cambiaFiltro("stato", e.target.value)}>
                  <option value="">Tutti gli stati</option>
                  {Object.entries(ETICHETTA_STATO).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>

                {/* Con "solo i miei" acceso la scelta della persona non ha
                    piu' senso: il server la ignorerebbe, quindi la si spegne
                    invece di lasciare un comando che non fa niente. */}
                <select value={filtri.assegnatoA} disabled={filtri.soloMiei}
                        onChange={(e) => cambiaFiltro("assegnatoA", e.target.value)}>
                  <option value="">Chiunque</option>
                  {utenti.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                </select>

                <select value={filtri.ordina}
                        onChange={(e) => cambiaFiltro("ordina", e.target.value)}>
                  <option value="">Ordine consueto</option>
                  <option value="scadenza">Per scadenza</option>
                  <option value="priorita">Per priorità</option>
                  <option value="recenti">Più recenti</option>
                </select>

                {filtriAttivi && (
                  <button className="link-testo"
                          onClick={() => setFiltri({ stato: "", soloMiei: false,
                                                     assegnatoA: "", ordina: "" })}>
                    Azzera filtri
                  </button>
                )}
              </div>

              {lavori.length === 0 ? (
                <p className="vuoto">{cercaLavori || filtriAttivi
                  ? "Nessun lavoro con questi filtri."
                  : "Nessun lavoro in questo progetto."}</p>
              ) : (
                <ul className="lista-lavori">
                  {lavori.map((l) => (
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

              {lavori.length < totaleLavori && (
                <button className="principale piccolo bottone-crea" onClick={altriLavori}>
                  Mostra altri ({totaleLavori - lavori.length})
                </button>
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
