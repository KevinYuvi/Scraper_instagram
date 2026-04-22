from dataclasses import dataclass, field


@dataclass(slots=True)
class PostRef:
    url: str
    pinned: bool = False


@dataclass(slots=True)
class PostStats:
    index: int
    tipo: str
    fecha: str
    likes: int
    comentarios: int
    hashtags: list[str] = field(default_factory=list)
    url: str = ""
    caption: str = ""


@dataclass(slots=True)
class ProfileStats:
    username: str = ""
    full_name: str = ""
    biography: str = ""
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    is_verified: bool = False
    profile_url: str = ""