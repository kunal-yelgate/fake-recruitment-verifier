import { render, screen } from "@testing-library/react";
import { VerdictHero } from "./VerdictHero";

describe("VerdictHero", () => {
  it("labels non-live results as demo results", () => {
    render(
      <VerdictHero
        score={20}
        verdict="Likely Legitimate"
        verdictBadge="success"
        summary="No live evidence was available."
        isMock
        dataQuality="demo"
      />,
    );

    expect(screen.getByText("Demo result, not a real verdict")).toBeInTheDocument();
    expect(screen.getAllByText(/not a real verdict/i)).toHaveLength(2);
    expect(screen.queryByText("Likely Legitimate")).not.toBeInTheDocument();
    expect(screen.getByText(/demo mode: simulated search results/i)).toBeInTheDocument();
  });
});
