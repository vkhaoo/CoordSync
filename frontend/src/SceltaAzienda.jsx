import { useState, useEffect } from "react";
import { api, setToken } from "./api.js";

// La schermata di scelta: le tue aziende in fila, e in fondo il riquadro col +
// per aprirne una nuova.
//
// E' anche la porta d'ingresso di chi si e' appena iscritto: li' dentro c'e'
// SOLO il +, perche' aziende non ne ha ancora nessuna. Iscriversi e aprire
// un'azienda erano la stessa cosa, e non tornava — chi viene invitato da
// qualcun altro doveva comunque farsene una propria, che poi restava vuota.
//
// Chi ha una sola azienda non la vede mai: si entra dritti dentro.
export default function SceltaAzienda({ onEntrato, onAnnulla }) {
  const [aziende, setAziende] = useState(null);
  const [creando, setCreando] = useState(false);
  const [nome, setNome] = useState("");
  const [errore, setErrore] = useState(null);

  async function carica() {
    try { setAziende(await api.mieAziende()); }
    catch (err) { setErrore(err.message); setAziende([]); }
  }

  useEffect(() => { carica(); }, []);

  async function crea(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creata = await api.creaAzienda(nome);
      // Il token che torna punta gia' dentro l'azienda appena creata: senza,
      // bisognerebbe rifare l'accesso per entrarci.
      setToken(creata.access_token);
      onEntrato();
    } catch (err) { setErrore(err.message); }
  }

  async function entraIn(azienda) {
    setErrore(null);
    try {
      const r = await api.cambiaAzienda(azienda.id);
      setToken(r.access_token);
      onEntrato();
    } catch (err) { setErrore(err.message); }
  }

  async function rispondi(azienda, accetto) {
    setErrore(null);
    try {
      if (accetto) await api.accettaInvito(azienda.id);
      else await api.rifiutaInvito(azienda.id);
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  if (aziende === null) return <div className="schermata"><p>Caricamento…</p></div>;

  const mie = aziende.filter((a) => !a.invito);
  const inviti = aziende.filter((a) => a.invito);

  return (
    <div className="schermata schermata-scelta">
      <div className="testa-scelta">
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">
          {mie.length === 0 && inviti.length === 0
            ? "Non fai ancora parte di nessuna azienda. Creane una per iniziare, oppure aspetta che qualcuno ti inviti nella sua."
            : "Dove vuoi lavorare?"}
        </p>
      </div>

      {errore && <p className="errore">{errore}</p>}

      {inviti.length > 0 && (
        <div className="fascia-inviti">
          <span className="titolo-colonna">Ti hanno invitato</span>
          {inviti.map((az) => (
            <div key={az.id} className="riquadro riquadro-invito">
              <span className="nome-riquadro">{az.nome}</span>
              <span className="ruolo-riquadro">come {az.ruolo}</span>
              <span className="azioni-invito">
                <button className="principale piccolo"
                        onClick={() => rispondi(az, true)}>Accetto</button>
                <button className="link-testo"
                        onClick={() => rispondi(az, false)}>No, grazie</button>
              </span>
            </div>
          ))}
        </div>
      )}

      {/* La fila scorrevole: un riquadro per azienda, e in fondo il +. */}
      <div className="fila-aziende">
        {mie.map((az) => (
          <button key={az.id} className="riquadro riquadro-azienda"
                  onClick={() => entraIn(az)}>
            <span className="nome-riquadro">{az.nome}</span>
            <span className="ruolo-riquadro">{az.ruolo}</span>
          </button>
        ))}

        {creando ? (
          <form className="riquadro riquadro-nuovo" onSubmit={crea}>
            <input placeholder="Nome dell'azienda" value={nome} autoFocus
                   onChange={(e) => setNome(e.target.value)} required />
            <span className="azioni-invito">
              <button type="submit" className="principale piccolo">Crea</button>
              <button type="button" className="link-testo"
                      onClick={() => { setCreando(false); setNome(""); }}>Annulla</button>
            </span>
          </form>
        ) : (
          <button className="riquadro riquadro-piu" onClick={() => setCreando(true)}
                  title="Apri una nuova azienda">
            <span className="segno-piu">+</span>
            <span className="ruolo-riquadro">Nuova azienda</span>
          </button>
        )}
      </div>

      {/* Chi e' gia' dentro da qualche parte puo' tornare indietro senza
          scegliere niente. Chi non ha ancora nulla no: non c'e' un "dietro". */}
      {onAnnulla && mie.length > 0 && (
        <button className="link-testo" onClick={onAnnulla}>Torna indietro</button>
      )}
    </div>
  );
}
