import { useState, useEffect } from "react";

// Campo di ricerca riutilizzabile.
//
// Aspetta che si smetta di digitare prima di avvisare chi lo usa: senza questa
// pausa, cercare "valvola" farebbe partire sette richieste al server, una per
// lettera. Per i filtri che lavorano in locale basta passare attesa={0}.
export default function CampoRicerca({ valore, onCambia, segnaposto = "Cerca…", attesa = 300 }) {
  const [testo, setTesto] = useState(valore ?? "");

  useEffect(() => {
    if (testo === valore) return;
    const timer = setTimeout(() => onCambia(testo), attesa);
    return () => clearTimeout(timer);   // ogni tasto premuto annulla il timer precedente
  }, [testo]);

  // Se qualcuno azzera la ricerca da fuori (es. cambio progetto), mi allineo.
  useEffect(() => { setTesto(valore ?? ""); }, [valore]);

  return (
    <div className="campo-ricerca">
      <span className="lente" aria-hidden="true">⌕</span>
      <input type="search" value={testo} placeholder={segnaposto}
             onChange={(e) => setTesto(e.target.value)} />
      {testo && (
        <button className="chip-x" title="Azzera la ricerca"
                onClick={() => { setTesto(""); onCambia(""); }}>×</button>
      )}
    </div>
  );
}
