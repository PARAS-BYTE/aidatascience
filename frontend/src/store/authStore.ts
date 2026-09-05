import { create } from 'zustand';
import { User, UserProfileSummary } from '../types/api';
import { apiService } from '../services/api';

const TOKEN_STORAGE_KEY = 'aidatascience_auth_token';

interface AuthState {
  token: string | null;
  user: User | null;
  profileSummary: UserProfileSummary | null;
  isLoading: boolean;
  isSummaryLoading: boolean;
  error: string | null;
  isAuthModalOpen: boolean;
  authModalMode: 'login' | 'register';

  // Actions
  openAuthModal: (mode?: 'login' | 'register') => void;
  closeAuthModal: () => void;
  login: (email: string, password: string) => Promise<boolean>;
  register: (data: { name: string; email: string; password: string; bio?: string }) => Promise<boolean>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  fetchProfileSummary: () => Promise<void>;
  updateProfile: (data: { name?: string; bio?: string; avatar?: string }) => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem(TOKEN_STORAGE_KEY),
  user: null,
  profileSummary: null,
  isLoading: false,
  isSummaryLoading: false,
  error: null,
  isAuthModalOpen: false,
  authModalMode: 'login',

  openAuthModal: (mode = 'login') => set({ isAuthModalOpen: true, authModalMode: mode, error: null }),
  closeAuthModal: () => set({ isAuthModalOpen: false, error: null }),

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiService.login(email, password);
      localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
      set({
        token: res.access_token,
        user: res.user,
        isLoading: false,
        isAuthModalOpen: false,
        error: null,
      });
      get().fetchProfileSummary();
      return true;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.error?.message || 'Login failed. Please check credentials.';
      set({ isLoading: false, error: msg });
      return false;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiService.register(data);
      localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
      set({
        token: res.access_token,
        user: res.user,
        isLoading: false,
        isAuthModalOpen: false,
        error: null,
      });
      get().fetchProfileSummary();
      return true;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.error?.message || 'Registration failed. Try a different email.';
      set({ isLoading: false, error: msg });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    set({
      token: null,
      user: null,
      profileSummary: null,
      error: null,
    });
  },

  fetchUser: async () => {
    const token = get().token;
    if (!token) return;
    try {
      const user = await apiService.getMe();
      set({ user });
      get().fetchProfileSummary();
    } catch {
      // Invalid/expired token
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      set({ token: null, user: null });
    }
  },

  fetchProfileSummary: async () => {
    const token = get().token;
    if (!token) return;
    set({ isSummaryLoading: true });
    try {
      const summary = await apiService.getProfile();
      set({ profileSummary: summary, isSummaryLoading: false });
    } catch (err) {
      set({ isSummaryLoading: false });
    }
  },

  updateProfile: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await apiService.updateProfile(data);
      set({ user: updated, isLoading: false });
      get().fetchProfileSummary();
      return true;
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to update profile.';
      set({ isLoading: false, error: msg });
      return false;
    }
  },
}));
