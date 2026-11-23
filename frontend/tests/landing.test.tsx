import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import Page from "../app/page";
describe("Local application entry", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: !url.includes("/auth/me"),
        json: async () =>
          url.includes("/auth/me") ? { detail: "Please sign in" } : [],
      })),
    );
    vi.stubGlobal("scrollTo", vi.fn());
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  it("opens the real login form from the primary action", async () => {
    render(<Page />);
    fireEvent.click(
      screen.getAllByRole("button", { name: /Find my schemes/ })[1],
    );
    expect(await screen.findByLabelText("Demo username")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Get a one-time code" }),
    ).toBeVisible();
  });
  it("switches the entry journey to Kannada", () => {
    render(<Page />);
    fireEvent.click(screen.getByRole("button", { name: "Language" }));
    expect(
      screen.getAllByRole("button", { name: /ನನ್ನ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ/ }).length,
    ).toBeGreaterThan(0);
    expect(document.documentElement.lang).toBe("kn");
  });
  it("shows meaningful privacy controls and no implied consent", () => {
    render(<Page />);
    fireEvent.click(screen.getByRole("button", { name: "Privacy & data" }));
    expect(
      screen.getByRole("heading", { name: "You control your data." }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", {
        name: "Delete this profile and its data",
      }),
    ).not.toBeInTheDocument();
  });
});
