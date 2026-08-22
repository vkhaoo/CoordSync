import { useState } from "react";
import { api, setToken } from "./api.js";
import Dashboard from "./Dashboard.jsx";

export default function App() {
  // "stato" = dati che, se cambiano, ridisegnano lo schermo da soli.
  const [modo, setModo] = useState("login");      // "login" oppure "registra"
  const [connesso, setConnesso] = useState(false);
  const [errore, setErrore] = useState(null);

  // Campi del form
  const [nomeAzienda, setNomeAzienda] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    try {
      let risposta;
      if (modo === "registra") {
        risposta = await api.registra({ nome_azienda: nomeAzienda, nome, email, password });
      } else {
        risposta = await api.login({ email, password });
      }
      setToken(risposta.access_token);   // salvo il token per le chiamate successive
      setConnesso(true);
    } catch (err) {
      setErrore(err.message);            // mostro il messaggio del backend
    }
  }

  // Se sono connesso, mostro la dashboard vera.
  if (connesso) {
    return <Dashboard onLogout={() => { setToken(null); setConnesso(false); }} />;
  }

  // Altrimenti mostro il form di accesso/registrazione.
  return (
    <div className="schermata">
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">Coordinamento lavori per squadre tecniche</p>

        <div className="tabs">
          <button type="button" className={modo === "login" ? "attivo" : ""}
                  onClick={() => setModo("login")}>Accedi</button>
          <button type="button" className={modo === "registra" ? "attivo" : ""}
                  onClick={() => setModo("registra")}>Registra azienda</button>
        </div>

        {modo === "registra" && (
          <>
            <label>Nome azienda
              <input value={nomeAzienda} onChange={(e) => setNomeAzienda(e.target.value)} required />
            </label>
            <label>Il tuo nome
              <input value={nome} onChange={(e) => setNome(e.target.value)} required />
            </label>
          </>
        )}

        <label>Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>

        {errore && <p className="errore">{errore}</p>}

        <button type="submit" className="principale">
          {modo === "registra" ? "Crea azienda e accedi" : "Accedi"}
        </button>
      </form>
    </div>
  );
}
