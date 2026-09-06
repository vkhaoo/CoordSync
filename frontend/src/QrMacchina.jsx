import { useState, useEffect } from "react";
import QRCode from "qrcode";

/**
 * L'etichetta da stampare e attaccare sulla macchina: chi la inquadra col
 * telefono si trova davanti la scheda di QUELL'impianto.
 *
 * E' il pezzo che cambia l'uso dell'app in officina. Senza, per leggere lo
 * storico di una pressa bisogna ricordarsi come si chiama, aprire l'app,
 * cercarla in un elenco di trenta: tre passaggi che davanti a un guasto,
 * con i guanti addosso, non fa nessuno.
 *
 * IL CODICE NON E' UNA CHIAVE. Dentro c'e' solo l'indirizzo della scheda:
 * chi lo inquadra senza essere collegato vede la schermata di accesso, e chi
 * e' collegato a un'altra azienda non trova niente, perche' il controllo di
 * chi vede cosa resta dov'era. Quindi l'etichetta si puo' attaccare in giro
 * per il reparto senza che diventi un modo per entrare.
 *
 * Il QR si disegna QUI e non sul server: e' un calcolo, non un dato, e non ha
 * senso far viaggiare un'immagine per una cosa che il browser sa fare da se'.
 */
export default function QrMacchina({ macchina, onChiudi }) {
  const [svg, setSvg] = useState(null);
  const [errore, setErrore] = useState(null);

  // L'indirizzo di questa stessa app, con l'aggiunta di quale macchina
  // aprire. window.location.origin e non un indirizzo scritto a mano: cosi'
  // l'etichetta stampata in prova punta alla prova, e quella stampata dal
  // sito vero punta al sito vero.
  const indirizzo = `${window.location.origin}/?macchina=${macchina.id}`;

  useEffect(() => {
    let vivo = true;
    QRCode.toString(indirizzo, {
      type: "svg",
      // Correzione d'errore alta: un'etichetta in officina si sporca di
      // grasso e si graffia, e con "M" un angolo rovinato la rende illeggibile.
      errorCorrectionLevel: "H",
      margin: 2,
    })
      .then((disegno) => { if (vivo) setSvg(disegno); })
      .catch((e) => { if (vivo) setErrore(e.message); });
    return () => { vivo = false; };
  }, [indirizzo]);

  return (
    <div className="velo-qr" onClick={onChiudi}>
      <div className="foglio-qr" onClick={(e) => e.stopPropagation()}>
        <div className="comandi-qr">
          <button className="principale piccolo" onClick={() => window.print()}>
            Stampa
          </button>
          <button className="mini annulla" title="Chiudi" onClick={onChiudi}>×</button>
        </div>

        {/* Da qui in giu' e' quello che finisce sulla carta. */}
        <div className="etichetta-qr">
          <h2>{macchina.nome}</h2>
          {macchina.descrizione && <p className="sottotitolo">{macchina.descrizione}</p>}

          {errore ? (
            <p className="errore">Non sono riuscito a disegnare il codice: {errore}</p>
          ) : svg ? (
            <div className="disegno-qr" dangerouslySetInnerHTML={{ __html: svg }} />
          ) : (
            <p className="vuoto">Preparazione…</p>
          )}

          <p className="piede-qr">
            Inquadra il codice per aprire la scheda di questa macchina.
          </p>
        </div>
      </div>
    </div>
  );
}
