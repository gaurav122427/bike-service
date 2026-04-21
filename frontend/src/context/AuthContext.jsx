import { createContext, useContext, useState, useCallback } from "react";
import axios from "axios";

const AuthContext = createContext(null);

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("kwick_token"));

  const login = useCallback(async (username, password) => {
    // Explicit string encoding is the most reliable for OAuth2 form data
    const body = `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;

    const { data } = await axios.post(`${API_URL}/login`, body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    localStorage.setItem("kwick_token", data.access_token);
    setToken(data.access_token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("kwick_token");
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
