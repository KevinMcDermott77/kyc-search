'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AuthGuard from '@/components/layout/AuthGuard';
import { listCases, type CaseListItem } from '@/lib/api';
import { formatDate } from '@/lib/format';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import clsx from 'clsx';

type StatusFilter = 'all' | 'pending' | 'approved' | 'flagged' | 'closed';

const STATUS_FILTERS: { id: StatusFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'approved', label: 'Approved' },
  { id: 'flagged', label: 'Flagged' },
  { id: 'closed', label: 'Closed' },
];

const STATUS_STYLES: Record<string, string> = {
  pending:  'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  flagged:  'bg-red-100 text-red-800',
  closed:   'bg-gray-100 text-gray-600',
};

const RISK_STYLES: Record<string, string> = {
  HIGH:   'bg-red-100 text-red-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW:    'bg-green-100 text-green-800',
};

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    listCases(statusFilter === 'all' ? undefined : statusFilter)
      .then(setCases)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <AuthGuard>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-gray-900">Cases</h1>
        </div>

        {/* Status filter pills */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {STATUS_FILTERS.map(f => (
            <button
              key={f.id}
              onClick={() => setStatusFilter(f.id)}
              className={clsx(
                'px-4 py-1.5 rounded-full text-sm font-medium transition-colors border',
                statusFilter === f.id
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-brand-400'
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && <ErrorBanner message={error} />}

        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : cases.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p className="text-4xl mb-3">📁</p>
            <p className="font-medium text-gray-600">No cases yet</p>
            <p className="text-sm mt-1">
              Run a screening on a company and click <strong>Save as Case</strong> to create one.
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Company</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Risk</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hidden sm:table-cell">Created</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hidden md:table-cell">Created by</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {cases.map(c => (
                  <tr
                    key={c.id}
                    onClick={() => router.push(`/cases/${c.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{c.company_name}</p>
                      <p className="text-xs text-gray-400 font-mono">{c.company_number}</p>
                    </td>
                    <td className="px-4 py-3">
                      {c.risk_label ? (
                        <div className="flex items-center gap-2">
                          <span className={clsx('text-xs font-semibold px-2 py-0.5 rounded-full', RISK_STYLES[c.risk_label])}>
                            {c.risk_label}
                          </span>
                          {c.risk_score !== null && (
                            <span className="text-xs text-gray-400">{c.risk_score}/100</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('text-xs font-semibold px-2 py-0.5 rounded-full capitalize', STATUS_STYLES[c.status] ?? 'bg-gray-100 text-gray-600')}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">
                      {c.created_at ? formatDate(c.created_at.slice(0, 10)) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs hidden md:table-cell">
                      {c.created_by_email ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-brand-600 text-xs font-medium">View →</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
