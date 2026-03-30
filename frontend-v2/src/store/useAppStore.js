import { create } from "zustand";
import { getUsers } from "../services/api";

export const useAppStore = create((set, get) => ({
  users: [],
  selectedUserId: "",
  isLoadingUsers: false,
  usersError: "",
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
}));
