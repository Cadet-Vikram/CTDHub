// src/hooks/useAuthStore.js
import { create } from "zustand";
import { persist } from "zustand/middleware";
import api from "../utils/api";

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const res = await api.post("/auth/login", { email, password });
        const { access_token, user } = res.data;
        api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
        set({ user, token: access_token, isAuthenticated: true });
        return user;
      },

      logout: () => {
        delete api.defaults.headers.common["Authorization"];
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: "ctd-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          api.defaults.headers.common["Authorization"] = `Bearer ${state.token}`;
        }
      },
    }
  )
);
