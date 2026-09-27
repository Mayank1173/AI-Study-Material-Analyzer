import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  getToken,
  loginRequest,
  meRequest,
  registerRequest,
  setToken,
} from '../lib/api';

const UserContext = createContext();

const DEFAULT_USER = {
  name: 'Student',
  username: '',
  email: '',
  language: 'English (US)',
  role: 'Student',
  avatarUrl: '',
};

export function UserProvider({ children }) {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('campuslearn_user');
    return savedUser ? JSON.parse(savedUser) : DEFAULT_USER;
  });
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    localStorage.setItem('campuslearn_user', JSON.stringify(user));
  }, [user]);

  // If a real session token exists, hydrate the profile from the backend so
  // the displayed name/email match the logged-in account.
  useEffect(() => {
    if (!getToken()) {
      setAuthReady(true);
      return;
    }
    let cancelled = false;
    meRequest()
      .then((me) => {
        if (cancelled) return;
        setUser((prev) => ({
          ...prev,
          id: me.id,
          name: me.name || prev.name,
          email: me.email || prev.email,
        }));
      })
      .catch(() => {
        if (!cancelled) {
          // Stale/invalid session: drop the token and reset state so route
          // guards re-render and send the user back to the login page.
          setToken('');
          setUser(DEFAULT_USER);
        }
      })
      .finally(() => {
        if (!cancelled) setAuthReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const updateUser = (newDetails) => {
    setUser((prev) => ({ ...prev, ...newDetails }));
  };

  const login = async (email, password) => {
    await loginRequest(email, password);
    const me = await meRequest();
    setUser((prev) => ({
      ...prev,
      id: me.id,
      name: me.name || prev.name,
      email: me.email || prev.email,
    }));
    return me;
  };

  const register = async (name, email, password) => {
    await registerRequest(name, email, password);
    await login(email, password);
  };

  const logout = () => {
    setToken('');
    setUser(DEFAULT_USER);
  };

  return (
    <UserContext.Provider value={{ user, updateUser, login, register, logout, authReady }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
