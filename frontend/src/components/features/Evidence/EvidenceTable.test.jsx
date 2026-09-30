import { fireEvent, render, screen } from "@testing-library/react";
import { EvidenceTable } from "./EvidenceTable";

const signals = [
  {
    signal_name: "Company footprint",
    finding: "Official careers page found",
    engine: "google",
    status: "pass",
    score_delta: -10,
  },
  {
    signal_name: "Duplicate posting",
    finding: "Copied listing found",
    engine: "google",
    status: "fail",
    score_delta: 20,
  },
];

describe("EvidenceTable", () => {
  it("filters evidence by threat status", () => {
    render(<EvidenceTable signals={signals} />);

    fireEvent.click(screen.getByRole("button", { name: /Threats/i }));

    expect(screen.getByText("Duplicate posting")).toBeInTheDocument();
    expect(screen.queryByText("Company footprint")).not.toBeInTheDocument();
  });

  it("filters evidence by finding text", () => {
    render(<EvidenceTable signals={signals} />);

    fireEvent.change(screen.getByPlaceholderText("Search findings..."), {
      target: { value: "official" },
    });

    expect(screen.getByText("Company footprint")).toBeInTheDocument();
    expect(screen.queryByText("Duplicate posting")).not.toBeInTheDocument();
  });
});
