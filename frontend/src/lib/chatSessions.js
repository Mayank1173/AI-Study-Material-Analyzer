// Chat sessions persisted in localStorage so the Chat History panel can show
// the user's past chats. Sessions are scoped per account (email/user id).

const KEY_PREFIX = 'campuslearn_chat_sessions';
const MAX_SESSIONS = 50;

function keyFor(owner) {
  return `${KEY_PREFIX}:${owner || 'anonymous'}`;
}

export function listSessions(owner) {
  try {
    const raw = localStorage.getItem(keyFor(owner));
    const sessions = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(sessions)) return [];
    return [...sessions].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  } catch {
    return [];
  }
}

function persist(owner, sessions) {
  const sorted = [...sessions].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  const trimmed = sorted.slice(0, MAX_SESSIONS);
  try {
    localStorage.setItem(keyFor(owner), JSON.stringify(trimmed));
  } catch {
    // Storage full (large histories): drop the oldest and retry once.
    try {
      localStorage.setItem(keyFor(owner), JSON.stringify(trimmed.slice(0, 10)));
    } catch {
      /* ignore */
    }
  }
  return trimmed;
}

function deriveTitle(messages) {
  const firstUser = (messages || []).find((m) => m && m.role === 'user');
  const text = ((firstUser && firstUser.text) || '').trim();
  if (!text) return 'New chat';
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}

export function newSessionId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function saveSession(owner, session) {
  const messages = Array.isArray(session.messages) ? session.messages : [];
  const existing = listSessions(owner);
  const base = existing.find((s) => s.id === session.id);
  const updated = {
    id: session.id,
    createdAt: session.createdAt || (base && base.createdAt) || Date.now(),
    updatedAt: Date.now(),
    title: (base && base.title) || deriveTitle(messages),
    messages,
  };
  persist(owner, [updated, ...existing.filter((s) => s.id !== session.id)]);
  return updated;
}

export function deleteSession(owner, id) {
  persist(
    owner,
    listSessions(owner).filter((s) => s.id !== id)
  );
}
