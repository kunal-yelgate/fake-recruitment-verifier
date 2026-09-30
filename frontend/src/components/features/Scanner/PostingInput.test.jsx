import { fireEvent, render, screen } from "@testing-library/react";
import { PostingInput } from "./PostingInput";

describe("PostingInput URL import", () => {
  it("only enables public HTTP(S) URL fetching and reports the callback", () => {
    const onFetchUrl = vi.fn();
    render(<PostingInput text="" setText={vi.fn()} onVerify={vi.fn()} onFetchUrl={onFetchUrl} />);

    const input = screen.getByLabelText(/import from a public url/i);
    const button = screen.getByRole("button", { name: /fetch posting/i });
    expect(button).toBeDisabled();

    fireEvent.change(input, { target: { value: "https://jobs.example.test/role" } });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(onFetchUrl).toHaveBeenCalledWith("https://jobs.example.test/role");

    fireEvent.change(input, { target: { value: "file:///etc/passwd" } });
    expect(button).toBeDisabled();
  });
});
