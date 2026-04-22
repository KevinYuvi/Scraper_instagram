import re


def parse_count(text: str) -> int:
    value = str(text).strip().upper().replace(" ", "")

    try:
        if "MILL" in value:
            num = re.sub(r"[^0-9,\.]", "", value).replace(".", "").replace(",", ".")
            return int(float(num) * 1_000_000)

        if "MIL" in value:
            num = re.sub(r"[^0-9,\.]", "", value).replace(".", "").replace(",", ".")
            return int(float(num) * 1_000)

        if value.endswith("M"):
            return int(float(value[:-1].replace(",", ".")) * 1_000_000)

        if value.endswith("K"):
            return int(float(value[:-1].replace(",", ".")) * 1_000)

        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", value):
            return int(re.sub(r"[.,]", "", value))

        if re.fullmatch(r"\d+", value):
            return int(value)

        cleaned = re.sub(r"[^0-9]", "", value)
        return int(cleaned) if cleaned else 0

    except Exception:
        return 0


def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    tags = re.findall(r'#[\wáéíóúÁÉÍÓÚñÑ_]+', text)
    return sorted(set(tags))


def choose_caption(text: str) -> str:
    lines = [x.strip() for x in text.split("\n") if x.strip()]

    blacklist_exact = {
        "Seguir",
        "Follow",
        "Más",
        "Meta",
        "Threads",
        "Ver traducción",
        "View translation",
        "Añade un comentario...",
        "Add a comment...",
        "Responder",
        "Reply",
        "Enviar mensaje",
        "Message",
        "Ver respuestas",
        "View replies",
    }

    blacklist_contains = [
        "me gusta",
        "likes",
        "followers",
        "seguidores",
        "following",
        "seguidos",
        "publicaciones",
        "posts",
    ]

    candidates = []

    for line in lines:
        if line in blacklist_exact:
            continue

        if len(line) < 20:
            continue

        if re.fullmatch(r'[\d.,]+\s*(mil|mill\.|M|K)?', line, re.I):
            continue

        if any(term in line.lower() for term in blacklist_contains):
            continue

        if re.search(r"\b\d+\s*(d|h|min|sem)\b", line.lower()):
            continue

        candidates.append(line)

    if not candidates:
        return ""

    candidates.sort(key=lambda x: ("#" in x, len(x)), reverse=True)
    return candidates[0]
    lines = [x.strip() for x in text.split("\n") if x.strip()]

    blacklist_exact = {
        "Seguir",
        "Follow",
        "Más",
        "Meta",
        "Threads",
        "Ver traducción",
        "View translation",
        "Añade un comentario...",
        "Add a comment...",
        "Responder",
        "Reply",
        "Enviar mensaje",
        "Message",
    }

    blacklist_contains = [
        "me gusta",
        "likes",
        "followers",
        "seguidores",
        "following",
        "seguidos",
        "ver respuestas",
        "view replies",
        "publicaciones",
        "posts",
    ]

    candidates = []

    for line in lines:
        if line in blacklist_exact:
            continue

        if len(line) < 20:
            continue

        if re.fullmatch(r'[\d.,]+\s*(mil|mill\.|M|K)?', line, re.I):
            continue

        if any(term in line.lower() for term in blacklist_contains):
            continue

        # evitar líneas que parecen fechas o tiempos
        if re.search(r"\b\d+\s*(d|h|min|sem)\b", line.lower()):
            continue

        candidates.append(line)

    if not candidates:
        return ""

    # priorizar líneas con hashtags o con texto más natural
    candidates.sort(key=lambda x: ("#" in x, len(x)), reverse=True)
    return candidates[0]