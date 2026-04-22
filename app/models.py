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