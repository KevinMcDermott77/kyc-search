'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { clearToken } from '@/lib/api';
import clsx from 'clsx';

const NAV = [
  { href: '/search', label: 'Search' },
  { href: '/cases', label: 'Cases' },
];

export default function Header({ isAdmin }: { isAdmin?: boolean }) {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push('/login');
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/search" className="flex items-center gap-2">
            <span className="text-xl">🔎</span>
            <span className="font-bold text-brand-700 text-lg tracking-tight">Kev YC</span>
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map(link => (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  pathname.startsWith(link.href)
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                )}
              >
                {link.label}
              </Link>
            ))}
            {isAdmin && (
              <Link
                href="/admin"
                className={clsx(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  pathname === '/admin'
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                )}
              >
                Admin
              </Link>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://find-and-update.company-information.service.gov.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline text-xs text-gray-400 hover:text-brand-600 transition-colors"
          >
            Companies House ↗
          </a>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-800 transition-colors border border-gray-200 px-3 py-1 rounded-md hover:bg-gray-50"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
