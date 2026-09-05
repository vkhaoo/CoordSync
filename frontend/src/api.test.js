import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";

// La parte di api.js che ragiona: cosa fare quando il server non risponde.
//
// E' il pezzo di frontend piu' facile da rompere senza accorgersene, perche'
// per vederlo in azione bisogna spegnere il server. Qui il server si finge
// spento in un millisecondo.
//
// Nota: si importa il modulo con import() dentro ogni test e si azzera la
// cache dei moduli, perche' api.js ha uno stato suo (il token, il contatore
// delle richieste in attesa) che non deve passare da un test all'altro.

async function caricaApi() {
  vi.resetModules();
  return await import("./api.js");
}

function rispostaFinta(corpo, stato = 200) {
  return {
    ok: stato >= 200 && stato < 300,
    status: stato,
    json: async () => corpo,
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// I tentativi aspettano 1,5 s e 3 s: con gli orologi finti bisogna far
// scorrere il tempo, se no il test resta li' a guardare.
async function conIlTempoCheScorre(promessa) {
  const risultato = promessa.catch((e) => ({ errore: e }));
  await vi.runAllTimersAsync();
  return risultato;
}

describe("quando il server non risponde", () => {
  test("una lettura viene riprovata tre volte", async () => {
    const fetchFinto = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchFinto);
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(api.progetti());

    expect(fetchFinto).toHaveBeenCalledTimes(3);
    expect(esito.errore.message).toContain("Non riesco a contattare il server");
  });

  test("basta che uno dei tentativi vada a buon fine", async () => {
    const fetchFinto = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(rispostaFinta([{ id: 1, nome: "Linea 3" }]));
    vi.stubGlobal("fetch", fetchFinto);
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(api.progetti());

    expect(fetchFinto).toHaveBeenCalledTimes(2);
    expect(esito).toEqual([{ id: 1, nome: "Linea 3" }]);
  });

  test("una SCRITTURA non si riprova mai", async () => {
    // E' la regola piu' importante del file: se la richiesta era arrivata e
    // si e' persa solo la risposta, riprovare creerebbe un doppione — due
    // lavori, due commenti, due voci di storico.
    const fetchFinto = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchFinto);
    const { api } = await caricaApi();

    await conIlTempoCheScorre(api.creaProgetto({ nome: "Nuovo" }));

    expect(fetchFinto).toHaveBeenCalledTimes(1);
  });

  test("chi guarda viene avvisato che si sta riprovando, e poi che e' finita", async () => {
    const fetchFinto = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchFinto);
    const { api, quandoIlServerSiSveglia } = await caricaApi();

    const avvisi = [];
    quandoIlServerSiSveglia((inCorso) => avvisi.push(inCorso));
    await conIlTempoCheScorre(api.progetti());

    expect(avvisi[0]).toBe(true);                    // "mi sto svegliando"
    expect(avvisi[avvisi.length - 1]).toBe(false);   // e alla fine si spegne
  });
});

describe("gli errori diventano frasi comprensibili", () => {
  test("la sessione scaduta si spiega, non si dice 'Unauthorized'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      rispostaFinta({ detail: "Token non valido o scaduto" }, 401)));
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(api.progetti());
    expect(esito.errore.message).toContain("sessione");
    expect(esito.errore.stato).toBe(401);
  });

  test("il 401 dell'accesso resta quello del server", async () => {
    // Sbagliando la password si deve leggere "email o password non validi",
    // non "la tua sessione e' scaduta": la sessione non c'era proprio.
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      rispostaFinta({ detail: "Email o password non validi" }, 401)));
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(
      api.login({ email: "a@a.it", password: "x" }));
    expect(esito.errore.message).toBe("Email o password non validi");
  });

  test("un guasto del server non mostra il traceback a nessuno", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(rispostaFinta({}, 500)));
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(api.progetti());
    expect(esito.errore.message).toContain("problema");
    expect(esito.errore.stato).toBe(500);
  });

  test("gli errori di validazione diventano un elenco leggibile", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(rispostaFinta({
      detail: [{ msg: "La password e' troppo corta" },
               { msg: "Serve almeno un numero" }],
    }, 422)));
    const { api } = await caricaApi();

    const esito = await conIlTempoCheScorre(
      api.creaProgetto({ nome: "" }));
    expect(esito.errore.message).toBe("La password e' troppo corta; Serve almeno un numero");
  });
});

describe("il token", () => {
  test("si allega alle richieste e sopravvive al ricaricamento", async () => {
    const fetchFinto = vi.fn().mockResolvedValue(rispostaFinta([]));
    vi.stubGlobal("fetch", fetchFinto);
    const { api, setToken } = await caricaApi();

    setToken("abc123");
    await conIlTempoCheScorre(api.progetti());

    const intestazioni = fetchFinto.mock.calls[0][1].headers;
    expect(intestazioni.Authorization).toBe("Bearer abc123");
    // ed e' finito nel browser, cosi' ricaricando la pagina si resta dentro
    expect(localStorage.getItem("coordsync_token")).toBe("abc123");
  });

  test("uscendo sparisce", async () => {
    const { setToken, getToken } = await caricaApi();
    setToken("abc123");
    setToken(null);

    expect(getToken()).toBeNull();
    expect(localStorage.getItem("coordsync_token")).toBeNull();
  });
});
