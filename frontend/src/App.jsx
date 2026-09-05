import { useState } from "react";
import { api, setToken, getToken } from "./api.js";
import Dashboard from "./Dashboard.jsx";
import ResetPassword from "./ResetPassword.jsx";
import AccettaInvito from "./AccettaInvito.jsx";
import AvvisoRete from "./AvvisoRete.jsx";
import AccettaInvitoAzienda from "./AccettaInvitoAzienda.jsx";

// Leggo eventuali token dall'indirizzo (arrivo da un link email).
const parametri = new URLSearchParams(window.location.search);
const tokenReset = parametri.get("reset_token");
const tokenInvito = parametri.get("invito_token");
// Invito rivolto a chi ha gia' un account: aggiunge un'azienda alle sue.
const tokenInvitoAzienda = parametri.get("invito_azienda_token");

export default function App() {
  // "stato" = dati che, se cambiano, ridisegnano lo schermo da soli.
  const [modo, setModo] = useState("login");      // "login", "registra" o "recupero"
  // All'avvio sono gia' connesso se un token e' salvato nel browser.
  const [connesso, setConnesso] = useState(Boolean(getToken()));
  const [errore, setErrore] = useState(null);
  const [messaggio, setMessaggio] = useState(null);

  // Campi del form
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Secondo passo dell'accesso: chi ha acceso il 2FA riceve dal login un
  // token di passaggio che da solo non apre niente, e deve mettere il codice.
  const [attesa2fa, setAttesa2fa] = useState(null);
  const [codice2fa, setCodice2fa] = useState("");

  // Se arrivo dal link dell'email, mostro la pagina per la nuova password.
  if (tokenReset) {
    return <><AvvisoRete /><ResetPassword token={tokenReset}
             onFatto={() => { window.location.href = window.location.origin; }} /></>;
  }

  // Invito a una seconda azienda: l'account c'e' gia', serve solo il si'.
  if (tokenInvitoAzienda) {
    return <><AvvisoRete /><AccettaInvitoAzienda token={tokenInvitoAzienda}
             onFatto={() => { window.location.href = window.location.origin; }} /></>;
  }

  // Se arrivo da un invito, mostro la pagina "scegli la tua password".
  if (tokenInvito) {
    return <><AvvisoRete /><AccettaInvito token={tokenInvito}
             onFatto={() => { window.location.href = window.location.origin; }} /></>;
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
        risposta = await api.registra({ nome, email, password });
      } else {
        risposta = await api.login({ email, password });
      }
      if (risposta.token_type === "attesa_2fa") {
        // Password giusta, ma manca il codice: NON si salva questo token,
        // che non e' una credenziale valida.
        setAttesa2fa(risposta.access_token);
        setPassword("");
        return;
      }
      setToken(risposta.access_token);   // salvo il token per le chiamate successive
      setConnesso(true);
    } catch (err) {
      setErrore(err.message);            // mostro il messaggio del backend
    }
  }

  async function inviaCodice(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const risposta = await api.verificaDueFattori(attesa2fa, codice2fa);
      setToken(risposta.access_token);
      setConnesso(true);
    } catch (err) {
      setErrore(err.message);
      setCodice2fa("");
    }
  }

  // Secondo passo: il codice del telefono (o uno di recupero).
  if (attesa2fa && !connesso) {
    return (
      <>
        <AvvisoRete />
        <div className="schermata">
          <form className="card" onSubmit={inviaCodice}>
            <div className="marchio">CoordSync</div>
            <p className="sottotitolo">
              Apri l'app dei codici sul telefono e scrivi le sei cifre.
            </p>
            <input
              className="campo-codice"
              placeholder="000000"
              value={codice2fa}
              onChange={(e) => setCodice2fa(e.target.value)}
              autoFocus
              autoComplete="one-time-code"
              inputMode="numeric"
              required
            />
            {errore && <p className="errore">{errore}</p>}
            <button type="submit" className="principale">Entra</button>
            <p className="vuoto piccolo">
              Telefono perso o cambiato? Scrivi qui uno dei codici di recupero
              che avevi salvato: vale una volta sola.
            </p>
            <button type="button" className="link-testo"
                    onClick={() => { setAttesa2fa(null); setCodice2fa(""); setErrore(null); }}>
              Torna indietro
            </button>
          </form>
        </div>
      </>
    );
  }

  // Se sono connesso, mostro la dashboard vera.
  if (connesso) {
    return <><AvvisoRete />
             <Dashboard onLogout={() => { setToken(null); setConnesso(false); }} /></>;
  }

  // Altrimenti mostro il form di accesso/registrazione/recupero.
  return (
    <div className="schermata">
      <AvvisoRete />
      <form className="card" onSubmit={invia}>
        <div className="marchio">CoordSync</div>
        <p className="sottotitolo">Coordinamento lavori per squadre tecniche</p>

        {modo !== "recupero" && (
          <div className="tabs">
            <button type="button" className={modo === "login" ? "attivo" : ""}
                    onClick={() => setModo("login")}>Accedi</button>
            <button type="button" className={modo === "registra" ? "attivo" : ""}
                    onClick={() => setModo("registra")}>Crea un account</button>
          </div>
        )}

        {modo === "recupero" && (
          <p className="sottotitolo">Inserisci la tua email: ti mandiamo un link per reimpostare la password.</p>
        )}

        {modo === "registra" && (
          <>
            <p className="vuoto piccolo">
              L'azienda si crea dopo, da dentro. Se ti hanno invitato in una,
              non devi crearne nessuna: ti bastera' accettare l'invito.
            </p>
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
          {modo === "registra" ? "Crea l'account"
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
