import { useState } from "react";
import { api } from "./api.js";
import { quandoRelativo } from "./date.js";

/**
 * La conversazione attaccata a qualcosa: un lavoro di progetto o una voce del
 * taccuino di una macchina.
 *
 * Un componente solo per tutti e due perche' la lista, il modo di correggere e
 * quello di togliere sono identici: cambia solo DOVE si scrive, e quello lo sa
 * il genitore (passa `onInvia`). Correggere e togliere invece passano da un
 * indirizzo unico /commenti/{id}, quindi li fa direttamente questo componente.
 *
 * I permessi rispecchiano quelli del server, ma NON li sostituiscono: qui si
 * nascondono i comandi che non servono, li' si rifiutano le richieste.
 * - correggere: solo chi ha scritto;
 * - togliere: chi ha scritto, oppure admin e caposquadra.
 */
// Toglie accenti e maiuscole, per cercare un nome come lo si scrive di fretta
// ("nicolo" deve trovare "Nicolò"). Stessa regola del server.
function piatto(testo) {
  return testo.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// Il pezzo di nome che si sta scrivendo adesso, se si e' dentro una chiocciola.
// Si guarda solo il testo PRIMA del cursore: scrivendo in mezzo a una frase
// gia' fatta, il suggerimento deve riguardare il nome che si sta digitando li'.
function menzioneInCorso(testo, cursore) {
  const prima = testo.slice(0, cursore);
  const trovato = prima.match(/@([\p{L}\p{M} ]{0,30})$/u);
  return trovato ? trovato[1] : null;
}

export default function Commenti({ commenti, setCommenti, io, gestisco,
                                   persone = [], puoiScrivere = true,
                                   vietato, onInvia }) {
  const [nuovo, setNuovo] = useState("");
  const [frammento, setFrammento] = useState(null);   // null = nessun @ aperto
  const [correggo, setCorreggo] = useState(null);   // id del commento in modifica
  const [bozza, setBozza] = useState("");
  const [errore, setErrore] = useState(null);

  // I nomi da suggerire: i colleghi, meno me stesso (nominarsi da soli non
  // fa niente) e meno chi non c'entra col frammento scritto finora.
  const suggeriti = frammento === null ? [] : persone
    .filter((u) => (!io || u.id !== io.id) && piatto(u.nome).includes(piatto(frammento)))
    .slice(0, 5);

  function scrivendo(e) {
    setNuovo(e.target.value);
    setFrammento(menzioneInCorso(e.target.value, e.target.selectionStart));
  }

  function scegli(persona) {
    // Sostituisco SOLO il frammento gia' scritto, non tutta la parola: il
    // resto della frase (anche quello dopo il cursore) resta dov'e'.
    setNuovo((prec) => {
      const taglio = prec.lastIndexOf("@" + frammento);
      if (taglio < 0) return prec;
      return prec.slice(0, taglio) + "@" + persona.nome + " "
           + prec.slice(taglio + 1 + frammento.length);
    });
    setFrammento(null);
  }

  async function invia(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const creato = await onInvia(nuovo);
      setCommenti((prec) => [...prec, creato]);
      setNuovo("");
      setFrammento(null);
    } catch (err) { setErrore(err.message); }
  }

  function apriCorrezione(c) {
    setCorreggo(c.id);
    setBozza(c.testo);
  }

  async function salvaCorrezione(e) {
    e.preventDefault();
    setErrore(null);
    try {
      const corretto = await api.correggiCommento(correggo, bozza);
      setCommenti((prec) => prec.map((c) => (c.id === corretto.id ? corretto : c)));
      setCorreggo(null);
    } catch (err) { setErrore(err.message); }
  }

  async function togli(c) {
    if (!window.confirm("Togliere questo commento?")) return;
    setErrore(null);
    try {
      await api.togliCommento(c.id);
      setCommenti((prec) => prec.filter((x) => x.id !== c.id));
    } catch (err) { setErrore(err.message); }
  }

  return (
    <div className="commenti">
      {errore && <p className="errore">{errore}</p>}

      {commenti.length === 0 ? (
        <p className="vuoto piccolo">Nessun commento.</p>
      ) : (
        <ul className="lista-commenti">
          {commenti.map((c) => {
            const mio = io && c.autore && c.autore.id === io.id;
            return (
              <li key={c.id} className="commento">
                {correggo === c.id ? (
                  <form className="form-commento" onSubmit={salvaCorrezione}>
                    <input value={bozza} autoFocus
                           onChange={(e) => setBozza(e.target.value)} required />
                    <button type="submit" className="mini" title="Salva">✓</button>
                    <button type="button" className="mini annulla" title="Annulla"
                            onClick={() => setCorreggo(null)}>×</button>
                  </form>
                ) : (
                  <>
                    <span className="commento-autore">{c.autore.nome}</span>
                    <span className="commento-testo">{c.testo}</span>
                    <span className="quando-avviso">
                      {quandoRelativo(c.creato_il)}
                      {/* Una correzione si dichiara: riscrivere in silenzio
                          quello che si era detto cambia la storia. */}
                      {c.modificato_il && <> · corretto</>}
                    </span>
                    <span className="azioni-commento">
                      {mio && (
                        <button className="chip-x" title="Correggi"
                                onClick={() => apriCorrezione(c)}>✎</button>
                      )}
                      {(mio || gestisco) && (
                        <button className="chip-x" title="Togli"
                                onClick={() => togli(c)}>×</button>
                      )}
                    </span>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {puoiScrivere ? (
        <div className="scrivi-commento">
          <form className="form-commento" onSubmit={invia}>
            <input placeholder="Scrivi un commento… (@ per chiamare qualcuno)"
                   value={nuovo} onChange={scrivendo}
                   onKeyUp={(e) => setFrammento(
                     menzioneInCorso(e.target.value, e.target.selectionStart))}
                   onBlur={() => setTimeout(() => setFrammento(null), 150)}
                   required />
            <button type="submit" className="mini">→</button>
          </form>

          {/* Si suggeriscono solo i colleghi: il server avvisa comunque
              soltanto chi quella cosa la vedeva gia'. */}
          {suggeriti.length > 0 && (
            <ul className="suggerimenti-menzione">
              {suggeriti.map((u) => (
                <li key={u.id}>
                  <button type="button" className="voce"
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => scegli(u)}>{u.nome}</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        vietato && <p className="vuoto piccolo">{vietato}</p>
      )}
    </div>
  );
}
