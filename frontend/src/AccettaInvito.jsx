import { useState } from "react";
import { api } from "./api.js";

// Pagina di benvenuto per gli invitati: si apre dal link email (?invito_token=...).
// L'invitato sceglie la SUA password (l'admin non la conosce mai).
export default function AccettaInvito({ token, onFatto }) {
  const [password, setPassword] = useState("");
  const [errore, setErrore] = useState(null);
  const [fatto, setFatto] = useState(false);

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    try {
      await api.accettaInvito(token, password);
      setFatto(true);
    } catch (err) { setErrore(err.message); }
  }

  if (fatto) {
    return (
      <div className="schermata">
        <div className="card">
          <div className="marchio">CoordSync</div>
          <p className="ok">Account attivato. Benvenuto!</p>
          <button className="principale" onClick={onFatto}>Vai all'accesso</button>
        </div>
      </div>
    );
  }

  return (
    <div className="schermata">
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">Sei stato invitato: scegli la tua password per attivare l'account</p>
        <label>La tua password
          <input type="password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {errore && <p className="errore">{errore}</p>}
        <button type="submit" className="principale">Attiva account</button>
      </form>
    </div>
  );
}
