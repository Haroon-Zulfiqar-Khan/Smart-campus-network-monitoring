// @ts-nocheck
import { useState } from 'react';
import { ArrowRight, ChevronDown, Check, GraduationCap, Headset, ChartNoAxesCombined, Eye, EyeOff, LockKeyhole, Mail, Radio, ShieldCheck, UserRound, Wifi, Zap } from 'lucide-react';

function Brand(){return <img className="auth-logo" src="/branding/campusnet-logo.png" alt="CampusNet — campus network monitoring"/>;}

function Field({ label, icon: Icon, error, trailing, ...props }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className={`input-wrap ${error ? 'input-error' : ''}`}>
        <Icon size={18} aria-hidden="true" />
        <input {...props} />
        {trailing}
      </span>
      {error && <span className="error-text">{error}</span>}
    </label>
  );
}

export default function AuthScreen(vm) {
  const signup = vm.mode === 'signup';
  const [demoOpen, setDemoOpen] = useState(false);
  const [demoRole, setDemoRole] = useState('Student');
  const selectedDemo = vm.judgeDemoAccounts.find(account => account.role === demoRole);
  const demoIcons = {Student: GraduationCap, Administrator: ShieldCheck, 'IT Staff': Headset, Manager: ChartNoAxesCombined};
  const demoDescriptions = {Student: 'Test and report', Administrator: 'Manage the campus', 'IT Staff': 'Investigate issues', Manager: 'Review insights'};
  const [forgot, setForgot] = useState(false);
  const [resetSent, setResetSent] = useState(false);const [resetError,setResetError]=useState('');

  return (
    <main className="auth-page">
      <section className="visual-panel" aria-label="CampusNet network overview">
        <div className="visual-image" />
        <div className="visual-shade" />
        <div className="hero-copy">
          <h1>
            Your campus.<br />Connected <em>better.</em>
          </h1>
          <p>One place to monitor Wi-Fi health, find reliable connections, and keep your campus moving.</p>
          <div className="hero-actions">
            <span><Radio size={16} /> Campus network insights</span>
            <span><ShieldCheck size={16} /> Built for your campus</span>
          </div>
        </div>
        <div className="visual-footer">
          <span>SMARTER CONNECTIONS START HERE</span>
          <span>01 — 03</span>
        </div>
      </section>

      <section className="form-panel">
        <div className="form-top">
          <span className="mobile-brand"><Brand /></span>
          <span className="top-prompt">
            {signup ? 'Already a member?' : 'New to CampusNet?'}
            <button className="text-link" onClick={() => vm.changeMode(signup ? 'login' : 'signup')}>
              {signup ? 'Sign in' : 'Create account'}
            </button>
          </span>
        </div>

        <div className="auth-card">
          <div className="card-brand"><Brand /></div>
          <div className="card-heading">
            <span className="step-label">{forgot ? 'ACCOUNT RECOVERY' : signup ? 'GET STARTED' : 'WELCOME BACK'}</span>
            <h2>{forgot ? 'Reset your password' : signup ? 'Create your account' : 'Sign in to your account'}</h2>
            <p>
              {forgot
                ? 'Enter your university email to check password recovery availability.'
                : signup
                ? 'Join your campus network in just a few steps.'
                : 'Your campus network is just a sign-in away.'}
            </p>
          </div>

          {forgot ? (
            <form
              className="auth-form"
              onSubmit={(e) => {
                e.preventDefault();
                vm.update('email', vm.values.email);
              }}
            >
              <Field
                label="University email"
                icon={Mail}
                type="email"
                placeholder="you@muet.edu.pk"
                value={vm.values.email}
                onChange={(e) => {
                  vm.update('email', e.target.value);
                  setResetSent(false);
                }}
                autoComplete="email"
              />
              <button
                className="primary-button"
                type="button"
                onClick={() => {const valid=/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(vm.values.email);setResetSent(valid);setResetError(valid?'':'Enter a valid university email.');}}
              >
                Send reset link <ArrowRight size={15} />
              </button>
              {resetError&&<p className="error-text" role="alert">{resetError}</p>}{resetSent && (
                <div className="notice" role="status">
                  Password recovery is not connected yet. Contact your campus IT team for assistance.
                </div>
              )}
              <button
                className="back-link"
                type="button"
                onClick={() => {
                  setForgot(false);
                  setResetSent(false);
                }}
              >
                Back to sign in
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={vm.submit} noValidate>
              {signup && (
                <Field
                  label="Full name"
                  icon={UserRound}
                  error={vm.errors.fullName}
                  type="text"
                  placeholder="Enter your full name"
                  value={vm.values.fullName}
                  onChange={(e) => vm.update('fullName', e.target.value)}
                  autoComplete="name"
                />
              )}
              <Field
                label="University email"
                icon={Mail}
                error={vm.errors.email}
                type="email"
                placeholder="you@muet.edu.pk"
                value={vm.values.email}
                onChange={(e) => vm.update('email', e.target.value)}
                autoComplete="email"
              />
              <Field
                label="Password"
                icon={LockKeyhole}
                error={vm.errors.password}
                type={vm.showPassword ? 'text' : 'password'}
                placeholder={signup ? 'Create a password (8+ characters)' : 'Enter your password'}
                value={vm.values.password}
                onChange={(e) => vm.update('password', e.target.value)}
                autoComplete={signup ? 'new-password' : 'current-password'}
                trailing={
                  <button
                    type="button"
                    className="visibility-button"
                    aria-label={vm.showPassword ? 'Hide password' : 'Show password'}
                    onClick={vm.togglePassword}
                  >
                    {vm.showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                }
              />
              {signup && (
                <>
                  <Field
                    label="Confirm password"
                    icon={LockKeyhole}
                    error={vm.errors.confirmPassword}
                    type={vm.showPassword ? 'text' : 'password'}
                    placeholder="Re-enter your password"
                    value={vm.values.confirmPassword}
                    onChange={(e) => vm.update('confirmPassword', e.target.value)}
                    autoComplete="new-password"
                  />

                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={vm.values.terms}
                      onChange={(e) => vm.update('terms', e.target.checked)}
                    />
                    <span>
                      I agree to the <a href="#terms">Terms of Service</a> and <a href="#privacy">Privacy Policy</a>.
                    </span>
                  </label>
                  {vm.errors.terms && <span className="error-text terms-error">{vm.errors.terms}</span>}
                </>
              )}
              {!signup && (
                <div className="form-options">
                  <label className="check-row remember">
                    <input
                      type="checkbox"
                      checked={vm.values.remember}
                      onChange={(e) => vm.update('remember', e.target.checked)}
                    />
                    <span>Remember me</span>
                  </label>
                  <button type="button" className="text-link forgot-link" onClick={() => setForgot(true)}>
                    Forgot password?
                  </button>
                </div>
              )}
              <button className="primary-button" type="submit" disabled={vm.busy}>
                {vm.busy ? 'Please wait…' : signup ? 'Create account' : 'Sign in'} <ArrowRight size={17} />
              </button>
              {vm.notice && <div className="notice" role="status">{vm.notice}</div>}
            </form>
          )}

          {!forgot && !signup && (
            <section className={`judge-demo ${demoOpen ? 'is-open' : ''}`} aria-labelledby="judge-demo-title">
              <button type="button" className="judge-demo-toggle" aria-expanded={demoOpen}
                aria-controls="judge-demo-options" onClick={() => setDemoOpen(open => !open)}>
                <span className="judge-demo-emblem"><ShieldCheck size={19} aria-hidden="true" /></span>
                <span className="judge-demo-intro"><span id="judge-demo-title">Explore the demo <span className="judge-demo-tag">FOR JUDGES</span></span><span>Four roles. One connected campus.</span></span>
                <ChevronDown className="judge-demo-chevron" size={17} aria-hidden="true" />
              </button>
              {demoOpen && <div id="judge-demo-options" className="judge-demo-options">
                <p className="judge-demo-hint">Select a role to fill your sign-in details.</p>
                <div className="judge-demo-roles" role="group" aria-label="Choose a demo role">
                  {vm.judgeDemoAccounts.map(account => {
                    const Icon = demoIcons[account.role];
                    const selected = account.role === demoRole;
                    return <button key={account.role} type="button" className={`judge-role ${selected ? 'is-selected' : ''}`}
                      aria-pressed={selected} disabled={vm.busy}
                      onClick={() => {setDemoRole(account.role); vm.fillDemoAccount(account);}}>
                      <Icon size={18} aria-hidden="true" />
                      <span><strong>{account.role}</strong><small>{demoDescriptions[account.role]}</small></span>
                      <span className="judge-role-check">{selected && <Check size={11} aria-hidden="true" />}</span>
                    </button>;
                  })}
                </div>
                <div className="judge-demo-preview" aria-live="polite" aria-atomic="true">
                  <div><span>Email</span><code>{selectedDemo.email}</code></div>
                  <div><span>Password</span><code>{selectedDemo.password}</code></div>
                </div>
                <p className="judge-demo-caption">Use the Sign in button above to enter the selected workspace.</p>
              </div>}
            </section>
          )}

          {!forgot && (
            <div className="card-bottom">
              <span>{signup ? 'Already have an account?' : 'Don’t have an account?'}</span>
              <button className="text-link" onClick={() => vm.changeMode(signup ? 'login' : 'signup')}>
                {signup ? 'Sign in' : 'Create account'}
              </button>
            </div>
          )}
        </div>

        <div className="form-footer">
          <span>© 2026 CampusNet</span>
          <span><Zap size={14} /> Reliable Wi-Fi starts here</span>
        </div>
      </section>
    </main>
  );
}

