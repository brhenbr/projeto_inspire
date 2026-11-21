import { describe, expect, it, vi } from "vitest";

import { fmtDate, fmtNum, fmtValue, minutesUntil, nota, toneOfNota } from "./format";

describe("format", () => {
  it("datas inválidas viram traço", () => {
    expect(fmtDate(null)).toBe("—");
    expect(fmtDate("lixo")).toBe("—");
    expect(fmtDate("2026-03-05T12:00:00Z")).toMatch(/05\/03\/2026/);
  });
  it("números em pt-BR", () => {
    expect(fmtNum(20700)).toBe("20.700");
    expect(fmtNum(null)).toBe("—");
  });
  it("notas e tons", () => {
    expect(nota("72.5")).toBe(72.5);
    expect(nota(null)).toBeNull();
    expect([toneOfNota(80), toneOfNota(55), toneOfNota(10), toneOfNota(null)]).toEqual(["bom", "medio", "ruim", "neutro"]);
  });
  it("valores para exibição", () => {
    expect(fmtValue(["a", "b"])).toBe("a, b");
    expect(fmtValue(null)).toBe("(vazio)");
    expect(fmtValue("")).toBe("(vazio)");
  });
  it("minutos até um horário", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T10:00:00Z"));
    expect(minutesUntil("2026-01-01T10:30:00Z")).toBe(30);
    expect(minutesUntil("2026-01-01T09:00:00Z")).toBe(0);
    expect(minutesUntil(null)).toBeNull();
    vi.useRealTimers();
  });
});
