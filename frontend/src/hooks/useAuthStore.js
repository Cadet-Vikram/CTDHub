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
        const body = new URLSearchParams();
        body.append("username", email);
        body.append("password", password);

        const res = await api.post("/api/auth/login", body.toString(), {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });
        const { access_token, role } = res.data;
        const user = { email, full_name: email, role: role || "user" };
        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        set({ user, token: access_token, isAuthenticated: true });
        return user;
      },

      logout: () => {
        delete api.defaults.headers.common.Authorization;
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: "ctd-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          api.defaults.headers.common.Authorization = `Bearer ${state.token}`;
        }
      },
    }
  )
);
