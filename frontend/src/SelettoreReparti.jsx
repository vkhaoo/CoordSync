import Tendina from "./Tendina.jsx";

// Scelta dei reparti di un progetto o di una macchina.
// Piu' reparti insieme sono ammessi: una linea seguita da due reparti non
// appartiene a uno solo dei due. Nessun reparto selezionato = "generale",
// cioe' visibile a tutta l'azienda.
//
// Sta dietro una tendina perche' e' un'impostazione che si tocca una volta e
// poi si guarda soltanto: da aperta occupava una riga intera di pulsanti sopra
// ogni progetto e ogni macchina.
export default function SelettoreReparti({ reparti, selezionati, modificabile, onCambia }) {
  if (reparti.length === 0) return null;   // finche' non ci sono reparti, non serve

  const ids = (selezionati || []).map((r) => r.id);
  // La stessa frase sia da fermi sia dentro il pulsante: chi legge deve
  // trovare scritto la stessa cosa, aperta o chiusa che sia.
  const riassunto = ids.length === 0
    ? "Tutta l'azienda"
    : selezionati.map((r) => r.nome).join(" · ");

  if (!modificabile) {
    return (
      <div className="riga-reparto">
        <span className="etichetta-tendina">Visibile a</span>
        <span className="reparto-chip">{riassunto}</span>
      </div>
    );
  }

  const alterna = (id) =>
    onCambia(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  return (
    <div className="riga-reparto">
      <Tendina etichetta="Visibile a" valore={riassunto}>
        {() => (
          <>
            <p className="vuoto piccolo">
              Chi non e' in nessuno dei reparti scelti non la vedra'. Senza
              reparti la vede tutta l'azienda.
            </p>
            {/* La tendina NON si chiude scegliendo: i reparti sono piu' d'uno
                e quasi sempre se ne tocca piu' di uno di fila. */}
            <div className="scelte-reparti">
              <button className={ids.length === 0 ? "sez attiva" : "sez"}
                      onClick={() => onCambia([])}>Tutta l'azienda</button>
              {reparti.map((r) => (
                <button key={r.id} className={ids.includes(r.id) ? "sez attiva" : "sez"}
                        onClick={() => alterna(r.id)}>{r.nome}</button>
              ))}
            </div>
          </>
        )}
      </Tendina>
    </div>
  );
}
