import { useState, useEffect } from 'react';
import Icon from '@/components/ui/icon';

const AUTH_URL = 'https://functions.poehali.dev/53927877-ae82-4bf1-af0d-755d69528b51';

interface UserProfile {
  uid: string;
  login: string;
  registered_at: string;
  last_login_at: string | null;
  token: string;
}

async function callAuth(action: string, payload: object = {}, token?: string) {
  const res = await fetch(AUTH_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-Session-Token': token } : {}),
    },
    body: JSON.stringify({ action, ...payload }),
  });
  return res.json();
}

function formatDate(iso: string | null) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

export default function App() {
  const [page, setPage] = useState<'auth' | 'cabinet'>('auth');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem('denov_token');
    if (savedToken) {
      callAuth('profile', {}, savedToken).then(data => {
        if (data.uid) {
          setUser({ ...data, token: savedToken });
          setPage('cabinet');
        } else {
          localStorage.removeItem('denov_token');
        }
      });
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const data = await callAuth(mode, { login, password });
    setLoading(false);
    if (data.error) {
      setError(data.error);
    } else {
      localStorage.setItem('denov_token', data.token);
      setUser(data);
      setPage('cabinet');
    }
  };

  const handleLogout = async () => {
    if (user?.token) {
      await callAuth('logout', {}, user.token);
      localStorage.removeItem('denov_token');
    }
    setUser(null);
    setPage('auth');
    setLogin('');
    setPassword('');
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--dark-bg)' }}>
      {/* NAVBAR */}
      <header style={{ borderBottom: '1px solid var(--border-crimson)', background: 'rgba(13,13,13,0.95)', backdropFilter: 'blur(8px)' }} className="sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #8B0000, #C0152A)', boxShadow: '0 0 12px rgba(192,21,42,0.5)' }}>
              <Icon name="Zap" size={16} className="text-white" />
            </div>
            <span className="text-xl font-semibold tracking-widest text-white" style={{ fontFamily: 'Oswald, sans-serif', letterSpacing: '0.12em' }}>
              DENO<span style={{ color: 'var(--crimson-bright)' }}>V</span>
            </span>
          </div>

          <nav className="flex items-center gap-1">
            <a href="https://denovclient2.tilda.ws/" target="_blank" rel="noopener noreferrer"
              className="nav-btn px-4 py-1.5 text-sm font-medium tracking-wide" style={{ fontFamily: 'Rubik, sans-serif' }}>
              НОВОСТИ
            </a>
            <a href="https://denovclient2.tilda.ws/download" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium btn-crimson rounded ml-1">
              <Icon name="Download" size={14} />
              СКАЧАТЬ
            </a>
            <a href="https://t.me/DenoVClient" target="_blank" rel="noopener noreferrer"
              className="nav-btn flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium ml-1">
              <Icon name="Send" size={14} fallback="MessageCircle" />
              TG
            </a>
          </nav>
        </div>
      </header>

      {/* MAIN */}
      <main className="flex-1 flex items-center justify-center px-4 py-16">

        {page === 'auth' && (
          <div className="w-full max-w-md animate-fade-in">
            <div className="h-0.5 w-16 mb-8 mx-auto rounded" style={{ background: 'linear-gradient(90deg, var(--crimson), var(--crimson-bright))' }} />

            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold tracking-widest mb-2" style={{ fontFamily: 'Oswald, sans-serif', color: 'var(--text-primary)' }}>
                {mode === 'login' ? 'ВХОД' : 'РЕГИСТРАЦИЯ'}
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {mode === 'login' ? 'Войдите в аккаунт DenoV Client' : 'Создайте аккаунт DenoV Client'}
              </p>
            </div>

            <div className="denov-card rounded-lg p-8 animate-glow">
              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                <div>
                  <label className="block text-xs font-medium tracking-widest mb-2" style={{ color: 'var(--text-muted)', fontFamily: 'Oswald, sans-serif' }}>
                    ЛОГИН
                  </label>
                  <input
                    type="text"
                    value={login}
                    onChange={e => setLogin(e.target.value)}
                    placeholder="Введите логин"
                    className="denov-input w-full px-4 py-3 rounded text-sm"
                    autoComplete="username"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium tracking-widest mb-2" style={{ color: 'var(--text-muted)', fontFamily: 'Oswald, sans-serif' }}>
                    ПАРОЛЬ
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Введите пароль"
                    className="denov-input w-full px-4 py-3 rounded text-sm"
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    required
                  />
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-sm px-3 py-2 rounded" style={{ background: 'rgba(139,0,0,0.2)', border: '1px solid rgba(192,21,42,0.4)', color: '#ff6b6b' }}>
                    <Icon name="AlertCircle" size={14} />
                    {error}
                  </div>
                )}

                <button type="submit" disabled={loading}
                  className="btn-crimson w-full py-3 rounded text-sm font-semibold tracking-widest mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ fontFamily: 'Oswald, sans-serif' }}>
                  {loading ? 'ЗАГРУЗКА...' : mode === 'login' ? 'ВОЙТИ' : 'СОЗДАТЬ АККАУНТ'}
                </button>
              </form>

              <div className="divider-crimson my-6" />

              <p className="text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                {mode === 'login' ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}{' '}
                <button
                  onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
                  className="font-medium transition-colors"
                  style={{ color: 'var(--crimson-bright)' }}
                  onMouseEnter={e => (e.currentTarget.style.color = '#ff4455')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--crimson-bright)')}>
                  {mode === 'login' ? 'Зарегистрироваться' : 'Войти'}
                </button>
              </p>
            </div>
          </div>
        )}

        {page === 'cabinet' && user && (
          <div className="w-full max-w-xl animate-fade-in">
            <div className="h-0.5 w-16 mb-8 mx-auto rounded" style={{ background: 'linear-gradient(90deg, var(--crimson), var(--crimson-bright))' }} />

            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold tracking-widest mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
                ЛИЧНЫЙ КАБИНЕТ
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Добро пожаловать, <span style={{ color: 'var(--crimson-bright)' }}>{user.login}</span>
              </p>
            </div>

            <div className="denov-card rounded-lg overflow-hidden">
              {/* Шапка профиля */}
              <div className="px-8 py-6 flex items-center gap-4" style={{ background: 'linear-gradient(135deg, rgba(139,0,0,0.2) 0%, rgba(26,16,16,0.5) 100%)', borderBottom: '1px solid var(--border-crimson)' }}>
                <div className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold flex-shrink-0" style={{ background: 'linear-gradient(135deg, #8B0000, #C0152A)', color: '#fff', fontFamily: 'Oswald, sans-serif', boxShadow: '0 0 20px rgba(192,21,42,0.5)' }}>
                  {user.login[0].toUpperCase()}
                </div>
                <div>
                  <div className="text-xl font-semibold tracking-wider" style={{ fontFamily: 'Oswald, sans-serif' }}>{user.login}</div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>DenoV Client</div>
                </div>
              </div>

              {/* Данные */}
              <div className="px-8 py-6 flex flex-col gap-5">
                {([
                  { label: 'UID', value: user.uid, icon: 'Fingerprint', badge: true },
                  { label: 'ЛОГИН', value: user.login, icon: 'User', badge: false },
                  { label: 'ПОСЛЕДНИЙ ВХОД', value: formatDate(user.last_login_at), icon: 'Clock', badge: false },
                  { label: 'ДАТА РЕГИСТРАЦИИ', value: formatDate(user.registered_at), icon: 'CalendarDays', badge: false },
                ] as const).map(({ label, value, icon, badge }) => (
                  <div key={label} className="flex items-start gap-4">
                    <div className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: 'rgba(139,0,0,0.15)', border: '1px solid rgba(139,0,0,0.25)' }}>
                      <Icon name={icon} size={15} fallback="Info" style={{ color: 'var(--crimson-bright)' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs tracking-widest mb-1" style={{ color: 'var(--text-muted)', fontFamily: 'Oswald, sans-serif' }}>{label}</div>
                      {badge ? (
                        <span className="uid-badge px-2 py-1 rounded inline-block max-w-full text-xs" style={{ wordBreak: 'break-all' }}>{value}</span>
                      ) : (
                        <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{value}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="divider-crimson" />

              <div className="px-8 py-5">
                <button onClick={handleLogout}
                  className="flex items-center gap-2 text-sm px-4 py-2 rounded transition-all"
                  style={{ color: 'var(--text-muted)', border: '1px solid rgba(139,0,0,0.25)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#ff6b6b'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(192,21,42,0.5)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(139,0,0,0.25)'; }}>
                  <Icon name="LogOut" size={14} />
                  Выйти из аккаунта
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* FOOTER */}
      <footer className="py-6 text-center" style={{ borderTop: '1px solid var(--border-crimson)' }}>
        <p className="text-xs tracking-widest" style={{ color: 'var(--text-muted)', fontFamily: 'Oswald, sans-serif' }}>
          © 2024 DENO<span style={{ color: 'var(--crimson-bright)' }}>V</span> CLIENT
        </p>
      </footer>
    </div>
  );
}
