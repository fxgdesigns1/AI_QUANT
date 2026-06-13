/**
 * Main entry point - Uses App.jsx for routing
 * Routes:
 * - /vm -> VMTradeJournal
 * - / -> Dashboard (default)
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
