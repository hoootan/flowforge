'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2, AlertCircle, Shield } from 'lucide-react';
import { FlowForgeLogo } from '@/components/flowforge-logo';
import { useAuthStore, useHasHydrated } from '@/stores/auth-store';

export default function LoginPage() {
  const router = useRouter();
  const hasHydrated = useHasHydrated();
  const { login, verify2FA, isAuthenticated, isLoading, refreshUser, requires2FA } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!hasHydrated) return;
    refreshUser();
  }, [hasHydrated, refreshUser]);

  useEffect(() => {
    if (hasHydrated && isAuthenticated && !isLoading) router.push('/');
  }, [hasHydrated, isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const result = await login({ email, password });
    if (result.success && !result.requires2FA) router.push('/');
    else if (!result.success) setError(result.error || 'Login failed');
    setIsSubmitting(false);
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const result = await verify2FA(totpCode);
    if (result.success) router.push('/');
    else setError(result.error || 'Invalid verification code');
    setIsSubmitting(false);
  };

  if (!hasHydrated || isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Loader2 className="animate-spin" style={{ color: 'var(--ink-3)' }} />
      </div>
    );
  }
  if (isAuthenticated) return null;

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg-0)', padding: 24 }}>
      <div className="dot-grid" style={{ position: 'fixed', inset: 0, opacity: 0.5, pointerEvents: 'none' }} />
      <div style={{ width: '100%', maxWidth: 400, position: 'relative' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 44, height: 44, background: 'var(--brand)', color: 'var(--brand-ink)', borderRadius: 8, marginBottom: 12 }}>
            <FlowForgeLogo style={{ width: 24, height: 24 }} />
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, color: 'var(--ink-1)' }}>
            Welcome <em className="serif" style={{ color: 'var(--ink-2)' }}>back.</em>
          </h1>
          <p className="mono" style={{ fontSize: 11.5, color: 'var(--ink-3)', margin: '6px 0 0', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
            FlowForge · v0.8
          </p>
        </div>

        <div className="panel">
          <div className="panel-body" style={{ padding: 24 }}>
            {error && (
              <div className="tag tag-fail" style={{ width: '100%', marginBottom: 16, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertCircle size={12} /> {error}
              </div>
            )}

            {requires2FA ? (
              <form onSubmit={handleVerify2FA}>
                <div style={{ textAlign: 'center', marginBottom: 16 }}>
                  <Shield size={28} style={{ color: 'var(--brand)', marginBottom: 8 }} />
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-1)' }}>Two-factor authentication</div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 4 }}>Enter the code from your authenticator app</div>
                </div>
                <div className="field" style={{ marginBottom: 16 }}>
                  <label className="field-label" htmlFor="totp">Code</label>
                  <input
                    id="totp"
                    className="field-input mono"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="000000"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                    required
                    disabled={isSubmitting}
                    autoComplete="one-time-code"
                    autoFocus
                    style={{ textAlign: 'center', fontSize: 18, letterSpacing: '0.4em' }}
                  />
                </div>
                <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }} disabled={isSubmitting || totpCode.length < 6}>
                  {isSubmitting ? <><Loader2 className="animate-spin" size={14} /> Verifying…</> : 'Verify'}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ width: '100%', marginTop: 8 }}
                  onClick={() => {
                    useAuthStore.setState({ requires2FA: false, tempToken: null });
                    setTotpCode('');
                    setError(null);
                  }}
                >
                  Back to login
                </button>
              </form>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="field" style={{ marginBottom: 14 }}>
                  <label className="field-label" htmlFor="email">Email</label>
                  <input
                    id="email"
                    className="field-input"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isSubmitting}
                    autoComplete="email"
                    autoFocus
                  />
                </div>
                <div className="field" style={{ marginBottom: 18 }}>
                  <label className="field-label" htmlFor="password">Password</label>
                  <input
                    id="password"
                    className="field-input"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isSubmitting}
                    autoComplete="current-password"
                  />
                </div>
                <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }} disabled={isSubmitting || !email || !password}>
                  {isSubmitting ? <><Loader2 className="animate-spin" size={14} /> Signing in…</> : 'Sign in'}
                </button>
              </form>
            )}
          </div>
        </div>

        <p className="mono" style={{ textAlign: 'center', fontSize: 11, color: 'var(--ink-3)', marginTop: 16 }}>
          Need access? Contact your administrator
        </p>
        <p className="mono" style={{ textAlign: 'center', fontSize: 10, color: 'var(--ink-4)', marginTop: 4 }}>
          <Link href="/terms" style={{ color: 'var(--ink-3)' }}>Terms</Link> · <Link href="/privacy" style={{ color: 'var(--ink-3)' }}>Privacy</Link>
        </p>
      </div>
    </div>
  );
}
