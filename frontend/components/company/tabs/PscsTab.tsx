'use client';

import { useEffect, useState } from 'react';
import { getPscs, type Psc } from '@/lib/api';
import Link from 'next/link';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import Badge from '@/components/ui/Badge';
import { toTitleCase, formatDate, formatKind } from '@/lib/format';

function controlLabel(s: string): string {
  return s.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function PscsTab({ companyNumber }: { companyNumber: string }) {
  const [pscs, setPscs] = useState<Psc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getPscs(companyNumber)
      .then(setPscs)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyNumber]);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) return <ErrorBanner message={error} />;
  if (pscs.length === 0) return <p className="text-gray-500 text-sm">No persons with significant control found.</p>;

  return (
    <div className="space-y-2">
      {pscs.map(psc => (
        <div key={psc.id} className={`card p-4 ${psc.ceased_on ? 'opacity-60' : ''}`}>
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium text-gray-900">{toTitleCase(psc.name)}</p>
                {psc.linked_company_number && (
                  <Link
                    href={`/company/${psc.linked_company_number}`}
                    className="text-xs text-brand-600 hover:underline"
                  >
                    {psc.linked_company_number} →
                  </Link>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-0.5">
                {formatKind(psc.kind)}
                {psc.notified_on && ` · Notified ${formatDate(psc.notified_on)}`}
                {psc.ceased_on && ` · Ceased ${formatDate(psc.ceased_on)}`}
              </p>
              {psc.natures_of_control && psc.natures_of_control.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {psc.natures_of_control.map(n => (
                    <Badge key={n} variant="blue">{controlLabel(n)}</Badge>
                  ))}
                </div>
              )}
            </div>
            <div className="flex flex-col gap-1 items-end text-xs text-gray-400">
              {psc.nationality && <span>{toTitleCase(psc.nationality)}</span>}
              {psc.country_of_residence && <span>{toTitleCase(psc.country_of_residence)}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
