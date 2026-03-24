import { clearStoredToken, getStoredToken, setStoredToken } from "./auth-storage";

describe("auth storage", () => {
  it("stores and clears the access token", () => {
    setStoredToken("token-123");
    expect(getStoredToken()).toBe("token-123");
    clearStoredToken();
    expect(getStoredToken()).toBeNull();
  });
});
