'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AuthGuard from '@/components/layout/AuthGuard';
import { getCase, updateCase, addCaseNote, type CaseDetail } from '@/lib/api';
import { formatDate } from '@/lib/format';
import {
  RiskScoreCard,
  SanctionsSection,
  PepSection,
  CountryRiskSection,
  SectorRiskSection,
  AdverseMediaSection,
} from '@/components/company/tabs/ScreeningTab';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import clsx from 'clsx';

type CaseStatus = 'pending' | 'approved' | 'flagged' | 'closed';

const STATUSES: { id: CaseStatus; label: string; style: string }[] = [
  { id: 'pending',  label: 'Pending',  style: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  { id: 'approved', label: 'Approved', style: 'bg-green-100 text-green-800 border-green-200' },
  { id: 'flagged',  label: 'Flagged',  style: 'bg-red-100 text-red-800 border-red-200' },
  { id: 'closed',   label: 'Closed',   style: 'bg-gray-100 text-gray-600 border-gray-200' },
];

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [addingNote, setAddingNote] = useState(false);

  useEffect(() => {
    getCase(Number(id))
      .then(setCaseData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleStatusChange(status: CaseStatus) {
    if (!caseData || caseData.status === status) return;
    setStatusUpdating(true);
    try {
      const updated = await updateCase(Number(id), { status });
      setCaseData(updated);
    } catch {
      // ignore
    } finally {
      setStatusUpdating(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      const note = await addCaseNote(Number(id), noteText.trim());
      setCaseData(prev => prev ? { ...prev, notes: [...prev.notes, note] } : prev);
      setNoteText('');
    } catch {
      // ignore
    } finally {
      setAddingNote(false);
    }
  }

  return (
    <AuthGuard>
      {loading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
      {error && <ErrorBanner message={error} />}
      {caseData && (
        <div className="space-y-6 max-w-5xl mx-auto">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Case #{caseData.id}</p>
              <h1 className="text-xl font-bold text-gray-900">{caseData.company_name}</h1>
              <p className="text-sm text-gray-400 font-mono mt-0.5">{caseData.company_number}</p>
            </div>
            <a
              href={`/company/${caseData.company_number}`}
              className="text-sm text-brand-600 hover:underline whitespace-nowrap"
            >
              View company →
            </a>
          </div>

          {/* Status selector */}
          <div className="card p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Case Status</p>
            <div className="flex flex-wrap gap-2">
              {STATUSES.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleStatusChange(s.id)}
                  disabled={statusUpdating}
                  className={clsx(
                    'px-4 py-1.5 rounded-full text-sm font-semibold border transition-all',
                    caseData.status === s.id
                      ? s.style + ' ring-2 ring-offset-1 ring-brand-400'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
                  )}
                >
                  {s.label}
                </button>
              ))}
              {statusUpdating && <Spinner />}
            </div>
            <div className="mt-3 text-xs text-gray-400 flex gap-4">
              {caseData.created_by_email && <span>Created by: {caseData.created_by_email}</span>}
              {caseData.created_at && <span>Created: {formatDate(caseData.created_at.slice(0, 10))}</span>}
              {caseData.updated_at && <span>Updated: {formatDate(caseData.updated_at.slice(0, 10))}</span>}
            </div>
          </div>

          {/* Screening snapshot */}
          {caseData.screening_snapshot ? (
            <div className="space-y-4">
              <RiskScoreCard result={caseData.screening_snapshot} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <SanctionsSection
                  data={caseData.screening_snapshot.sanctions}
                  source={caseData.screening_snapshot.sanctions_api_source}
                />
                <PepSection
                  data={caseData.screening_snapshot.pep_indicators}
                  source={caseData.screening_snapshot.pep_source}
                />
                <CountryRiskSection
                  data={caseData.screening_snapshot.country_risks}
                  source={caseData.screening_snapshot.country_source}
                />
                <SectorRiskSection
                  data={caseData.screening_snapshot.sector_risks}
                  source={caseData.screening_snapshot.sector_source}
                />
              </div>
              <AdverseMediaSection
                companyName={caseData.company_name}
                data={caseData.screening_snapshot.adverse_media}
              />
            </div>
          ) : (
            <div className="card p-6 text-center text-gray-400">
              <p>No screening snapshot saved for this case.</p>
            </div>
          )}

          {/* Notes */}
          <div className="card p-5">
            <h2 className="font-semibold text-gray-800 mb-4">Notes</h2>

            {caseData.notes.length === 0 ? (
              <p className="text-sm text-gray-400 mb-4">No notes yet.</p>
            ) : (
              <div className="space-y-3 mb-4">
                {caseData.notes.map(note => (
                  <div key={note.id} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <p className="text-sm text-gray-800 whitespace-pre-wrap">{note.text}</p>
                    <p className="text-xs text-gray-400 mt-2">
                      {note.user_email ?? 'Unknown'} &nbsp;·&nbsp;{' '}
                      {note.created_at ? formatDate(note.created_at.slice(0, 10)) : ''}
                    </p>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleAddNote} className="flex gap-2">
              <textarea
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Add a note…"
                rows={2}
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
              <button
                type="submit"
                disabled={addingNote || !noteText.trim()}
                className="btn-primary px-4 py-2 text-sm self-end disabled:opacity-50"
              >
                {addingNote ? '…' : 'Add Note'}
              </button>
            </form>
          </div>
        </div>
      )}
    </AuthGuard>
  );
}
