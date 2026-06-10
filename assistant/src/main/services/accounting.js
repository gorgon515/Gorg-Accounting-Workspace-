'use strict';

// Accounting pillar — a practical small-business ledger for the workspace.
// Fully local (persisted JSON), no key. Covers:
//   • Transactions  — income/expense ledger with categories and accounts
//   • Invoices       — issue, track, mark paid (accounts receivable)
//   • Reports        — P&L by category, net, cash position, outstanding AR
//
// Informational bookkeeping only — not tax or financial advice.

const store = require('../store');

const DEFAULT_CATEGORIES = {
  income: ['Sales', 'Services', 'Consulting', 'Interest', 'Other income'],
  expense: ['Software', 'Payroll', 'Rent', 'Utilities', 'Travel', 'Marketing', 'Fees', 'Supplies', 'Taxes', 'Other'],
};

const ledger = () => store.get('ledger', []);
const saveLedger = (l) => store.set('ledger', l);
const invoices = () => store.get('invoices', []);
const saveInvoices = (i) => store.set('invoices', i);

const newId = (p) => p + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const today = () => new Date().toISOString().slice(0, 10);

function parseDate(d) {
  if (!d) return today();
  const s = String(d).trim().toLowerCase();
  if (s === 'today') return today();
  const parsed = new Date(s);
  return Number.isNaN(parsed.getTime()) ? today() : parsed.toISOString().slice(0, 10);
}

function money(n) {
  return Math.round(Number(n) * 100) / 100;
}

// ---------- transactions ----------
function addTransaction({ type, amount, category, description, date, account }) {
  type = String(type || '').toLowerCase();
  if (!['income', 'expense'].includes(type)) throw new Error('type must be "income" or "expense"');
  amount = money(amount);
  if (!Number.isFinite(amount) || amount <= 0) throw new Error('amount must be a positive number');
  const t = {
    id: newId('txn'),
    date: parseDate(date),
    type,
    amount,
    category: (category && String(category).trim()) || (type === 'income' ? 'Other income' : 'Other'),
    description: (description && String(description).trim()) || '',
    account: (account && String(account).trim()) || 'bank',
    createdAt: new Date().toISOString(),
  };
  const l = ledger();
  l.push(t);
  saveLedger(l);
  return t;
}

function listTransactions({ from, to, type, category, limit } = {}) {
  let rows = ledger();
  if (from) rows = rows.filter((t) => t.date >= from);
  if (to) rows = rows.filter((t) => t.date <= to);
  if (type) rows = rows.filter((t) => t.type === String(type).toLowerCase());
  if (category) rows = rows.filter((t) => t.category.toLowerCase() === String(category).toLowerCase());
  rows = rows.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  return limit ? rows.slice(0, limit) : rows;
}

function deleteTransaction({ id }) {
  saveLedger(ledger().filter((t) => t.id !== id));
  return { deleted: id };
}

function categories() {
  const used = { income: new Set(DEFAULT_CATEGORIES.income), expense: new Set(DEFAULT_CATEGORIES.expense) };
  ledger().forEach((t) => used[t.type] && used[t.type].add(t.category));
  return { income: [...used.income], expense: [...used.expense] };
}

// ---------- invoices ----------
function nextInvoiceNumber() {
  const n = invoices().length + 1;
  return 'INV-' + String(n).padStart(4, '0');
}

function addInvoice({ client, amount, due, issued, number, notes }) {
  if (!client || !String(client).trim()) throw new Error('client is required');
  amount = money(amount);
  if (!Number.isFinite(amount) || amount <= 0) throw new Error('amount must be a positive number');
  const inv = {
    id: newId('inv'),
    number: (number && String(number).trim()) || nextInvoiceNumber(),
    client: String(client).trim(),
    amount,
    issued: parseDate(issued),
    due: due ? parseDate(due) : null,
    status: 'sent',
    notes: (notes && String(notes).trim()) || '',
    createdAt: new Date().toISOString(),
    paidAt: null,
  };
  const list = invoices();
  list.push(inv);
  saveInvoices(list);
  return inv;
}

function listInvoices({ status } = {}) {
  let list = invoices();
  if (status) list = list.filter((i) => i.status === String(status).toLowerCase());
  return list.sort((a, b) => (a.issued < b.issued ? 1 : -1));
}

function findInvoice(list, idOrNumber) {
  const key = String(idOrNumber || '').trim().toLowerCase();
  return list.find((i) => i.id === idOrNumber) || list.find((i) => i.number.toLowerCase() === key) || null;
}

function updateInvoiceStatus({ id, number, status }) {
  status = String(status || '').toLowerCase();
  if (!['draft', 'sent', 'paid'].includes(status)) throw new Error('status must be draft, sent, or paid');
  const list = invoices();
  const inv = findInvoice(list, id || number);
  if (!inv) throw new Error('No matching invoice found.');
  inv.status = status;
  inv.paidAt = status === 'paid' ? today() : null;
  saveInvoices(list);
  return inv;
}

