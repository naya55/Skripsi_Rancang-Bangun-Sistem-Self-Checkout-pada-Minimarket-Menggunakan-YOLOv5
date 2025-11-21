'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';
import { doc, setDoc, getDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';

interface User {
  uid: string;
  email: string;
  displayName: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, displayName: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
  isLoggingOut: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      
      if (firebaseUser) {
        try {
          const userDoc = await getDoc(doc(db, 'users', firebaseUser.uid));
          
          if (userDoc.exists()) {
            const userData = userDoc.data();
            const userProfile: User = {
              uid: firebaseUser.uid,
              email: firebaseUser.email!,
              displayName: userData.displayName,
              role: userData.role
            };
            
            setUser(userProfile);
          } else {
            setUser(null);
          }
        } catch (error) {
          console.error('Error loading user profile:', error);
          setUser(null);
        }
      } else {
        setUser(null);
      }
      
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const userDoc = await getDoc(doc(db, 'users', userCredential.user.uid));
      
      if (!userDoc.exists()) {
        throw new Error('User tidak ditemukan. Silakan register terlebih dahulu.');
      }
      
      const userData = userDoc.data();
      
      if (userData.role !== 'admin') {
        throw new Error('Akses ditolak. Hanya admin yang diizinkan.');
      }
      
      const userProfile = {
        uid: userCredential.user.uid,
        email: userCredential.user.email!,
        displayName: userData.displayName,
        role: userData.role
      };
      
      setUser(userProfile);
      setLoading(false);
      
      return true;
      
    } catch (err: any) {
      setError(err.message || 'Login gagal. Silakan coba lagi.');
      setLoading(false);
      return false;
    }
  };

  const register = async (email: string, password: string, displayName: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      await setDoc(doc(db, 'users', userCredential.user.uid), {
        uid: userCredential.user.uid,
        email: email,
        role: 'admin',
        displayName: displayName,
        createdAt: serverTimestamp(),
        lastLogin: serverTimestamp()
      });
      
      const userProfile = {
        uid: userCredential.user.uid,
        email: userCredential.user.email!,
        displayName: displayName,
        role: 'admin'
      };
      
      setUser(userProfile);
      setLoading(false);
      
      return true;
      
    } catch (err: any) {
      setError(err.message || 'Register gagal. Silakan coba lagi.');
      setLoading(false);
      return false;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      setIsLoggingOut(true);
      await signOut(auth);
      setUser(null);
      setIsLoggingOut(false);
      router.push('/');
    } catch (error) {
      console.error('Logout error:', error);
      setIsLoggingOut(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    clearError,
    isLoggingOut
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}