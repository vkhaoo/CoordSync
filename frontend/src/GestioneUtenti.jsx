import { useState, useEffect } from "react";
import { api } from "./api.js";

const RUOLI = ["admin", "caposquadra", "operatore"];

// Pannello di amministrazione utenti. Visibile solo all'admin.
export default function GestioneUtenti({ io }) {
  const [utenti, setUtenti] = useState([]);
  const [errore, setErrore] = useState(null);
  const [caricando, setCaricando] = useState(true);

  // Campi del form "nuovo utente"
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ruolo, setRuolo] = useState("operatore");

  // Campi del form "invita utente" (niente password: la sceglie l'invitato)
  const [nomeInvito, setNomeInvito] = useState("");
  const [emailInvito, setEmailInvito] = useState("");
  const [ruoloInvito, setRuoloInvito] = useState("operatore");
  const [messaggio, setMessaggio] = useState(null);

  async function carica() {
    try { setUtenti(await api.utenti()); }
    catch (e) { setErrore(e.message); }
    finally { setCaricando(false); }
  }

  useEffect(() => { carica(); }, []);

  async function aggiungiUtente(e) {
    e.preventDefault();
    setErrore(null); setMessaggio(null);
    try {
      await api.creaUtente({ nome, email, password, ruolo });
      setNome(""); setEmail(""); setPassword(""); setRuolo("operatore");
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  async function invitaUtente(e) {
    e.preventDefault();
    setErrore(null); setMessaggio(null);
    try {
      await api.invitaUtente({ nome: nomeInvito, email: emailInvito, ruolo: ruoloInvito });
      setMessaggio(`Invito inviato a ${emailInvito}.`);
      setNomeInvito(""); setEmailInvito(""); setRuoloInvito("operatore");
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  async function cambiaRuolo(utenteId, nuovoRuolo) {
    setErrore(null);
    try {
      await api.cambiaRuolo(utenteId, nuovoRuolo);
      await carica();
    } catch (err) { setErrore(err.message); }
  }

  if (caricando) return <p className="vuoto">Caricamento…</p>;

  return (
    <div className="gestione-utenti">
      <h2 className="titolo-progetto">Utenti dell'azienda</h2>

      {errore && <p className="errore">{errore}</p>}
      {messaggio && <p className="ok">{messaggio}</p>}

      <p className="etichetta-form">Invita via email (sceglie lui la password)</p>
      <form className="form-utente" onSubmit={invitaUtente}>
        <input placeholder="Nome" value={nomeInvito} onChange={(e) => setNomeInvito(e.target.value)} required />
        <input type="email" placeholder="Email" value={emailInvito} onChange={(e) => setEmailInvito(e.target.value)} required />
        <select value={ruoloInvito} onChange={(e) => setRuoloInvito(e.target.value)}>
          {RUOLI.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button type="submit" className="principale piccolo">Invita utente</button>
      </form>

      <p className="etichetta-form">Oppure crea direttamente con una password</p>
      <form className="form-utente" onSubmit={aggiungiUtente}>
        <input placeholder="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <select value={ruolo} onChange={(e) => setRuolo(e.target.value)}>
          {RUOLI.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button type="submit" className="principale piccolo">Aggiungi utente</button>
      </form>

      <table className="tabella-utenti">
        <thead>
          <tr><th>Nome</th><th>Email</th><th>Ruolo</th></tr>
        </thead>
        <tbody>
          {utenti.map((u) => (
            <tr key={u.id}>
              <td>{u.nome}</td>
              <td>{u.email}</td>
              <td>
                {u.id === io.id ? (
                  // Non permetto all'admin di cambiare il PROPRIO ruolo (si bloccherebbe fuori).
                  <span className="ruolo-mio">{u.ruolo} (tu)</span>
                ) : (
                  <select value={u.ruolo} onChange={(e) => cambiaRuolo(u.id, e.target.value)}>
                    {RUOLI.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
