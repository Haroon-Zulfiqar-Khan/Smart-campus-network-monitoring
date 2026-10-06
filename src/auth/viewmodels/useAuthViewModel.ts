// @ts-nocheck
import { useState } from 'react';
import { authenticate, validateCredentials, USER_TYPES } from '../models/authModel';
import { judgeDemoAccounts } from '../models/judgeDemoAccounts';

const emptyValues = {
  fullName: '',
  email: '',
  password: '',
  confirmPassword: '',
  terms: false,
  remember: true,
};

export function useAuthViewModel(onAuthenticated) {
  const [mode, setMode] = useState('login');
  const [values, setValues] = useState(emptyValues);
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const changeMode = (next) => {
    setMode(next);
    setErrors({});
    setNotice('');
  };

  const update = (key, value) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: '' }));
    setNotice('');
  };

  const submit = async (event) => {
    event.preventDefault();
    const nextErrors = validateCredentials(values, mode);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setBusy(true);
    try {
      const result = await authenticate(values, mode);
      onAuthenticated({name:result.name,email:values.email,remember:values.remember,user:result.user});
      setValues(emptyValues);
      setNotice(
        mode === 'signup'
          ? `Account created successfully, welcome ${result.name}!`
          : `Welcome back, ${result.name}.`
      );
    } catch(error){if(import.meta.env.DEV)console.error("Authentication request failed:",error.message);setNotice(error.status===401?'The email or password is incorrect. Please try again.':error instanceof TypeError?'Unable to reach the campus server. Please try again.':typeof error.message==='string'?error.message:'Unable to sign in. Please try again.');} finally {
      setBusy(false);
    }
  };

  return {
    judgeDemoAccounts,
    fillDemoAccount: (account) => {
      if (busy) return;
      setValues((current) => ({...current, email: account.email, password: account.password}));
      setErrors({});
      setNotice(`${account.role} demo details filled. Select Sign in to continue.`);
    },
    mode,
    values,
    errors,
    showPassword,
    notice,
    busy,
    changeMode,
    update,
    togglePassword: () => setShowPassword((value) => !value),
    submit,
  };
}

