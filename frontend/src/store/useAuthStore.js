import { create } from "zustand";
import {
  getCurrentAdmin,
  getStoredSession,
  loginAdmin,
  registerAdmin,
  logoutAdmin,
  setStoredSession,
} from "../services/api";

export const useAuthStore = create((set) => ({
  session: getStoredSession(),
  admin: getStoredSession()?.admin ?? null,
  isLoading: false,
  error: "",
  async restoreSession() {
    const session = getStoredSession();
    if (!session?.token) {
      set({ session: null, admin: null });
      return;
    }

    // If Zustand already has a valid session object (e.g. from the
    // localStorage initialiser on line 12-13), skip the network
    // round-trip — avoids wiping the session on HMR / fast navigation.
    const currentState = useAuthStore.getState();
    if (currentState.session?.token === session.token && currentState.admin) {
      return;
    }

    set({ isLoading: true, error: "" });
    try {
      const admin = await getCurrentAdmin();
      const nextSession = { token: session.token, admin };
      setStoredSession(nextSession);
      set({ session: nextSession, admin, isLoading: false, error: "" });
    } catch (error) {
      setStoredSession(null);
      set({ session: null, admin: null, isLoading: false, error: error.message || "Session expired." });
    }
  },
  async signIn(credentials) {
    set({ isLoading: true, error: "" });
    try {
      const result = await loginAdmin(credentials);
      const session = { token: result.token, admin: result.admin };
      setStoredSession(session);
      set({ session, admin: result.admin, isLoading: false, error: "" });
      return result.admin;
    } catch (error) {
      set({ isLoading: false, error: error.message || "Unable to sign in." });
      throw error;
    }
  },
  async register(payload) {
    set({ isLoading: true, error: "" });
    try {
      const admin = await registerAdmin(payload);
      set({ isLoading: false, error: "" });
      return admin;
    } catch (error) {
      set({ isLoading: false, error: error.message || "Unable to register admin." });
      throw error;
    }
  },
  async signOut() {
    try {
      await logoutAdmin();
    } catch {
      // Ignore logout failures and clear local session anyway.
    }
    setStoredSession(null);
    set({ session: null, admin: null, isLoading: false, error: "" });
  },
}));
