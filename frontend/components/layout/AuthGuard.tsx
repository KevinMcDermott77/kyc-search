'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getMe } from '@/lib/api';
import Header from './Header';
import Spinner from '@/components/ui/Spinner';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    getMe()
      .then(u => { setIsAdmin(u.is_admin); setReady(true); })
      .catch(() => router.replace('/login'));
  }, [router]);

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <>
      <Header isAdmin={isAdmin} />
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </>
  );
}
