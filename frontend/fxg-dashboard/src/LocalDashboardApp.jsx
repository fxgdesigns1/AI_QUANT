/**
 * Local Dashboard App - Entry point for local-only OANDA trade dashboard
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import LocalTradeDashboard from './components/LocalTradeDashboard';
import './LocalDashboard.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LocalTradeDashboard />
  </StrictMode>
);
