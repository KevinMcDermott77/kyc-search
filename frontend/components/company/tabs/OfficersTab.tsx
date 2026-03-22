'use client';

import { useEffect, useState } from 'react';
import { getOfficers, type Officer } from '@/lib/api';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import Badge from '@/components/ui/Badge';
import { toTitleCase, formatDate, formatRole } from '@/lib/format';
import clsx from 'clsx';

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

type Filter = 'all' | 'active' | 'resigned';

export default function OfficersTab({ companyNumber }: { companyNumber: string }) {
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<Filter>('active');

  useEffect(() => {
    getOfficers(companyNumber)
      .then(setOfficers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyNumber]);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) return <ErrorBanner message={error} />;
  if (officers.length === 0) return <p className="text-gray-500 text-sm">No officers found.</p>;

  const active = officers.filter(o => !o.resigned_on);
  const resigned = officers.filter(o => o.resigned_on);
  const visible = filter === 'all' ? officers : filter === 'active' ? active : resigned;

  const FILTERS: { id: Filter; label: string; count: number }[] = [
    { id: 'active', label: 'Active', count: active.length },
    { id: 'resigned', label: 'Resigned', count: resigned.length },
    { id: 'all', label: 'All', count: officers.length },
  ];

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={clsx(
              'px-3 py-1.5 rounded-full text-sm font-medium transition-colors border',
              filter === f.id
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
            )}
          >
            {f.label}
            <span className={clsx('ml-1.5 text-xs', filter === f.id ? 'opacity-80' : 'text-gray-400')}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Results */}
      {visible.length === 0 ? (
        <p className="text-gray-400 text-sm">No officers in this category.</p>
      ) : (
        <div className="space-y-2">
          {visible.map(o => (
            <div key={o.id} className={clsx('card p-4', o.resigned_on && filter !== 'active' && 'opacity-60')}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">{toTitleCase(o.name)}</p>
                    {o.resigned_on && (
                      <span className="badge badge-gray text-xs">Resigned</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {formatRole(o.role)}
                    {o.appointed_on && ` · Appointed ${formatDate(o.appointed_on)}`}
                    {o.resigned_on && ` · Resigned ${formatDate(o.resigned_on)}`}
                  </p>
                  {(o.birth_month || o.birth_year) && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      DOB: {o.birth_month ? MONTHS[o.birth_month - 1] : '?'} {o.birth_year ?? ''}
                    </p>
                  )}
                  {o.service_address_locality && (
                    <p className="text-xs text-gray-400">
                      {[o.service_address_line1, o.service_address_locality, o.service_address_postal_code, o.service_address_country].filter(Boolean).join(', ')}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-1 items-end">
                  {o.nationality && <Badge variant="gray">{toTitleCase(o.nationality)}</Badge>}
                  {o.occupation && <span className="text-xs text-gray-400">{toTitleCase(o.occupation)}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
