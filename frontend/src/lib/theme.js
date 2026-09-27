// Tiny global theme helper: persists the choice, applies the `dark` class on
// <html> (Tailwind dark variant) and keeps "system" in sync with the OS.

const THEME_KEY = 'campuslearn_theme';
const THEME_EVENT = 'campuslearn-theme';
const VALID = ['light', 'dark', 'system'];

function systemPrefersDark() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );
}

export function resolveTheme(theme) {
  if (theme === 'dark') return 'dark';
  if (theme === 'system') return systemPrefersDark() ? 'dark' : 'light';
  return 'light';
}

export function applyTheme(theme) {
  if (typeof document === 'undefined') return;
  const resolved = resolveTheme(theme);
  const root = document.documentElement;
  root.classList.toggle('dark', resolved === 'dark');
  root.style.colorScheme = resolved;
}

export function getTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  return VALID.includes(saved) ? saved : 'light';
}

export function setTheme(theme) {
  const next = VALID.includes(theme) ? theme : 'light';
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
  window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: { theme: next } }));
}

// Called once at app start: applies the saved theme and keeps "system"
// tracking the OS preference while the app is open.
export function initTheme() {
  const saved = getTheme();
  applyTheme(saved);

  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      if (getTheme() === 'system') applyTheme('system');
    };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
}
