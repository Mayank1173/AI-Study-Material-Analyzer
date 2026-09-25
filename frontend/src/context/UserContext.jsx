import React, { createContext, useContext, useState, useEffect } from 'react';

const UserContext = createContext();

export function UserProvider({ children }) {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('campuslearn_user');
    return savedUser
      ? JSON.parse(savedUser)
      : {
          name: 'Mayank',
          username: 'foundationalproject',
          email: 'foundationalproject4@gmail.com',
          language: 'English (US)',
          role: 'Student',
          avatarUrl: '',
        };
  });

  useEffect(() => {
    localStorage.setItem('campuslearn_user', JSON.stringify(user));
  }, [user]);

  const updateUser = (newDetails) => {
    setUser((prev) => ({ ...prev, ...newDetails }));
  };

  return (
    <UserContext.Provider value={{ user, updateUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}