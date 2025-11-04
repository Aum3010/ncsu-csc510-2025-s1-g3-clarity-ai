import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./lib/auth-context.jsx";
import AuthGuard from "./components/AuthGuard.jsx";
import AuthWrapper from "./components/AuthWrapper.jsx";
import MainLayout from "./layouts/MainLayout.jsx";
import LoginPage from "./views/LoginPage.jsx";

import OverviewDashboard from "./views/OverviewDashboard.jsx";
import RequirementsDashboard from "./views/RequirementsDashboard.jsx";
import DocumentsDashboard from "./views/DocumentsDashboard.jsx";
import "./App.css";
import "./index.css";

// A simple placeholder for views you haven't built yet
const PlaceholderView = ({ viewName }) => (
  <div className="p-8 w-full">
    <h2 className="text-3xl font-bold text-gray-900 mb-4">{viewName} View</h2>
    <p className="text-gray-400">
      This is a placeholder for the {viewName} feature.
    </p>
  </div>
);

function App() {
  const [refreshSignal, setRefreshSignal] = useState(0);
  const triggerRefresh = () => {
    setRefreshSignal((prev) => prev + 1);
  };

  return (
    <AuthProvider>
      <Routes>
        {/* Public login route */}
        <Route
          path="/login"
          element={
            <AuthGuard requireAuth={false}>
              <LoginPage />
            </AuthGuard>
          }
        />
        


        {/* Protected routes */}
        <Route
          element={
            <AuthGuard requireAuth={true} requireCompleteProfile={true}>
              <MainLayout />
            </AuthGuard>
          }
        >
          {/* Default route redirects to overview */}
          <Route index element={<Navigate to="/overview" replace />} />

          {/* Pass refreshSignal to all dashboards that need to auto-update */}
          <Route
            path="overview"
            element={<OverviewDashboard refreshSignal={refreshSignal} />}
          />
          <Route
            path="requirements"
            element={
              <RequirementsDashboard
                refreshSignal={refreshSignal}
                onTriggerRefresh={triggerRefresh}
              />
            }
          />
          <Route
            path="documents"
            element={<DocumentsDashboard onTriggerRefresh={triggerRefresh} />}
          />

          {/* Protected routes with specific access control */}
          <Route
            path="integrations"
            element={
              <AuthWrapper
                authConfig={{
                  requireAuth: true,
                  requireCompleteProfile: true,
                  permissions: ["integrations"],
                  redirectTo: "/overview",
                }}
                onAccessDenied={(context) =>
                  console.log("Access denied to integrations:", context)
                }
              >
                <PlaceholderView viewName="Integrations" />
              </AuthWrapper>
            }
          />
          <Route
            path="team"
            element={
              <AuthWrapper
                authConfig={{
                  requireAuth: true,
                  requireCompleteProfile: true,
                  permissions: ["team"],
                  redirectTo: "/overview",
                }}
                onAccessDenied={(context) =>
                  console.log("Access denied to team:", context)
                }
              >
                <PlaceholderView viewName="Team Management" />
              </AuthWrapper>
            }
          />

          {/* Admin route with role-based protection */}
          <Route
            path="admin"
            element={
              <AuthWrapper
                authConfig={{
                  requireAuth: true,
                  requireCompleteProfile: true,
                  roles: ["admin"],
                  permissions: ["admin_panel"],
                  redirectTo: "/overview",
                }}
                onAccessDenied={(context) =>
                  console.log("Access denied to admin:", context)
                }
              >
                <PlaceholderView viewName="Admin Panel" />
              </AuthWrapper>
            }
          />

          {/* Beta features route for pilot users */}
          <Route
            path="beta"
            element={
              <AuthWrapper
                authConfig={{
                  requireAuth: true,
                  requireCompleteProfile: true,
                  requirePilot: true,
                  permissions: ["beta_features"],
                  redirectTo: "/overview",
                }}
                onAccessDenied={(context) =>
                  console.log("Access denied to beta features:", context)
                }
              >
                <PlaceholderView viewName="Beta Features" />
              </AuthWrapper>
            }
          />
        </Route>

        <Route
          path="*"
          element={<PlaceholderView viewName="404 Not Found" />}
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
