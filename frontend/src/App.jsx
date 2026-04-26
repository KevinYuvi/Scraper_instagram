import { useMemo, useState } from "react";
import { Search, Play, Users, UserPlus, Images, Heart, MessageCircle, Hash } from "lucide-react";

const apiUrl = "http://127.0.0.1:8000/api/scrape";

function formatNumber(value) {
    return new Intl.NumberFormat("es-EC").format(value || 0);
}

function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;

    return new Intl.DateTimeFormat("es-EC", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).format(date);
}

function MetricCard({ title, value, icon: Icon }) {
    return (
        <div className="metric-card">
            <div className="metric-icon">
                <Icon size={20} />
            </div>
            <div>
                <p>{title}</p>
                <strong>{formatNumber(value)}</strong>
            </div>
        </div>
    );
}

export default function App() {
    const [username, setUsername] = useState("marvel");
    const [maxPosts, setMaxPosts] = useState(10);
    const [loading, setLoading] = useState(false);
    const [profile, setProfile] = useState(null);
    const [posts, setPosts] = useState([]);
    const [error, setError] = useState("");

    const cleanUsername = username.trim().replace("@", "");

    const totals = useMemo(() => {
        const likes = posts.reduce((acc, item) => acc + (item.likes || 0), 0);
        const comments = posts.reduce((acc, item) => acc + (item.comentarios || 0), 0);
        const hashtags = new Set(posts.flatMap((item) => item.hashtags || [])).size;

        return { likes, comments, hashtags };
    }, [posts]);

    async function handleRun() {
        if (!cleanUsername) {
            setError("Ingresa un nombre de usuario válido.");
            return;
        }

        setLoading(true);
        setError("");

        try {
            const response = await fetch(apiUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: cleanUsername,
                    max_posts: Number(maxPosts),
                    
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "No se pudo ejecutar el scraper.");
            }

            setProfile(data.profile || null);
            setPosts(data.posts || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error inesperado.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="app">
            <section className="hero">
                <div>
                    <h1> Instagram Scraper</h1>
                </div>
            </section>

            <section className="panel">
                <div className="field main-field">
                    <label>Nombre de usuario</label>
                    <div className="input-row">
                        <div className="input-with-icon">
                            <Search size={17} />
                            <input
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="marvel"
                            />
                        </div>

                        <button onClick={handleRun} disabled={loading}>
                            <Play size={16} />
                            {loading ? "Ejecutando..." : "Ejecutar"}
                        </button>
                    </div>
                </div>

                <div className="options-row">
                    <div className="field">
                        <label>Máximo de publicaciones</label>
                        <input
                            type="number"
                            min="1"
                            max="100"
                            value={maxPosts}
                            onChange={(e) => setMaxPosts(e.target.value)}
                        />
                    </div>

                </div>

                {error ? <div className="error">{error}</div> : null}
            </section>

            {profile ? (
                <>
                    <section className="profile-summary">
                        <div className="profile-card">
                            <div>
                                <span className="eyebrow">Perfil</span>
                                <h2>{profile.username || cleanUsername}</h2>
                            </div>

                            <a href={profile.profile_url} target="_blank" rel="noreferrer">
                                Ver perfil
                            </a>
                        </div>

                        <div className="metrics-grid">
                            <MetricCard title="Seguidores" value={profile.followers} icon={Users} />
                            <MetricCard title="Seguidos" value={profile.following} icon={UserPlus} />
                            <MetricCard title="Publicaciones" value={profile.posts_count} icon={Images} />                            <MetricCard title="Likes totales" value={totals.likes} icon={Heart} />
                            <MetricCard title="Comentarios" value={totals.comments} icon={MessageCircle} />
                            <MetricCard title="Hashtags" value={totals.hashtags} icon={Hash} />
                        </div>
                    </section>

                    <section className="card">
                        <div className="section-header">
                            <div>
                                <span className="eyebrow">Detalle</span>
                                <h2>Publicaciones analizadas</h2>
                            </div>
                        </div>

                        <div className="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Tipo</th>
                                        <th>Fecha</th>
                                        <th>Likes</th>
                                        <th>Comentarios</th>
                                        <th>Hashtags</th>
                                        <th>Publicación</th>
                                        <th>Comentario</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {posts.map((item) => (
                                        <tr key={item.url}>
                                            <td>{item.index}</td>
                                            <td><span className="badge">{item.tipo}</span></td>
                                            <td>{formatDate(item.fecha)}</td>
                                            <td>{formatNumber(item.likes)}</td>
                                            <td>{formatNumber(item.comentarios)}</td>
                                            <td>
                                                {(item.hashtags || []).length ? (
                                                    item.hashtags.map((tag) => (
                                                        <span key={tag} className="tag">{tag}</span>
                                                    ))
                                                ) : (
                                                    "-"
                                                )}
                                            </td>
                                            <td>
                                                <a href={item.url} target="_blank" rel="noreferrer" className="post-link">
                                                    Ver
                                                </a>
                                            </td>
                                            <td className="caption-cell">{item.caption || "-"}</td>
                                        </tr>
                                    ))}

                                    {!posts.length ? (
                                        <tr>
                                            <td colSpan="8" className="empty">
                                                Sin resultados todavía.
                                            </td>
                                        </tr>
                                    ) : null}
                                </tbody>
                            </table>
                        </div>
                    </section>
                </>
            ) : null}
        </main>
    );
}