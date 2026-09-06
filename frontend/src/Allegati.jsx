import { useState } from "react";
import { linkSicuro } from "./link.js";

// Lista di link appesi a una scheda. La stessa ovunque: macchina, sezione,
// voce dello storico, progetto e lavoro.
export default function Allegati({ allegati, onAggiungi, onElimina }) {
  const [apri, setApri] = useState(false);
  const [url, setUrl] = useState("");
  const [titolo, setTitolo] = useState("");

  async function invia(e) {
    e.preventDefault();
    await onAggiungi({ url, titolo: titolo || null });
    setUrl(""); setTitolo(""); setApri(false);
  }

  return (
    <div className="allegati">
      {allegati.map((a) => (
        <span key={a.id} className="chip allegato">
          {linkSicuro(a.url)
            ? <a href={linkSicuro(a.url)} target="_blank" rel="noreferrer">🔗 {a.titolo || a.url}</a>
            /* Link non apribile (salvato prima del controllo, o pericoloso):
               si mostra il testo, senza renderlo cliccabile. */
            : <span className="tenue" title="Link non valido">🔗 {a.titolo || a.url}</span>}
          <button className="chip-x" title="Togli il link"
                  onClick={() => onElimina(a.id)}>×</button>
        </span>
      ))}
      {apri ? (
        <form className="form-inline form-allegato" onSubmit={invia}>
          <input placeholder="https://…" value={url}
                 onChange={(e) => setUrl(e.target.value)} required />
          <input placeholder="Etichetta (facoltativa)" value={titolo}
                 onChange={(e) => setTitolo(e.target.value)} />
          <button type="submit" className="mini">✓</button>
          <button type="button" className="mini annulla" onClick={() => setApri(false)}>×</button>
        </form>
      ) : (
        <button className="assegna-select" onClick={() => setApri(true)}>+ link</button>
      )}
    </div>
  );
}
