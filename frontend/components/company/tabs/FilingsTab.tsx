'use client';

import { useEffect, useState } from 'react';
import { getFilings, type Filing } from '@/lib/api';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import Badge from '@/components/ui/Badge';
import { formatDate, toTitleCase } from '@/lib/format';
import clsx from 'clsx';

const CATEGORY_VARIANTS: Record<string, 'green' | 'blue' | 'yellow' | 'gray'> = {
  'accounts': 'green',
  'confirmation-statement': 'blue',
  'officers': 'yellow',
  'capital': 'yellow',
};

const CATEGORY_LABELS: Record<string, string> = {
  'accounts': 'Accounts',
  'confirmation-statement': 'Confirmation',
  'officers': 'Officers',
  'capital': 'Capital',
  'persons-with-significant-control': 'PSC',
  'mortgage': 'Mortgage',
  'dissolution': 'Dissolution',
  'restoration': 'Restoration',
  'insolvency': 'Insolvency',
};

function ConfirmationStatementSummary({ filings }: { filings: Filing[] }) {
  const statements = filings
    .filter(f => f.category === 'confirmation-statement')
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  if (statements.length === 0) return null;

  const latest = statements[0];
  const daysSince = Math.floor(
    (new Date().getTime() - new Date(latest.date).getTime()) / (1000 * 60 * 60 * 24)
  );
  const isStale = daysSince > 365;

  return (
    <div className={`card p-4 border-l-4 ${isStale ? 'border-yellow-400' : 'border-blue-400'} mb-2`}>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Latest Confirmation Statement
      </p>
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${isStale ? 'text-yellow-600' : 'text-blue-600'}`}>
              {isStale ? '⚠ Overdue' : '✓ Up to date'}
            </span>
            <span className="text-sm text-gray-700">
              Filed: <strong>{formatDate(latest.date)}</strong> · {daysSince} days ago
            </span>
          </div>
          <p className="text-xs text-gray-400">
            {statements.length} confirmation statement{statements.length !== 1 ? 's' : ''} on record.
            Ownership and shareholder data confirmed at this date.
          </p>
        </div>
        {latest.document_url && (
          <a
            href={latest.document_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-600 hover:underline flex-shrink-0"
          >
            View latest ↗
          </a>
        )}
      </div>
    </div>
  );
}

export default function FilingsTab({ companyNumber }: { companyNumber: string }) {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    getFilings(companyNumber)
      .then(setFilings)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyNumber]);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) return <ErrorBanner message={error} />;
  if (filings.length === 0) return <p className="text-gray-500 text-sm">No filings found.</p>;

  const categoryCounts = filings.reduce<Record<string, number>>((acc, f) => {
    const cat = f.category ?? 'other';
    acc[cat] = (acc[cat] ?? 0) + 1;
    return acc;
  }, {});
  const categories = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([cat]) => cat);

  const visible = activeCategory
    ? filings.filter(f => (f.category ?? 'other') === activeCategory)
    : filings;

  return (
    <div className="space-y-4">
      <ConfirmationStatementSummary filings={filings} />

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveCategory(null)}
          className={clsx(
            'px-3 py-1.5 rounded-full text-sm font-medium transition-colors border',
            activeCategory === null
              ? 'bg-brand-600 text-white border-brand-600'
              : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
          )}
        >
          All <span className={clsx('ml-1 text-xs', activeCategory === null ? 'opacity-80' : 'text-gray-400')}>{filings.length}</span>
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
            className={clsx(
              'px-3 py-1.5 rounded-full text-sm font-medium transition-colors border',
              activeCategory === cat
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
            )}
          >
            {CATEGORY_LABELS[cat] ?? toTitleCase(cat.replace(/-/g, ' '))}
            <span className={clsx('ml-1 text-xs', activeCategory === cat ? 'opacity-80' : 'text-gray-400')}>
              {categoryCounts[cat]}
            </span>
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {visible.map(f => {
          const isCS01 = f.category === 'confirmation-statement';
          return (
            <div
              key={f.id}
              className={clsx('card p-4', isCS01 && 'ring-1 ring-blue-200')}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {toTitleCase(f.description ?? f.type ?? '')}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formatDate(f.date)} · {f.transaction_id}
                  </p>
                  {isCS01 && (
                    <p className="text-xs text-blue-600 mt-1">
                      Ownership &amp; shareholder data confirmed at this date
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {f.category && (
                    <Badge variant={CATEGORY_VARIANTS[f.category] ?? 'gray'}>
                      {f.type ?? CATEGORY_LABELS[f.category] ?? f.category}
                    </Badge>
                  )}
                  {f.document_url && (
                    <a
                      href={f.document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand-600 hover:underline"
                    >
                      View ↗
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}