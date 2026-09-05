// Scelta dei reparti di un progetto o di una macchina.
// Piu' reparti insieme sono ammessi: una linea seguita da due reparti non
// appartiene a uno solo dei due. Nessun reparto selezionato = "generale",
// cioe' visibile a tutta l'azienda.
export default function SelettoreReparti({ reparti, selezionati, modificabile, onCambia }) {
  if (reparti.length === 0) return null;   // finche' non ci sono reparti, non serve

  const ids = (selezionati || []).map((r) => r.id);

  if (!modificabile) {
    return (
      <div className="riga-reparto">
        <span className="reparto-chip">
          {ids.length === 0 ? "Tutta l'azienda" : selezionati.map((r) => r.nome).join(" · ")}
        </span>
      </div>
    );
  }

  const alterna = (id) =>
    onCambia(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  return (
    <div className="riga-reparto">
      <span className="etichetta-reparti">Visibile a</span>
      <button className={ids.length === 0 ? "sez attiva" : "sez"}
              title="Nessun reparto: la vedono tutti in azienda"
              onClick={() => onCambia([])}>Tutta l'azienda</button>
      {reparti.map((r) => (
        <button key={r.id} className={ids.includes(r.id) ? "sez attiva" : "sez"}
                onClick={() => alterna(r.id)}>{r.nome}</button>
      ))}
    </div>
  );
}
