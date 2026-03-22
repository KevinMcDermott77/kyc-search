const FLAG_LABELS: Record<string, string> = {
  OVERDUE_ACCOUNTS: 'Accounts overdue',
  OVERDUE_CS: 'Confirmation statement overdue',
  INSOLVENCY_HISTORY: 'Insolvency history',
  FREQUENT_RESIGNATIONS: 'Frequent resignations',
  RECENT_OFFICER_CHANGES: 'Recent officer changes',
  NO_ACTIVE_PSCS: 'No active PSCs',
};

export default function RiskBadge({ flag }: { flag: string }) {
  return (
    <span className="risk-flag">
      ⚠ {FLAG_LABELS[flag] ?? flag}
    </span>
  );
}
