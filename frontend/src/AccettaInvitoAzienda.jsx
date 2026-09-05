import { useState, useEffect } from "react";
import { api } from "./api.js";

// Pagina che si apre dal link "ti hanno invitato in X" (?invito_azienda_token=).
//
// E' rivolta a chi CoordSync ce l'ha gia': non c'e' nessuna password da
// scegliere, l'account e' lo stesso. Quello che si chiede qui e' il consenso,
// e per questo il clic su questa pagina e' l'unico modo di entrare in
// un'azienda con un account esistente: un amministratore non puo' aggiungersi
// qualcuno da solo.
export default function AccettaInvitoAzienda({ token, onFatto }) {
  const [stato, setStato] = useState("chiedo");   // chiedo | fatto | errore
  const [esito, setEsito] = useState(null);
  const [errore, setErrore] = useState(null);

  // L'invito NON si accetta da solo aprendo la pagina: serve un clic. Un
  // programma che apre i link per conto tuo (l'anteprima di certe caselle di
  // posta) non deve poter accettare al posto tuo.
  async function accetta() {
    setStato("attendo");
    setErrore(null);
    try {
      setEsito(await api.accettaInvitoAzienda(token));
      setStato("fatto");
    } catch (err) {
      setErrore(err.message);
      setStato("errore");
    }
  }

  return (
    <div className="schermata">
      <div className="card">
        <div className="marchio">CoordSync</div>

        {stato === "fatto" ? (
          <>
            <p className="sottotitolo">
              Fatto: adesso fai parte anche di <strong>{esito.azienda}</strong>,
              come {esito.ruolo}.
            </p>
            <p className="vuoto piccolo">
              Il tuo account e la tua password restano gli stessi. Per passare
              da un'azienda all'altra usa il menu del tuo nome, in alto a
              destra.
            </p>
            <button className="principale" onClick={onFatto}>Entra</button>
          </>
        ) : (
          <>
            <p className="sottotitolo">
              Ti hanno invitato a lavorare anche per un'altra azienda.
            </p>
            <p className="vuoto piccolo">
              Accettando, quell'azienda si aggiunge alle tue: stesso account,
              stessa password, e un menu per passare dall'una all'altra. Se non
              te lo aspettavi, chiudi pure questa pagina: senza il tuo clic non
              cambia niente.
            </p>
            {errore && <p className="errore">{errore}</p>}
            <button className="principale" onClick={accetta}
                    disabled={stato === "attendo"}>
              {stato === "attendo" ? "Un momento…" : "Accetto l'invito"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
