import React from 'react';
import {createRoot} from 'react-dom/client';
import {App} from './App';
import '../app/auth.css';
import '../app/globals.css';
import '../app/campus.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);