function markInvoicePaid({ id, number }) {
  return updateInvoiceStatus({ id, number, status: 'paid' });
}

function deleteInvoice({ id, number }) {
  const list = invoices();
  const inv = findInvoice(list, id || number);
  if (!inv) throw new Error('No matching invoice found.');
  saveInvoices(list.filter((i) => i.id !== inv.id));
  return { deleted: inv.id };
}

// ---------- reports ----------
function summary({ from, to } = {}) {
  const rows = listTransactions({ from, to });
  const byCategory = { income: {}, expense: {} };
  let income = 0;
  let expense = 0;
  rows.forEach((t) => {
    if (t.type === 'income') income += t.amount;
    else expense += t.amount;
    byCategory[t.type][t.category] = money((byCategory[t.type][t.category] || 0) + t.amount);
  });

  // Cash position from all-time ledger (income - expense), independent of filter.
  const all = ledger();
  const cash = money(
    all.reduce((s, t) => s + (t.type === 'income' ? t.amount : -t.amount), 0)
  );

  const open = invoices().filter((i) => i.status !== 'paid');
  const todayStr = today();
  const outstanding = money(open.reduce((s, i) => s + i.amount, 0));
  const overdue = money(open.filter((i) => i.due && i.due < todayStr).reduce((s, i) => s + i.amount, 0));

  return {
    period: { from: from || null, to: to || null },
    income: money(income),
    expense: money(expense),
    net: money(income - expense),
    byCategory,
    cashPosition: cash,
    accountsReceivable: { outstanding, overdue, openCount: open.length },
    note: 'Local bookkeeping only — not tax or financial advice.',
  };
}

const tools = [
  {
    name: 'record_transaction',
    description:
      'Record an income or expense in the books. Call when the user says they earned, received, paid, spent, or bought something. Include amount and a category/description when known.',
    input_schema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['income', 'expense'] },
        amount: { type: 'number' },
        category: { type: 'string', description: 'e.g. Sales, Software, Rent' },
        description: { type: 'string' },
        date: { type: 'string', description: 'YYYY-MM-DD or "today"' },
      },
      required: ['type', 'amount'],
    },
  },
  {
    name: 'list_transactions',
    description: 'List ledger entries, optionally filtered by date range, type, or category.',
    input_schema: {
      type: 'object',
      properties: {
        from: { type: 'string', description: 'YYYY-MM-DD' },
        to: { type: 'string', description: 'YYYY-MM-DD' },
        type: { type: 'string', enum: ['income', 'expense'] },
        category: { type: 'string' },
        limit: { type: 'number' },
      },
    },
  },
  {
    name: 'create_invoice',
    description: 'Create an invoice for a client. Call when the user wants to bill or invoice someone.',
    input_schema: {
      type: 'object',
      properties: {
        client: { type: 'string' },
        amount: { type: 'number' },
        due: { type: 'string', description: 'Due date YYYY-MM-DD' },
        notes: { type: 'string' },
      },
      required: ['client', 'amount'],
    },
  },
  {
    name: 'list_invoices',
    description: 'List invoices, optionally filtered by status (draft, sent, paid).',
    input_schema: {
      type: 'object',
      properties: { status: { type: 'string', enum: ['draft', 'sent', 'paid'] } },
    },
  },
  {
    name: 'mark_invoice_paid',
    description: 'Mark an invoice as paid, by invoice number (e.g. INV-0001) or id.',
    input_schema: {
      type: 'object',
      properties: { number: { type: 'string' }, id: { type: 'string' } },
    },
  },
  {
    name: 'financial_summary',
    description:
      'Get a books summary: income, expenses, net profit, breakdown by category, cash position, and accounts receivable (outstanding/overdue invoices). Call for "how are the books", P&L, profit, or financial-summary requests. Optional date range.',
    input_schema: {
      type: 'object',
      properties: { from: { type: 'string' }, to: { type: 'string' } },
    },
  },
];

const handlers = {
  record_transaction: (i) => addTransaction(i),
  list_transactions: async (i) => listTransactions(i),
  create_invoice: (i) => addInvoice(i),
  list_invoices: async (i) => listInvoices(i),
  mark_invoice_paid: (i) => markInvoicePaid(i),
  financial_summary: async (i) => summary(i),
};

module.exports = {
  name: 'accounting',
  systemPromptFragment:
    'You keep the user\'s books: record income/expenses, create and track invoices, and report a P&L summary (income, expenses, net, by-category, cash position, accounts receivable). All figures come from the local ledger. When recording, confirm amount, type, and category. This is bookkeeping support, not tax or financial advice — say so if asked for tax/financial guidance.',
  tools,
  handlers,
  api: {
    addTransaction, listTransactions, deleteTransaction, categories,
    addInvoice, listInvoices, updateInvoiceStatus, markInvoicePaid, deleteInvoice,
    summary,
  },
};
