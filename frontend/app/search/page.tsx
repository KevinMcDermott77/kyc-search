'use client';

import { useState } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { searchCompanies, type CompanySearchResult } from '@/lib/api';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import Badge from '@/components/ui/Badge';
import Link from 'next/link';

const CH_BASE = 'https://find-and-update.company-information.service.gov.uk/company';

function statusVariant(status: string | null): 'green' | 'red' | 'gray' {
  if (!status) return 'gray';
  if (status === 'active') return 'green';
  if (['dissolved', 'liquidation', 'receivership'].includes(status)) return 'red';
  return 'gray';
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  async function doSearch(q: string, p = 1) {
    if (!q.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await searchCompanies(q, p);
      setResults(data.items);
      setTotal(data.total_results);
      setPage(p);
      setSearched(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    doSearch(query, 1);
  }

  const totalPages = Math.ceil(total / 20);

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto">

        {/* Hero — shown before first search */}
        {!searched && (
          <div className="text-center py-12 mb-8">
            <div className="text-5xl mb-4">🔎</div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Kev YC</h1>
            <p className="text-gray-500 text-base mb-1">
              UK company KYC lookup
            </p>
            <p className="text-gray-400 text-sm">
              Officers · PSCs · Filings · Ownership · Risk flags — all from Companies House
            </p>
          </div>
        )}

        {/* Search form */}
        <form onSubmit={handleSubmit} className="flex gap-3 mb-6">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Company name or number…"
            className="input flex-1"
            autoFocus={!searched}
          />
          <button type="submit" disabled={loading || !query.trim()} className="btn-primary px-6">
            {loading ? <Spinner size="sm" /> : 'Search'}
          </button>
        </form>

        {error && <ErrorBanner message={error} />}

        {searched && !loading && (
          <p className="text-sm text-gray-500 mb-4">
            {total.toLocaleString()} result{total !== 1 ? 's' : ''}
            {query && <span> for &ldquo;{query}&rdquo;</span>}
          </p>
        )}

        <div className="space-y-2">
          {results.map(c => (
            <div key={c.company_number} className="card p-4 hover:border-brand-300 hover:shadow-md transition-all">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <Link href={`/company/${c.company_number}`} className="group">
                    <p className="font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                      {c.company_name}
                    </p>
                  </Link>
                  <p className="text-sm text-gray-400 mt-0.5">
                    {c.company_number}
                    {c.date_of_creation && ` · Incorporated ${c.date_of_creation}`}
                    {c.company_type && ` · ${c.company_type}`}
                  </p>
                  {c.registered_office_address && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      {[
                        c.registered_office_address.address_line_1,
                        c.registered_office_address.locality,
                        c.registered_office_address.postal_code,
                      ].filter(Boolean).join(', ')}
                    </p>
                  )}
                  {c.snippet && <p className="text-xs text-gray-500 mt-1 italic">{c.snippet}</p>}
                  {/* Action links */}
                  <div className="flex items-center gap-3 mt-2">
                    <Link
                      href={`/company/${c.company_number}`}
                      className="text-xs font-medium text-brand-600 hover:text-brand-800 hover:underline"
                    >
                      View full profile →
                    </Link>
                    <a
                      href={`${CH_BASE}/${c.company_number}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
                      onClick={e => e.stopPropagation()}
                    >
                      Companies House ↗
                    </a>
                  </div>
                </div>
                <div className="flex flex-col gap-1 items-end flex-shrink-0">
                  <Badge variant={statusVariant(c.company_status)}>{c.company_status ?? 'unknown'}</Badge>
                </div>
              </div>
            </div>
          ))}
        </div>

        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-3 mt-6">
            <button
              onClick={() => doSearch(query, page - 1)}
              disabled={page <= 1 || loading}
              className="btn-secondary"
            >
              ← Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => doSearch(query, page + 1)}
              disabled={page >= totalPages || loading}
              className="btn-secondary"
            >
              Next →
            </button>
          </div>
        )}

        {/* Empty state */}
        {searched && !loading && results.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">🤷</p>
            <p className="font-medium text-gray-600">No results found</p>
            <p className="text-sm mt-1">Try a different company name or number</p>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
