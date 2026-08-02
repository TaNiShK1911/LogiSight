import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { loginUser, logoutUser, getMe, getStoredToken } from '../api/client';
import type { UserRole, CompanyType } from '../api/types';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  company_id?: number;
  company_type?: CompanyType;
  company_name?: string;
  is_admin: boolean;
}

export interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

export function useAuthProvider(): AuthContextValue {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount: check if there's a stored token and hydrate user
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    // Fetch user profile from backend
    getMe()
      .then((profile) => {
        if (profile) {
          setUser({
            id: profile.id,
            email: profile.email ?? '',
            name: profile.name ?? profile.email ?? '',
            role: profile.role as UserRole,
            company_id: profile.company_id ?? undefined,
            company_type: profile.company_type as CompanyType | undefined,
            is_admin: profile.is_admin ?? false,
          });
        }
      })
      .catch(() => {
        // Token invalid — clear it
        logoutUser();
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // Call Cognito auth via the backend
    await loginUser(email, password);

    // Fetch user profile
    const profile = await getMe();
    if (!profile) {
      throw new Error('Failed to load user profile');
    }

    setUser({
      id: profile.id,
      email: profile.email ?? '',
      name: profile.name ?? profile.email ?? '',
      role: profile.role as UserRole,
      company_id: profile.company_id ?? undefined,
      company_type: profile.company_type as CompanyType | undefined,
      is_admin: profile.is_admin ?? false,
    });
  }, []);

  const logout = useCallback(async () => {
    logoutUser();
    setUser(null);
  }, []);

  return { user, loading, login, logout };
}
