import { useMemo, useState } from "react";
import { Search, Play } from "lucide-react";

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
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}

export default function App() {
    const [username, setUsername] = useState("marvel");
    const [maxPosts, setMaxPosts] = useState(10);
    const [headless, setHeadless] = useState(false);
    const [excludePinned, setExcludePinned] = useState(false);
    const [loading, setLoading] = useState(false);
    const [profile, setProfile] = useState(null);
    const [posts, setPosts] = useState([]);
    const [error, setError] = useState("");

    const totals = useMemo(() => {
        const likes = posts.reduce((acc, item) => acc + (item.likes || 0), 0);
        const comments = posts.reduce((acc, item) => acc + (item.comentarios || 0), 0);
        return {
            likes,
            comments,
            hashtags: new Set(posts.flatMap((item) => item.hashtags || [])).size,
        };
    }, [posts]);

    async function handleRun() {
        const cleanUsername = username.trim().replace("@", "");
        if (!cleanUsername) {
            setError("Ingresa un nombre de usuario válido.");
            return;
        }

        setLoading(true);
        setError("");

        try {
            const response = await fetch("http://127.0.0.1:8000/api/scrape", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: cleanUsername,
                    max_posts: Number(maxPosts),
                    headless,
                    exclude_pinned: excludePinned,
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
        <div className="app">
            <div className="container">
                <h1>Instagram Scraper</h1>

                <div className="panel">
                    <div className="field">
                        <label>Nombre de usuario</label>
                        <div className="input-row">
                            <span className="icon"><Search size={16} /></span>
                            <input
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="marvel"
                            />
                            <button onClick={handleRun} disabled={loading}>
                                <Play size={16} />
                                {loading ? " Ejecutando..." : " Ejecutar"}
                            </button>
                        </div>
                    </div>

                    <div className="field-grid">
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

                        <div className="checks">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={headless}
                                    onChange={(e) => setHeadless(e.target.checked)}
                                />
                                Headless
                            </label>
                        </div>
                    </div>

                    {error ? <div className="error">{error}</div> : null}
                </div>

                {profile ? (
                    <div className="grid two">
                        <div className="card profile-card">
                            <h2>Perfil</h2>
                            <div className="profile-line">
                                <strong>Usuario:</strong> @{profile.username || username.trim().replace("@", "")}
                            </div>                            <div className="profile-line"><strong>Publicaciones:</strong> {formatNumber(profile.posts_count)}</div>
                            <div className="profile-line"><strong>Followers:</strong> {formatNumber(profile.followers)}</div>
                            <div className="profile-line"><strong>Following:</strong> {formatNumber(profile.following)}</div>
                            <div className="profile-line profile-url"><strong>URL:</strong> {profile.profile_url}</div>
                        </div>

                        <div className="stats-grid">
                            <div className="stat-box stat-blue">
                                <h3>Posts leídos</h3>
                                <div className="value">{formatNumber(posts.length)}</div>
                            </div>

                            <div className="stat-box stat-purple">
                                <h3>Likes totales</h3>
                                <div className="value">{formatNumber(totals.likes)}</div>
                            </div>

                            <div className="stat-box stat-green">
                                <h3>Comentarios totales</h3>
                                <div className="value">{formatNumber(totals.comments)}</div>
                            </div>

                            <div className="stat-box stat-orange">
                                <h3>Hashtags únicos</h3>
                                <div className="value">{formatNumber(totals.hashtags)}</div>
                            </div>
                        </div>
                    </div>
                ) : null}

                <div className="card">
                    <h2>Publicaciones</h2>
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
                                    <th>URL</th>
                                    <th>Caption</th>
                                </tr>
                            </thead>

                            <tbody>
                                {posts.map((item) => (
                                    <tr key={item.url}>
                                        <td>{item.index}</td>
                                        <td>{item.tipo}</td>
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
                                            <a
                                                href={item.url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="post-link"
                                            >
                                                Ver publicación
                                            </a>
                                        </td>

                                        <td className="caption-cell">{item.caption || "-"}</td>
                                    </tr>
                                ))}

                                {!posts.length ? (
                                    <tr>
                                        <td colSpan="8">Sin resultados todavía.</td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}