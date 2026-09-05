// Tema chiaro/scuro.
//
// La preferenza sta nel browser di chi usa l'app, non sul server: e' una scelta
// di questo dispositivo (magari sul telefono lo si vuole scuro e sul fisso no),
// non un dato dell'account.
const CHIAVE = "coordsync_tema";

export function temaCorrente() {
  try { return localStorage.getItem(CHIAVE) === "scuro" ? "scuro" : "chiaro"; }
  catch { return "chiaro"; }
}

export function impostaTema(tema) {
  const scuro = tema === "scuro";
  if (scuro) document.documentElement.dataset.tema = "scuro";
  else delete document.documentElement.dataset.tema;
  try { localStorage.setItem(CHIAVE, scuro ? "scuro" : "chiaro"); } catch { /* pazienza */ }
  return scuro ? "scuro" : "chiaro";
}
