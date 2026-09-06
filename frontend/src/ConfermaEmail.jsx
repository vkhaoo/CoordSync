import { useState } from "react";
import { api } from "./api.js";

// La pagina che si apre dal link "conferma il tuo nuovo indirizzo".
//
// Il cambio avviene QUI e solo qui: e' l'unico modo di dimostrare che a
// quella casella ci si arriva davvero. Fino a questo clic si continua a
// entrare con l'indirizzo di prima, quindi un errore di battitura non chiude
// fuori nessuno.
export default function ConfermaEmail({ token, onFatto }) {
  const [stato, setStato] = useState("chiedo");   // chiedo | attendo | fatto | errore
  const [messaggio, setMessaggio] = useState(null);

  async function conferma() {
    setStato("attendo");
    try {
      const r = await api.confermaEmail(token);
      setMessaggio(r.messaggio);
      setStato("fatto");
    } catch (err) {
      setMessaggio(err.message);
      setStato("errore");
    }
  }

  return (
    <div className="schermata">
      <div className="card">
        <div className="marchio">CoordSync</div>

        {stato === "fatto" ? (
          <>
            <p className="sottotitolo">{messaggio}</p>
            <button className="principale" onClick={onFatto}>Vai all'accesso</button>
          </>
        ) : (
          <>
            <p className="sottotitolo">
              Confermi di voler usare questo indirizzo per entrare in CoordSync?
            </p>
            {stato === "errore" && <p className="errore">{messaggio}</p>}
            <button className="principale" onClick={conferma}
                    disabled={stato === "attendo"}>
              {stato === "attendo" ? "Un momento…" : "Sì, confermo"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
