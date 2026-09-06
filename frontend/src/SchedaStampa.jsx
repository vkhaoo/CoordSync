import { useState, useEffect } from "react";
import { api } from "./api.js";
import { dalServer } from "./date.js";

const TIPI = {
  lavoro: "Lavoro",
  modifica: "Modifica",
  analisi: "Analisi",
  informazione: "Informazione utile",
};
const STATI = { da_fare: "Da fare", in_corso: "In corso", fatto: "Fatto" };

/**
 * La scheda della macchina in forma di DOCUMENTO, da stampare o salvare in PDF.
 *
 * PERCHE' NON BASTA "stampa la pagina". Quello che si vede a schermo e' fatto
 * per essere esplorato: menu, filtri, blocchi che si aprono e si chiudono.
 * Sulla carta serve il contrario — tutto aperto, tutto in fila, niente
 * comandi. Le checklist chiuse, per dire, a schermo non stanno proprio nella
 * pagina: nessuna regola di stampa potrebbe farle comparire.
 *
 * COSA CI FINISCE: quello che si sta guardando, filtri compresi. Se si e'
 * cercato "valvola", si stampa la storia della valvola; se si e' aperta una
 * sezione, si stampa quella. E' la cosa meno sorprendente: si stampa quello
 * che si ha davanti.
 *
 * I COMMENTI SI VANNO A PRENDERE. Non arrivano con lo storico — a schermo si
 * leggono aprendo una voce alla volta — ma su un documento che racconta la
 * vita di un impianto la discussione intorno a un guasto e' meta' del valore.
 * Si chiedono qui, tutti insieme, e solo quando si stampa davvero.
 */
export default function SchedaStampa({ scheda, voci, onChiudi }) {
  const [commentiPer, setCommentiPer] = useState({});
  const [pronto, setPronto] = useState(false);
  const [errore, setErrore] = useState(null);

  useEffect(() => {
    let vivo = true;
    Promise.all(voci.map((v) =>
      api.commentiVoce(v.id).then((c) => [v.id, c]).catch(() => [v.id, []])
    ))
      .then((coppie) => {
        if (!vivo) return;
        setCommentiPer(Object.fromEntries(coppie));
        setPronto(true);
      })
      .catch((e) => { if (vivo) { setErrore(e.message); setPronto(true); } });
    return () => { vivo = false; };
  }, [voci]);

  // La stampa NON parte da sola: aprirebbe la finestra di sistema prima che
  // si sia potuto guardare cosa ci finisce sopra.
  const oggi = new Date().toLocaleDateString("it-IT");

  return (
    <div className="velo-qr" onClick={onChiudi}>
      <div className="foglio-scheda" onClick={(e) => e.stopPropagation()}>
        <div className="comandi-qr">
          <button className="principale piccolo" disabled={!pronto}
                  onClick={() => window.print()}>
            {pronto ? "Stampa" : "Preparazione…"}
          </button>
          <button className="mini annulla" title="Chiudi" onClick={onChiudi}>×</button>
        </div>

        <div className="documento">
          <header className="testa-documento">
            <h1>{scheda.nome}</h1>
            {scheda.descrizione && <p className="riga-documento">{scheda.descrizione}</p>}
            {scheda.sezioni.length > 0 && (
              <p className="riga-documento">
                Sezioni: {scheda.sezioni.map((s) => s.nome).join(" · ")}
              </p>
            )}
            <p className="riga-documento tenue">
              Stampato il {oggi} · {voci.length} voci di storico
            </p>
          </header>

          {errore && <p className="errore">{errore}</p>}

          {voci.length === 0 ? (
            <p className="vuoto">Nessuna voce da stampare con questi filtri.</p>
          ) : (
            voci.map((v) => (
              <article key={v.id} className="voce-documento">
                <h2>
                  {v.titolo}
                  <span className="tenue"> — {TIPI[v.tipo]}
                    {v.tipo === "lavoro" && v.stato && <> ({STATI[v.stato]})</>}
                  </span>
                </h2>
                <p className="riga-documento tenue">
                  {dalServer(v.creato_il).toLocaleDateString("it-IT")}
                  {v.autore && <> · {v.autore.nome}</>}
                  {v.in_generale && <> · generale</>}
                  {v.sezioni.map((s) => <span key={s.id}> · {s.nome}</span>)}
                </p>

                {v.testo && <p className="riga-documento">{v.testo}</p>}

                {v.sotto_attivita && v.sotto_attivita.length > 0 && (
                  <ul className="elenco-documento">
                    {v.sotto_attivita.map((p) => (
                      <li key={p.id}>{p.completata ? "[x]" : "[ ]"} {p.testo}</li>
                    ))}
                  </ul>
                )}

                {v.allegati.length > 0 && (
                  <ul className="elenco-documento">
                    {v.allegati.map((a) => (
                      // L'indirizzo per esteso: su carta un link non si clicca,
                      // e "Schema" senza l'indirizzo non porta da nessuna parte.
                      <li key={a.id}>{a.titolo ? `${a.titolo}: ` : ""}{a.url}</li>
                    ))}
                  </ul>
                )}

                {(commentiPer[v.id] || []).length > 0 && (
                  <ul className="elenco-documento commenti-documento">
                    {commentiPer[v.id].map((c) => (
                      <li key={c.id}>
                        <strong>{c.autore.nome}</strong>: {c.testo}
                        {c.modificato_il && <span className="tenue"> (corretto)</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
