'use client';

import { useEffect, useState } from 'react';
import { Tree, TreeNode } from 'react-organizational-chart';
import { getOwnershipTree, getFilings, type OwnershipNode, type Filing } from '@/lib/api';
import OwnershipNodeCard from './OwnershipNode';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import { formatDate } from '@/lib/format';

function renderTree(node: OwnershipNode, isRoot = false): React.ReactNode {
  const label = <OwnershipNodeCard node={node} isRoot={isRoot} />;
  if (!node.children || node.children.length === 0) {
    return <TreeNode key={node.company_number} label={label} />;
  }
  return (
    <TreeNode key={node.company_number} label={label}>
      {node.children.map(child => renderTree(child))}
    </TreeNode>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  profile: 'Company profile',
  pscs: 'Persons with significant control (PSC register)',
  filings: 'Filing history (confirmation statements)',
};

function ConfirmationStatementPanel({ companyNumber }: { companyNumber: string }) {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFilings(companyNumber)
      .then(setFilings)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [companyNumber]);

  if (loading) return null;

  const confirmationStatements = filings
    .filter(f => f.category === 'confirmation-statement')
.sort((a, b) => new Date(b.date ?? 0).getTime() - new Date(a.date ?? 0).getTime());
  const latest = confirmationStatements[0];

  if (!latest) {
    return (
      <div className="card p-4 border-l-4 border-yellow-400">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
          Confirmation Statement
        </p>
        <p className="text-sm text-yellow-600 font-medium">No confirmation statement found</p>
        <p className="text-xs text-gray-400 mt-1">
          Ownership data relies solely on PSC register. Verify manually on Companies House.
        </p>
      </div>
    );
  }

  const daysSince = Math.floor(
(new Date().getTime() - new Date(latest.date ?? 0).getTime()) / (1000 * 60 * 60 * 24)  );
  const isStale = daysSince > 365;

  return (
    <div className={`card p-4 border-l-4 ${isStale ? 'border-yellow-400' : 'border-green-400'}`}>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Ownership Corroboration - Confirmation Statement
      </p>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${isStale ? 'text-yellow-600' : 'text-green-600'}`}>
              {isStale ? 'Stale' : 'Current'}
            </span>
            <span className="text-sm text-gray-700">
              Last filed: <strong>{formatDate(latest.date)}</strong> ({daysSince} days ago)
            </span>
          </div>
          {latest.description && (
            <p className="text-xs text-gray-500">{latest.description}</p>
          )}
          {isStale && (
            <p className="text-xs text-yellow-600 mt-1">
              Confirmation statement is over 12 months old. Ownership data may not reflect current structure.
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className="text-xs text-gray-400">{confirmationStatements.length} total filed</span>
          {latest.document_url && (
            <a
              href={latest.document_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-600 hover:underline"
            >
              View document
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OwnershipChart({ companyNumber }: { companyNumber: string }) {
  const [root, setRoot] = useState<OwnershipNode | null>(null);
  const [sources, setSources] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getOwnershipTree(companyNumber)
      .then(data => { setRoot(data.root); setSources(data.ch_sources ?? {}); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyNumber]);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) return <ErrorBanner message={error} />;
  if (!root) return <p className="text-gray-500 text-sm">No ownership data available.</p>;

  const hasConnections = root.children.length > 0;

  return (
    <div className="space-y-6">
      <ConfirmationStatementPanel companyNumber={companyNumber} />

      {hasConnections ? (
        <div className="overflow-x-auto pb-4">
          <div className="flex justify-center min-w-max mx-auto">
            <Tree
              lineWidth="2px"
              lineColor="#cbd5e1"
              lineBorderRadius="6px"
              label={<OwnershipNodeCard node={root} isRoot />}
            >
              {root.children.map(child => renderTree(child))}
            </Tree>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center py-8">
          <OwnershipNodeCard node={root} isRoot />
          <p className="text-sm text-gray-400 mt-4">
            No linked corporate parents or subsidiaries found in the PSC register.
          </p>
        </div>
      )}

      {Object.keys(sources).length > 0 && (
        <div className="card p-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Data sourced from Companies House
          </p>
          <p className="text-xs text-gray-400 mb-3">
            Each node links directly to its Companies House profile and PSC register - the source of record for that layer of ownership.
          </p>
          <ul className="flex flex-wrap gap-3">
            {Object.entries(sources).map(([key, url]) => (
              <li key={key}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-600 hover:underline"
                >
                  {SOURCE_LABELS[key] ?? key}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
