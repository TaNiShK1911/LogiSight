import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Companies } from './pages/SuperAdmin/Companies';
import { QuoteForm } from './pages/QuoteForm';
import { Quotes } from './pages/Quotes';
import { QuoteDetail } from './pages/QuoteDetail';
import { Invoices } from './pages/Invoices';
import { InvoiceAnalysis } from './pages/InvoiceAnalysis';
import { ChargeMaster } from './pages/ChargeMaster';
import { Tracking } from './pages/Tracking';
import { Copilot } from './pages/Copilot';

export const router = createBrowserRouter([
  { path: '/', element: <Landing /> },
  { path: '/login', element: <Login /> },
  {
    path: '/app',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Dashboard /> },
      {
        path: 'companies',
        element: (
          <ProtectedRoute allowedRoles={['super_admin']}>
            <Companies />
          </ProtectedRoute>
        ),
      },
      {
        path: 'quotes',
        element: (
          <ProtectedRoute allowedRoles={['client', 'forwarder']}>
            <Quotes />
          </ProtectedRoute>
        ),
      },
      {
        path: 'quotes/new',
        element: (
          <ProtectedRoute allowedRoles={['forwarder']}>
            <QuoteForm />
          </ProtectedRoute>
        ),
      },
      {
        path: 'quotes/:id',
        element: (
          <ProtectedRoute allowedRoles={['client', 'forwarder']}>
            <QuoteDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'invoices',
        element: (
          <ProtectedRoute allowedRoles={['client', 'forwarder']}>
            <Invoices />
          </ProtectedRoute>
        ),
      },
      {
        path: 'invoices/:id',
        element: (
          <ProtectedRoute allowedRoles={['client', 'forwarder']}>
            <InvoiceAnalysis />
          </ProtectedRoute>
        ),
      },
      {
        path: 'charge-master',
        element: (
          <ProtectedRoute allowedRoles={['client']}>
            <ChargeMaster />
          </ProtectedRoute>
        ),
      },
      {
        path: 'tracking',
        element: (
          <ProtectedRoute allowedRoles={['client', 'forwarder']}>
            <Tracking />
          </ProtectedRoute>
        ),
      },
      {
        path: 'copilot',
        element: (
          <ProtectedRoute allowedRoles={['client']}>
            <Copilot />
          </ProtectedRoute>
        ),
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
