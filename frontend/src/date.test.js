import { describe, test, expect, vi, afterEach } from "vitest";
import { dalServer, quandoRelativo } from "./date.js";

// Le date sono il posto dove i bug non si vedono: non esplode niente, si
// legge solo un orario sbagliato di due ore. Questo file protegge la regola
// che ci e' costata un pomeriggio: il server manda gli orari in UTC senza
// dirlo, e il browser li leggerebbe come ora locale.

describe("dalServer", () => {
  test("una data senza fuso viene letta come UTC", () => {
    // Senza la 'Z' aggiunta, in Italia d'estate questa diventerebbe le 09:33.
    expect(dalServer("2026-09-05T07:33:00").toISOString())
      .toBe("2026-09-05T07:33:00.000Z");
  });

  test("una data che il fuso ce l'ha gia' non si tocca", () => {
    expect(dalServer("2026-09-05T07:33:00Z").toISOString())
      .toBe("2026-09-05T07:33:00.000Z");
    expect(dalServer("2026-09-05T09:33:00+02:00").toISOString())
      .toBe("2026-09-05T07:33:00.000Z");
  });

  test("niente in entrata, niente in uscita", () => {
    expect(dalServer(null)).toBeNull();
    expect(dalServer("")).toBeNull();
  });
});

describe("quandoRelativo", () => {
  afterEach(() => vi.useRealTimers());

  function adesso(iso) {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(iso));
  }

  test("appena successo", () => {
    adesso("2026-09-05T10:00:00Z");
    // I minuti si arrotondano: sotto i 30 secondi e' "adesso", sopra diventa
    // gia' "1 min fa".
    expect(quandoRelativo("2026-09-05T09:59:45")).toBe("adesso");
    expect(quandoRelativo("2026-09-05T09:59:20")).toBe("1 min fa");
  });

  test("minuti e ore, con il singolare giusto", () => {
    adesso("2026-09-05T10:00:00Z");
    expect(quandoRelativo("2026-09-05T09:30:00")).toBe("30 min fa");
    expect(quandoRelativo("2026-09-05T09:00:00")).toBe("1 ora fa");
    expect(quandoRelativo("2026-09-05T07:00:00")).toBe("3 ore fa");
  });

  test("oltre il giorno si mostra la data", () => {
    adesso("2026-09-05T10:00:00Z");
    // Non si scrive "48 ore fa": passata la giornata quello che serve e'
    // il giorno, non il conteggio.
    expect(quandoRelativo("2026-09-03T10:00:00")).toMatch(/set/);
  });

  test("un avviso appena creato non dice 'due ore fa'", () => {
    // E' il bug vero da cui e' nato dalServer(): il server scrive l'ora UTC,
    // il browser la leggeva come locale e l'avviso nasceva gia' vecchio.
    adesso("2026-07-15T12:00:10Z");   // luglio: in Italia sono le 14:00
    expect(quandoRelativo("2026-07-15T12:00:00")).toBe("adesso");
  });
});
