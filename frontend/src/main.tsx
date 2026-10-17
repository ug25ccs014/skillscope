import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/inter';
import '@fontsource-variable/fraunces';
import App from './App';
import { ModeProvider } from './motion/ModeContext';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ModeProvider>
      <App />
    </ModeProvider>
  </React.StrictMode>,
);
