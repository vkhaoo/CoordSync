import { useState } from "react";
import { api } from "./api.js";

// Pagina di reset: si apre dal link nell'email (?reset_token=...).
// L'utente digita la nuova password.
export default function ResetPassword({ token, onFatto }) {
  const [password, setPassword] = useState("");
  const [errore, setErrore] = useState(null);
  const [fatto, setFatto] = useState(false);

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    try {
      await api.resetPassword(token, password);
      setFatto(true);
    } catch (err) { setErrore(err.message); }
  }

  if (fatto) {
    return (
      <div className="schermata">
        <div className="card">
          <div className="marchio">CoordSync</div>
          <p className="ok">Password reimpostata.</p>
          <button className="principale" onClick={onFatto}>Vai all'accesso</button>
        </div>
      </div>
    );
  }

  return (
    <div className="schermata">
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">Scegli una nuova password</p>
        <label>Nuova password
          <input type="password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {errore && <p className="errore">{errore}</p>}
        <button type="submit" className="principale">Reimposta password</button>
      </form>
    </div>
  );
}
