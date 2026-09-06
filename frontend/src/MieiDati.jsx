import { useState } from "react";
import { api } from "./api.js";

// Correggere i propri dati, dal menu del proprio nome.
//
// Le due cose funzionano in modo diverso, e la differenza va spiegata a chi
// le usa: il nome cambia subito, l'email no. L'email e' la chiave con cui si
// entra e l'unico modo di recuperare la password — se bastasse scriverla, un
// errore di battitura chiuderebbe fuori dal proprio account senza rimedio.
export default function MieiDati({ io, onAggiornato }) {
  const [modo, setModo] = useState(null);      // null | "nome" | "email"
  const [nome, setNome] = useState(io.nome);
  const [nuovaEmail, setNuovaEmail] = useState("");
  const [password, setPassword] = useState("");
  const [messaggio, setMessaggio] = useState(null);
  const [errore, setErrore] = useState(null);

  function chiudi() {
    setModo(null);
    setPassword("");
    setNuovaEmail("");
    setErrore(null);
  }

  async function salvaNome(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const aggiornato = await api.modificaProfilo(nome);
      setMessaggio("Nome aggiornato.");
      chiudi();
      onAggiornato && onAggiornato(aggiornato);
    } catch (err) { setErrore(err.message); }
  }

  async function chiediCambioEmail(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const r = await api.cambiaEmail(password, nuovaEmail);
      setMessaggio(r.messaggio);
      chiudi();
    } catch (err) { setErrore(err.message); }
  }

  return (
    <div className="blocco-miei-dati">
      <span className="etichetta-tendina">I tuoi dati</span>

      {messaggio && <p className="ok piccolo">{messaggio}</p>}
      {errore && <p className="errore">{errore}</p>}

      {modo === null && (
        <>
          <p className="riga-profilo">
            <strong>{io.nome}</strong>
            <button className="link-testo" onClick={() => { setNome(io.nome); setModo("nome"); }}>
              cambia
            </button>
            <br />
            {io.email}
            <button className="link-testo" onClick={() => setModo("email")}>
              cambia
            </button>
          </p>
        </>
      )}

      {modo === "nome" && (
        <form className="form-inline" onSubmit={salvaNome}>
          <input value={nome} autoFocus onChange={(e) => setNome(e.target.value)} required />
          <button type="submit" className="mini">✓</button>
          <button type="button" className="mini annulla" onClick={chiudi}>×</button>
        </form>
      )}

      {modo === "email" && (
        <form onSubmit={chiediCambioEmail}>
          <p className="vuoto piccolo">
            Ti mando un link al nuovo indirizzo: il cambio diventa attivo solo
            aprendolo. Fino ad allora entri con quello di adesso — cosi' un
            errore di battitura non ti chiude fuori.
          </p>
          <input type="email" placeholder="Nuovo indirizzo" value={nuovaEmail} autoFocus
                 onChange={(e) => setNuovaEmail(e.target.value)} required />
          <input type="password" placeholder="La tua password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
          <div className="form-inline">
            <button type="submit" className="principale piccolo">Mandami il link</button>
            <button type="button" className="mini annulla" onClick={chiudi}>×</button>
          </div>
        </form>
      )}
    </div>
  );
}
