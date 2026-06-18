import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Overview', 'Organizations', 'Users', 'Roles'] as const;
type Tab = typeof TABS[number];
const EDITIONS = ['professional', 'firm', 'enterprise'];
const ROLE_NAMES = ['owner', 'admin', 'manager', 'member', 'viewer', 'auditor'];

export function WorkspaceCenter() {
  const [tab, setTab] = useState<Tab>('Overview');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to manage workspaces." />;

  return (
    <Page
      title="Workspaces"
      subtitle="organizations · users · roles"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>
              {t}
            </Button>
          ))}
        </div>
      }
    >
      {tab === 'Overview' && <OverviewTab />}
      {tab === 'Organizations' && <OrganizationsTab />}
      {tab === 'Users' && <UsersTab />}
      {tab === 'Roles' && <RolesTab />}
    </Page>
  );
}

function OverviewTab() {
  const orgs = useAsync(() => helios.workspaces.listOrgs(), []);
  if (orgs.loading) return <Loading />;
  const list: any[] = orgs.data?.organizations ?? [];
  const totalSeats = list.reduce((s, o) => s + (o.max_seats || 0), 0);

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <MetricCard label="Organizations" value={list.length} />
        <MetricCard label="Total Seats" value={totalSeats} />
        <MetricCard label="Active Orgs" value={list.filter((o) => o.status === 'active').length} accent />
      </div>
      <Panel title="Organizations">
        {list.length === 0 ? (
          <EmptyState message="No organizations yet. Create one in the Organizations tab." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {list.map((o) => (
              <div key={o.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{o.name}</span>
                  <span className="mono text-[10px] uppercase text-gold">{o.edition}</span>
                </div>
                <div className="mono text-[11px] text-warmgray mt-1">
                  {o.slug} · {o.max_seats} seats · {o.status}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function OrganizationsTab() {
  const orgs = useAsync(() => helios.workspaces.listOrgs(), []);
  const [name, setName] = useState('');
  const [edition, setEdition] = useState('professional');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);

  async function create() {
    if (!name) return;
    setBusy(true);
    try {
      await helios.workspaces.createOrg({ name, edition, owner_email: email, max_seats: 5 });
      setName('');
      setEmail('');
      orgs.reload();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await helios.workspaces.deleteOrg(id);
    orgs.reload();
  }

  const list: any[] = orgs.data?.organizations ?? [];

  return (
    <div className="grid gap-3">
      <Panel title="Create Organization">
        <div className="flex flex-wrap items-end gap-2">
          <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
            placeholder="Organization name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-sm"
            value={edition} onChange={(e) => setEdition(e.target.value)}>
            {EDITIONS.map((ed) => <option key={ed} value={ed}>{ed}</option>)}
          </select>
          <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
            placeholder="Owner email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button variant="gold" size="sm" disabled={busy || !name} onClick={create}>Create</Button>
        </div>
      </Panel>
      <Panel title="Organizations">
        {orgs.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No organizations." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Name</th><th>Slug</th><th>Edition</th>
                <th>Seats</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((o) => (
                <tr key={o.id} className="border-t border-hairline">
                  <td className="py-1.5">{o.name}</td>
                  <td className="mono text-[11px] text-warmgray">{o.slug}</td>
                  <td className="text-gold">{o.edition}</td>
                  <td>{o.max_seats}</td>
                  <td>{o.status}</td>
                  <td className="text-right">
                    <Button variant="danger" size="sm" onClick={() => remove(o.id)}>Delete</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function UsersTab() {
  const orgs = useAsync(() => helios.workspaces.listOrgs(), []);
  const [orgId, setOrgId] = useState('');
  const users = useAsync(() => (orgId ? helios.workspaces.listUsers(orgId) : Promise.resolve({ users: [] })), [orgId]);
  const [email, setEmail] = useState('');
  const [uname, setUname] = useState('');
  const [role, setRole] = useState('member');

  const orgList: any[] = orgs.data?.organizations ?? [];
  const userList: any[] = users.data?.users ?? [];

  async function invite() {
    if (!orgId || !email) return;
    await helios.workspaces.inviteUser({ org_id: orgId, email, name: uname, role });
    setEmail('');
    setUname('');
    users.reload();
  }

  return (
    <div className="grid gap-3">
      <Panel title="Select Organization">
        <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-sm"
          value={orgId} onChange={(e) => setOrgId(e.target.value)}>
          <option value="">— choose organization —</option>
          {orgList.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
      </Panel>
      {orgId && (
        <>
          <Panel title="Invite User">
            <div className="flex flex-wrap items-end gap-2">
              <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
                placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
                placeholder="name" value={uname} onChange={(e) => setUname(e.target.value)} />
              <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-sm"
                value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLE_NAMES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <Button variant="gold" size="sm" onClick={invite} disabled={!email}>Invite</Button>
            </div>
          </Panel>
          <Panel title="Users">
            {users.loading ? <Loading /> : userList.length === 0 ? (
              <EmptyState message="No users in this organization." />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left mono text-[10px] uppercase text-warmgray">
                    <th className="py-1">Email</th><th>Name</th><th>Role</th>
                    <th>Status</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {userList.map((u) => (
                    <tr key={u.id} className="border-t border-hairline">
                      <td className="py-1.5">{u.email}</td>
                      <td>{u.name || '—'}</td>
                      <td>
                        <select className="border border-hairline bg-obsidian rounded px-1 py-0.5 text-xs"
                          value={u.role}
                          onChange={async (e) => { await helios.workspaces.updateUserRole(u.id, e.target.value); users.reload(); }}>
                          {ROLE_NAMES.map((r) => <option key={r} value={r}>{r}</option>)}
                        </select>
                      </td>
                      <td>{u.status}</td>
                      <td className="text-right">
                        <Button variant="danger" size="sm"
                          onClick={async () => { await helios.workspaces.removeUser(u.id); users.reload(); }}>
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}

function RolesTab() {
  const roles = useAsync(() => helios.workspaces.getRoles(), []);
  if (roles.loading) return <Loading />;
  const list: any[] = roles.data?.roles ?? [];
  return (
    <Panel title="Predefined Roles">
      <div className="grid gap-2">
        {list.map((r) => (
          <div key={r.name} className="rounded-lg border border-hairline px-3 py-2">
            <div className="flex items-center justify-between">
              <span className="text-sm capitalize">{r.name}</span>
              <span className="mono text-[10px] text-warmgray">{r.permissions.length} permissions</span>
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {r.permissions.map((p: string) => (
                <span key={p} className={cls('mono text-[10px] px-1.5 py-0.5 rounded border border-hairline text-warmgray')}>
                  {p}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
