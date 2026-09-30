import { fireEvent, render, screen } from "@testing-library/react";
import { LandingPage } from "./LandingPage";

vi.mock("@clerk/react", () => ({
  SignInButton: ({ children }) => children,
}));

describe("LandingPage authentication UX", () => {
  const baseProps = {
    isDark: true,
    onToggleTheme: vi.fn(),
    onEnter: vi.fn(),
  };

  it("requires sign-in before offering the scanner", () => {
    render(<LandingPage {...baseProps} requireAuth />);

    expect(
      screen.getByRole("button", { name: /sign in to scan/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /scan a recruiter message/i }),
    ).not.toBeInTheDocument();
  });

  it("offers the scanner CTA after authentication", () => {
    render(<LandingPage {...baseProps} />);

    fireEvent.click(
      screen.getByRole("button", { name: /scan a recruiter message/i }),
    );

    expect(baseProps.onEnter).toHaveBeenCalledTimes(1);
  });
});
