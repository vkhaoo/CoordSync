import { useState, useEffect, useRef } from "react";

// Un menu che si apre premendo un pulsante.
//
// Serve a togliere dallo schermo quello che non serve adesso: elenchi di
// progetti, di macchine e di sezioni stavano sempre aperti, e con venti voci
// la pagina diventava un elenco infinito prima ancora di arrivare al lavoro
// vero. Qui si vede solo la voce scelta; il resto sta dietro un clic.
//
// Il contenuto arriva come funzione e riceve 'chiudi': cosi' chi lo usa
// decide quali gesti chiudono il menu (scegliere una voce si', creare una
// cosa nuova a volte no, perche' magari se ne creano due di fila).
export default function Tendina({ etichetta, valore, vuoto, larghezza, children }) {
  const [aperta, setAperta] = useState(false);
  const contenitore = useRef(null);

  useEffect(() => {
    if (!aperta) return;
    function fuori(e) {
      if (contenitore.current && !contenitore.current.contains(e.target)) setAperta(false);
    }
    // Esc chiude: e' il gesto che si fa d'istinto, e senza resta solo il clic
    // fuori, che su un menu grande non e' sempre ovvio dove sia.
    function tasto(e) { if (e.key === "Escape") setAperta(false); }
    document.addEventListener("mousedown", fuori);
    document.addEventListener("keydown", tasto);
    return () => {
      document.removeEventListener("mousedown", fuori);
      document.removeEventListener("keydown", tasto);
    };
  }, [aperta]);

  return (
    <div className="tendina-scelta" ref={contenitore}>
      {etichetta && <span className="etichetta-tendina">{etichetta}</span>}
      <button type="button" className={aperta ? "bottone-tendina aperto" : "bottone-tendina"}
              onClick={() => setAperta((a) => !a)}
              aria-expanded={aperta}>
        <span className={valore ? "valore-tendina" : "valore-tendina assente"}>
          {valore || vuoto}
        </span>
        <span className="freccia-tendina" aria-hidden="true">▾</span>
      </button>

      {aperta && (
        <div className="pannello-tendina" style={larghezza ? { minWidth: larghezza } : undefined}>
          {children(() => setAperta(false))}
        </div>
      )}
    </div>
  );
}
