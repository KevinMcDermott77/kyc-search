'use client';

import { useEffect, useState } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import {
  listUsers, createUser, updateUser, listAuditLogs,
  type User, type AuditLogEntry,
} from '@/lib/api';
import Spinner from '@/components/ui/Spinner';
import ErrorBanner from '@/components/ui/ErrorBanner';
import Badge from '@/components/ui/Badge';

export default function AdminPage() {
  return (
    <AuthGuard>
      <div className="space-y-10">
        <UserManagement />
        <AuditLogTable />
      </div>
    </AuthGuard>
  );
}

function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listUsers()
      .then(setUsers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const u = await createUser({ email: newEmail, password: newPassword, is_admin: newIsAdmin });
      setUsers(prev => [u, ...prev]);
      setShowCreate(false);
      setNewEmail(''); setNewPassword(''); setNewIsAdmin(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(user: User) {
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active });
      setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Update failed');
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Users</h2>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-sm">
          + New user
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {showCreate && (
        <form onSubmit={handleCreate} className="card p-4 mb-4 space-y-3">
          <h3 className="font-medium text-gray-800">Create user</h3>
          <input value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="Email" type="email" className="input" required />
          <input value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="Password" type="password" className="input" required />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={newIsAdmin} onChange={e => setNewIsAdmin(e.target.checked)} />
            Admin user
          </label>
          <button type="submit" disabled={creating} className="btn-primary">{creating ? 'Creating…' : 'Create'}</button>
        </form>
      )}

      {loading ? <Spinner /> : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['Email', 'Role', 'Status', 'Created', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(u => (
                <tr key={u.id}>
                  <td className="px-4 py-3 text-gray-900">{u.email}</td>
                  <td className="px-4 py-3">
                    <Badge variant={u.is_admin ? 'blue' : 'gray'}>{u.is_admin ? 'Admin' : 'User'}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={u.is_active ? 'green' : 'red'}>{u.is_active ? 'Active' : 'Disabled'}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleActive(u)} className="text-xs text-brand-600 hover:underline">
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function AuditLogTable() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listAuditLogs()
      .then(setLogs)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Audit Log</h2>
      {error && <ErrorBanner message={error} />}
      {loading ? <Spinner /> : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Time', 'Action', 'Target', 'Source', 'User'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map(l => (
                  <tr key={l.id}>
                    <td className="px-4 py-2.5 text-gray-400 whitespace-nowrap text-xs">
                      {new Date(l.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant="blue">{l.action}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-gray-700 font-mono text-xs">{l.target ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant={l.source === 'companies_house' ? 'green' : 'gray'}>{l.source}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{l.user_id ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
