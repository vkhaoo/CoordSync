// Lettura delle date che arrivano dal server.
//
// Il backend registra i momenti "di sistema" (creato_il, completato_il) in UTC,
// ma li manda senza dirlo: "2026-09-05T07:33:00". Il browser una stringa cosi'
// la interpreta come ora LOCALE, e il risultato e' sbagliato di tutto il fuso:
// un avviso appena creato diceva "2 ore fa", e vicino a mezzanotte cambiava
// perfino il giorno mostrato.
//
// Qui aggiungo la "Z" mancante quando il fuso non c'e', cosi' la data viene
// letta per quello che e'. Le date scelte dall'utente (l'inizio di un impegno)
// arrivano invece gia' nel suo fuso e non vanno toccate: per quelle si continua
// a usare new Date() normale.
export function dalServer(iso) {
  if (!iso) return null;
  const haFuso = /[Zz]$|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(haFuso ? iso : iso + "Z");
}

// "adesso", "5 min fa", "3 ore fa", poi la data.
export function quandoRelativo(iso) {
  const d = dalServer(iso);
  if (!d) return "";
  const minuti = Math.round((Date.now() - d) / 60000);
  if (minuti < 1) return "adesso";
  if (minuti < 60) return `${minuti} min fa`;
  const ore = Math.round(minuti / 60);
  if (ore < 24) return `${ore} ${ore === 1 ? "ora" : "ore"} fa`;
  return d.toLocaleDateString("it-IT", { day: "numeric", month: "short" });
}
