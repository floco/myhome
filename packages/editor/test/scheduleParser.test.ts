import { describe, expect, it } from "vitest";
import { parseScheduleText } from "../src/lib/scheduleParser";

describe("parseScheduleText (English)", () => {
  it("parses a custom interval in months", () => {
    const result = parseScheduleText("Change water filter every 6 months", "en");
    expect(result).toEqual({
      name: "Change water filter",
      schedule: { frequencyType: "interval", frequency: 6, frequencyMetadata: { unit: "months" } },
    });
  });

  it("parses a custom interval in days", () => {
    const result = parseScheduleText("Clean the gutters every 14 days", "en");
    expect(result).toEqual({
      name: "Clean the gutters",
      schedule: { frequencyType: "interval", frequency: 14, frequencyMetadata: { unit: "days" } },
    });
  });

  it("parses specific weekdays, ignoring an unparsed trailing time", () => {
    const result = parseScheduleText("Take the trash out every Monday and Tuesday at 6:15 pm", "en");
    expect(result).toEqual({
      name: "Take the trash out at 6:15 pm",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1, 2] } },
    });
  });

  it("parses daily", () => {
    const result = parseScheduleText("Water the plants every day", "en");
    expect(result).toEqual({
      name: "Water the plants",
      schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses yearly", () => {
    const result = parseScheduleText("Pay the property tax every year", "en");
    expect(result).toEqual({
      name: "Pay the property tax",
      schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses a specific day of the month", () => {
    const result = parseScheduleText("Pay rent on the 1st of every month", "en");
    expect(result).toEqual({
      name: "Pay rent",
      schedule: { frequencyType: "day_of_the_month", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("falls back to a bare day interval when no unit is recognized", () => {
    const result = parseScheduleText("Rotate the mattress every 90", "en");
    expect(result).toEqual({
      name: "Rotate the mattress",
      schedule: { frequencyType: "interval", frequency: 90, frequencyMetadata: { unit: "days" } },
    });
  });

  it("returns null when nothing recurrence-like is found", () => {
    expect(parseScheduleText("Buy milk", "en")).toBeNull();
  });

  it("returns null for empty input", () => {
    expect(parseScheduleText("   ", "en")).toBeNull();
  });

  it("parses an Nth weekday of the month", () => {
    const result = parseScheduleText("Water the lawn every 2nd Tuesday of the month", "en");
    expect(result).toEqual({
      name: "Water the lawn",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } },
    });
  });

  it("parses the last weekday of every month", () => {
    const result = parseScheduleText("Pay rent the last Friday of every month", "en");
    expect(result).toEqual({
      name: "Pay rent",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_month", occurrences: [-1] } },
    });
  });

  it("parses an Nth weekday of the quarter", () => {
    const result = parseScheduleText("Rotate emergency supplies every 3rd Monday of the quarter", "en");
    expect(result).toEqual({
      name: "Rotate emergency supplies",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1], weekPattern: "week_of_quarter", occurrences: [3] } },
    });
  });
});

describe("parseScheduleText (French)", () => {
  it("parses a custom interval in months", () => {
    const result = parseScheduleText("Changer le filtre à eau tous les 6 mois", "fr");
    expect(result).toEqual({
      name: "Changer le filtre à eau",
      schedule: { frequencyType: "interval", frequency: 6, frequencyMetadata: { unit: "months" } },
    });
  });

  it("parses specific weekdays", () => {
    const result = parseScheduleText("Sortir la poubelle tous les lundis et mardis", "fr");
    expect(result).toEqual({
      name: "Sortir la poubelle",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1, 2] } },
    });
  });

  it("parses daily", () => {
    const result = parseScheduleText("Arroser les plantes tous les jours", "fr");
    expect(result).toEqual({
      name: "Arroser les plantes",
      schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses yearly", () => {
    const result = parseScheduleText("Payer la taxe foncière chaque année", "fr");
    expect(result).toEqual({
      name: "Payer la taxe foncière",
      schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses a specific day of the month", () => {
    const result = parseScheduleText("Payer le loyer le 1 de chaque mois", "fr");
    expect(result).toEqual({
      name: "Payer le loyer",
      schedule: { frequencyType: "day_of_the_month", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("returns null when nothing recurrence-like is found", () => {
    expect(parseScheduleText("Acheter du lait", "fr")).toBeNull();
  });

  it("parses an Nth weekday of the month", () => {
    const result = parseScheduleText("Nettoyer le garage le 2e mardi du mois", "fr");
    expect(result).toEqual({
      name: "Nettoyer le garage",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } },
    });
  });

  it("parses the last weekday of every month", () => {
    const result = parseScheduleText("Payer le loyer le dernier vendredi de chaque mois", "fr");
    expect(result).toEqual({
      name: "Payer le loyer",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_month", occurrences: [-1] } },
    });
  });

  it("parses an Nth weekday of the quarter", () => {
    const result = parseScheduleText("Vérifier l'extincteur le 3e lundi du trimestre", "fr");
    expect(result).toEqual({
      name: "Vérifier l'extincteur",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1], weekPattern: "week_of_quarter", occurrences: [3] } },
    });
  });
});
