import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../api/supabase';
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
  session: Session | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

function extractUserFromSupabase(supabaseUser: User): AuthUser {
  const meta = supabaseUser.user_metadata ?? {};
  const appMeta = supabaseUser.app_metadata ?? {};

  const role: UserRole = appMeta.role ?? meta.role ?? 'client';

  return {
    id: supabaseUser.id,
    email: supabaseUser.email ?? '',
    name: meta.name ?? meta.full_name ?? supabaseUser.email ?? '',
    role,
    company_id: meta.company_id ?? appMeta.company_id,
    company_type: meta.company_type ?? appMeta.company_type,
    company_name: meta.company_name ?? appMeta.company_name,
    is_admin: meta.is_admin ?? appMeta.is_admin ?? false,
  };
}

export function useAuthProvider(): AuthContextValue {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setUser(data.session?.user ? extractUserFromSupabase(data.session.user) : null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, newSession) => {
      (async () => {
        setSession(newSession);
        setUser(newSession?.user ? extractUserFromSupabase(newSession.user) : null);
        setLoading(false);
      })();
    });

    return () => subscription.unsubscribe();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }, []);

  return { user, session, loading, login, logout };
}
