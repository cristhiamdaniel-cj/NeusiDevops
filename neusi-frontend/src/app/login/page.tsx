"use client";
import PolygonsBackground from "@/components/PolygonsBackground";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login, me } from "@/lib/api";
import "./login.css";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    // Si ya hay sesión, redirige al home
    me().then((u) => {
      if (u?.is_authenticated) router.replace("/");
      setLoading(false);
    });
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const u = await login(username, password);
      if (u?.must_change_password) {
        router.replace("/change-password");
        return;
      }
      router.replace("/");
    } catch (err: any) {
      setError(err?.message || "Error al iniciar sesión");
    }
  }

  if (loading) return <p className="loading-msg">Cargando…</p>;

  return (
    <main className="login-page">
      {<PolygonsBackground /> }
      <div id="login-bg" aria-hidden="true" />
      <section className="login-wrapper" aria-label="Inicio de sesión NEUSI">
        {/* Logo centrado */}
        <header className="brand">
         <div className="brand-ring">
          <img
            src="/backlog/img/logo.png"
            alt="Neusi"
            className="brand-logo"
            width={112}
            height={112}
            
          />
          {/* anillo exterior */}
         
          {/* órbita suave */}
          <span className="brand-orbit" aria-hidden />
          </div>
           <h1><strong>Iniciar sesión</strong></h1>  
    </header>

        {/* Tarjeta */}
        <form className="login-card" onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor="username">Usuario</label>
            <input
              id="username"
              name="username"
              type="text"
              placeholder="tu usuario…"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" className="btn-primary">
            Entrar
          </button>
        </form>

        <footer className="login-footer">
          <small>© {new Date().getFullYear()} NEUSI</small>
        </footer>
      </section>
    </main>
  );
}
