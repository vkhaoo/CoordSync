// Un link scritto da un utente, reso innocuo prima di finire in un href.
//
// React protegge il TESTO ma non l'attributo href: "javascript:qualcosa"
// dentro un href e' codice che parte quando qualcuno ci clicca. Il controllo
// vero sta sul server (nessun link del genere si salva piu'), questo serve a
// due cose: ai link gia' salvati prima della correzione, e come seconda rete
// se un domani si aggiunge un endpoint dimenticandosi il validatore.
const PERMESSI = ["http://", "https://"];

export function linkSicuro(url) {
  if (!url) return null;
  const pulito = String(url).trim();
  const sicuro = PERMESSI.some((s) => pulito.toLowerCase().startsWith(s));
  return sicuro ? pulito : null;
}
