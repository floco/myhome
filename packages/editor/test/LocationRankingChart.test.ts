import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationRankingChart from "../src/lib/components/LocationRankingChart.svelte";

const criteria = [{ id: "c1", name: "Cost", description: "", weight: "high" as const }];

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationRankingChart", () => {
  it("sorts locations by weighted score descending and crowns the top one", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "Nantes", emoji: "🇫🇷" },
          { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
        ],
        criteria,
        ratings: [
          { locationId: "l1", criterionId: "c1", score: 2, note: "" },
          { locationId: "l2", criterionId: "c1", score: 5, note: "" },
        ],
      },
    });
    flushSync();
    const rows = Array.from(el.querySelectorAll(".row"));
    expect(rows[0].querySelector(".name")?.textContent).toBe("Ljubljana");
    expect(rows[0].querySelector(".crown")).not.toBeNull();
    expect(rows[1].querySelector(".crown")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows unrated locations last with a dash", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "Rated", emoji: "📍" },
          { id: "l2", name: "Unrated", emoji: "📍" },
        ],
        criteria,
        ratings: [{ locationId: "l1", criterionId: "c1", score: 3, note: "" }],
      },
    });
    flushSync();
    const rows = Array.from(el.querySelectorAll(".row"));
    expect(rows[1].querySelector(".name")?.textContent).toBe("Unrated");
    expect(rows[1].querySelector(".score")?.textContent).toBe("—");
    unmount(comp);
    el.remove();
  });

  it("crowns tied top locations", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "A", emoji: "📍" },
          { id: "l2", name: "B", emoji: "📍" },
        ],
        criteria,
        ratings: [
          { locationId: "l1", criterionId: "c1", score: 4, note: "" },
          { locationId: "l2", criterionId: "c1", score: 4, note: "" },
        ],
      },
    });
    flushSync();
    expect(el.querySelectorAll(".crown").length).toBe(2);
    unmount(comp);
    el.remove();
  });
});
