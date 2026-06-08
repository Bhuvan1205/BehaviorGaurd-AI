import { create } from "zustand";
import { getUsers } from "../services/api";

export const useAppStore = create((set, get) => ({
  users: [],
  selectedUserId: "",
  isLoadingUsers: false,
  usersError: "",
  _refreshInterval: null,

  async loadUsers() {
    if (get().isLoadingUsers) {
      return;
    }

    set({ isLoadingUsers: true, usersError: "" });

    try {
      const users = await getUsers();
      const currentSelected = get().selectedUserId;
      const hasCurrentSelection = users.some((user) => user.user_id === currentSelected);
      const nextSelectedUserId = hasCurrentSelection ? currentSelected : "";

      set({
        users,
        selectedUserId: nextSelectedUserId,
        isLoadingUsers: false,
        usersError: "",
      });
    } catch (error) {
      set({
        isLoadingUsers: false,
        usersError: error.message || "Unable to load users.",
      });
    }
  },

  selectUser(userId) {
    set({ selectedUserId: userId });
  },

  // Auto-refresh users every `intervalMs` milliseconds (default 15s).
  // Call once from AppLayout; it will keep data fresh across all pages.
  startAutoRefresh(intervalMs = 15000) {
    const existing = get()._refreshInterval;
    if (existing) clearInterval(existing);

    // Load immediately, then on the interval
    get().loadUsers();
    const id = setInterval(() => get().loadUsers(), intervalMs);
    set({ _refreshInterval: id });
  },

  stopAutoRefresh() {
    const existing = get()._refreshInterval;
    if (existing) {
      clearInterval(existing);
      set({ _refreshInterval: null });
    }
  },
}));
