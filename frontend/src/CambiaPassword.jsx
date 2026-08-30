import { useState } from "react";
import { api } from "./api.js";

// Schermata BLOCCANTE al primo accesso di un utente creato dall'admin:
// finche' non sceglie una password sua, non entra nella dashboard.
export default function CambiaPassword({ onFatto, onLogout }) {
  const [vecchia, setVecchia] = useState("");
  const [nuova, setNuova] = useState("");
  const [errore, setErrore] = useState(null);

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    try {
      await api.cambiaPassword(vecchia, nuova);
      onFatto();
    } catch (err) { setErrore(err.message); }
  }

  return (
    <div className="schermata">
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">
          Per sicurezza, scegli una password che conosci solo tu prima di continuare.
        </p>
        <label>Password attuale
          <input type="password" value={vecchia}
                 onChange={(e) => setVecchia(e.target.value)} required />
        </label>
        <label>Nuova password
          <input type="password" value={nuova}
                 onChange={(e) => setNuova(e.target.value)} required />
        </label>
        {errore && <p className="errore">{errore}</p>}
        <button type="submit" className="principale">Cambia password ed entra</button>
        <button type="button" className="link-testo" onClick={onLogout}>Esci</button>
      </form>
    </div>
  );
}
