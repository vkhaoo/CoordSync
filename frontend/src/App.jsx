import { useState } from "react";
import { api, setToken, getToken } from "./api.js";
import Dashboard from "./Dashboard.jsx";
import ResetPassword from "./ResetPassword.jsx";
import AccettaInvito from "./AccettaInvito.jsx";

// Leggo eventuali token dall'indirizzo (arrivo da un link email).
const parametri = new URLSearchParams(window.location.search);
const tokenReset = parametri.get("reset_token");
const tokenInvito = parametri.get("invito_token");

export default function App() {
  // "stato" = dati che, se cambiano, ridisegnano lo schermo da soli.
  const [modo, setModo] = useState("login");      // "login", "registra" o "recupero"
  // All'avvio sono gia' connesso se un token e' salvato nel browser.
  const [connesso, setConnesso] = useState(Boolean(getToken()));
  const [errore, setErrore] = useState(null);
  const [messaggio, setMessaggio] = useState(null);

  // Campi del form
  const [nomeAzienda, setNomeAzienda] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Se arrivo dal link dell'email, mostro la pagina per la nuova password.
  if (tokenReset) {
    return <ResetPassword token={tokenReset}
             onFatto={() => { window.location.href = window.location.origin; }} />;
  }

  // Se arrivo da un invito, mostro la pagina "scegli la tua password".
  if (tokenInvito) {
    return <AccettaInvito token={tokenInvito}
             onFatto={() => { window.location.href = window.location.origin; }} />;
  }

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    setMessaggio(null);
    try {
      if (modo === "recupero") {
        await api.richiediReset(email);
        setMessaggio("Se l'email è registrata, riceverai un link per reimpostare la password.");
        return;
      }
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

  // Altrimenti mostro il form di accesso/registrazione/recupero.
  return (
    <div className="schermata">
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">Coordinamento lavori per squadre tecniche</p>

        {modo !== "recupero" && (
          <div className="tabs">
            <button type="button" className={modo === "login" ? "attivo" : ""}
                    onClick={() => setModo("login")}>Accedi</button>
            <button type="button" className={modo === "registra" ? "attivo" : ""}
                    onClick={() => setModo("registra")}>Registra azienda</button>
          </div>
        )}

        {modo === "recupero" && (
          <p className="sottotitolo">Inserisci la tua email: ti mandiamo un link per reimpostare la password.</p>
        )}

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
        {modo !== "recupero" && (
          <label>Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
        )}

        {errore && <p className="errore">{errore}</p>}
        {messaggio && <p className="ok" style={{ fontSize: "0.9rem" }}>{messaggio}</p>}

        <button type="submit" className="principale">
          {modo === "registra" ? "Crea azienda e accedi"
            : modo === "recupero" ? "Invia link di recupero"
            : "Accedi"}
        </button>

        {modo === "login" && (
          <button type="button" className="link-testo" onClick={() => { setModo("recupero"); setErrore(null); }}>
            Password dimenticata?
          </button>
        )}
        {modo === "recupero" && (
          <button type="button" className="link-testo" onClick={() => { setModo("login"); setMessaggio(null); }}>
            ← Torna all'accesso
          </button>
        )}
      </form>
    </div>
  );
}
