import { useState, useEffect } from "react";
import { quandoIlServerSiSveglia } from "./api.js";

// Una striscia in alto che compare SOLO quando una richiesta non e' arrivata
// e si sta riprovando. Serve a spiegare l'attesa: sul piano gratuito il
// servizio si spegne dopo 15 minuti di silenzio e il risveglio richiede tempo.
// Senza questo avviso l'utente vede l'app ferma e pensa che sia rotta.
export default function AvvisoRete() {
  const [inCorso, setInCorso] = useState(false);

  useEffect(() => {
    // Mi registro una volta sola: api.js chiama questa funzione quando un
    // tentativo fallisce e quando la storia si chiude (bene o male).
    quandoIlServerSiSveglia(setInCorso);
    return () => quandoIlServerSiSveglia(null);
  }, []);

  if (!inCorso) return null;
  return (
    <div className="striscia-rete" role="status">
      Il server si sta svegliando, un momento…
    </div>
  );
}
