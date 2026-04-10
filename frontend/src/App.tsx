import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Library from "./pages/Library";
import BookDetail from "./pages/BookDetail";
import Network from "./pages/Network";
import Stats from "./pages/Stats";
import Settings from "./pages/Settings";

function Protected({ children }: { children: React.ReactNode }) {
  const { isAuthed } = useAuth();
  if (!isAuthed) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/*"
        element={
          <Protected>
            <AppShell>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/library" element={<Library />} />
                <Route path="/books/:id" element={<BookDetail />} />
                <Route path="/network" element={<Network />} />
                <Route path="/stats" element={<Stats />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </AppShell>
          </Protected>
        }
      />
    </Routes>
  );
}
