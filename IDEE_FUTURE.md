# Idee future (parcheggio)

Idee buone che NON entrano nel V1, per non cadere nello scope creep.
Si riprendono quando il V1 è completo, finito e usato.

- **Chat real-time nell'app.** Richiede websocket (tecnologia diversa: stream
  sempre aperto, stato connessione, "sta scrivendo"...). Rimandata.
  → Alternativa scelta per il V1: **commenti attaccati al singolo lavoro**
    (coordina meglio perché la conversazione resta legata al lavoro, ed è molto
    più semplice da costruire).
- **Notifiche** (email / push) quando cambia lo stato o arriva un commento.
- **Allegati** ai lavori (foto dal campo, PDF di schemi).
- **Scadenze / calendario** dei lavori.
- **Ruoli e permessi** (chi può creare progetti, chi solo lavori, ecc.).

## Squadre dentro un'azienda (deciso: ISOLAMENTO vero)

- Gerarchia: Organizzazione -> Squadre (es. Digitale, Automazione) -> utenti/progetti.
- Scelta: isolamento vero (Digitale NON vede i lavori di Automazione).
  E' un secondo livello di multi-tenancy annidato: guardie + filtri come per
  l'organizzazione, ma su un piano piu' fine. Lavoro impegnativo -> milestone a se'.
- Prerequisito: prima va chiuso il flusso di registrazione (signup + ruoli).

## Ruoli & permessi (famiglia — progettare INSIEME)

Queste tre idee sono la stessa famiglia (sistema di autorizzazione). Da fare
come blocco unico e ragionato DOPO il V1, non a pezzi sparsi.

- **Trasferire/aggiungere admin.** Oggi l'admin e' solo chi registra l'azienda:
  se se ne va, azienda senza timone. Serve endpoint "promuovi ad admin" /
  "trasferisci ruolo" (protetto: solo un admin). Modifica piccola (flag is_admin).
- **Privilegi read/write in stile Active Directory.** Ruoli tipo caposquadra
  (crea progetti/lavori) vs operatore (vede e aggiorna i suoi). E' un vero
  sistema di ruoli/permessi: `is_admin` e' gia' il primo mattone.
- **Squadre con isolamento** (gia' sopra) — imparentata: chi vede cosa.

## Sicurezza avanzata (quando sara' in produzione)

- **2FA (autenticazione a due fattori).** Codici temporanei (app TOTP / SMS),
  recovery code, flusso attiva/disattiva. Capitolo serio: da fare quando il
  prodotto e' online e usato, NON nel V1. Prematuro ora.

## Un utente in PIU' aziende

- Oggi un utente appartiene a UNA sola organizzazione (`Utente.organizzazione_id`,
  legame uno-a-molti). Idea: una persona che collabora con piu' aziende dovrebbe
  poter far parte di piu' organizzazioni con un unico account.
- Impatto sul modello: diventa un molti-a-molti Utente <-> Organizzazione
  (tabella-ponte, es. "membership", magari con un ruolo per azienda). Cambia
  anche il login/token: servirebbe scegliere "con quale azienda sto lavorando
  ora" (contesto attivo) e filtrare i dati in base a quello.
- E' imparentata con la famiglia "ruoli & permessi": il ruolo diventa per-azienda,
  non globale. Da progettare INSIEME a quel blocco, dopo il V1.
- Nota: e' un cambio strutturale non banale (tocca ancora, token, filtri). Non un
  ritocco: va pianificato come milestone.

## Sicurezza da produzione (blocco per il DEPLOY, non prima)

Base gia' presente e solida: password hashate (bcrypt), accesso via token,
isolamento multi-tenant. Questi sono STRATI AGGIUNTIVI, da fare al deploy:

- **Robustezza password**: lunghezza minima + regole (aggiunta piccola, si puo'
  anticipare). Oggi accetta anche "1".
- **Verifica email**: link di conferma alla registrazione. Richiede un servizio
  di invio email (SendGrid/Postmark/...). Prerequisito anche per il recupero.
- **Recupero password** ("password dimenticata"): dipende dall'invio email.
- **Limite tentativi di login** (rate limiting) contro attacchi a forza bruta.
- **HTTPS**: connessione cifrata. Non e' codice: arriva col deploy su piattaforma
  seria. Non farlo ora (in locale non serve).
- **2FA** (gia' nel magazzino sopra): dopo il resto.

## Dark mode (frontend)

- Tema scuro alternabile (preferenza dell'utente). Richiede di rivedere TUTTA la
  palette dei colori: sfondi, testo, card colorate per stato, badge priorità.
- Approccio pulito: variabili CSS gia' impostate (:root) + una classe "tema-scuro"
  che le ridefinisce, con un interruttore che la attiva. Salvare la preferenza.
- Non un ritocco: tocca ogni colore. Milestone frontend a se'.

## Sicurezza del token (quando sara' prodotto)

- Oggi il token JWT sta in localStorage (pragmatico, diffuso). Limite: e'
  leggibile da eventuale JS malevolo (rischio XSS).
- Alternativa piu' robusta: cookie httpOnly (il JS non li legge). Piu' complessi
  da gestire (CSRF, gestione lato backend). Da valutare se CoordSync diventa
  un prodotto con clienti veri.

## Onboarding utenti: creazione diretta vs inviti

Due modelli per far entrare persone in un'azienda:

- **Modello 1 - creazione diretta (ATTUALE).** L'admin inserisce nome/email/password.
  Comodo per squadre sul campo (operai poco avvezzi alla tecnologia). Difetto:
  l'admin conosce la password iniziale.
  -> Miglioramento minimo: OBBLIGO cambio password al primo accesso (chiude il
     difetto restando su questo modello). Serve un flag "deve_cambiare_password".

- **Modello 2 - inviti via email (MODERNO, "SaaS").** L'admin inserisce solo
  nome+email. Il sistema manda un invito con link; l'utente sceglie LUI la
  password. Piu' sicuro/privacy. Come Slack/Notion/Google. Richiede il servizio
  email funzionante. Riusa il meccanismo token-con-scopo della verifica email
  (scopo "invito"). Da fare DOPO aver collegato un servizio email reale.

- Molti prodotti offrono ENTRAMBI. Scelta consigliata: tenere il Modello 1 ora,
  aggiungere l'obbligo cambio-password, poi il Modello 2 a inviti col servizio email.
