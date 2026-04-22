import re

def parse_count(text: str) -> int:
    value = str(text).upper().strip().replace(" ", "")
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
        return int(value.replace(".", "").replace(",", ""))
    except Exception:
        return 0

def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    tags = re.findall(r'#[\wáéíóúÁÉÍÓÚñÑ_]+', text)
    return sorted(set(tags))

def choose_caption(text: str) -> str:
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    candidates = []
    for line in lines:
        if len(line) < 15:
            continue
        if re.fullmatch(r'[\d.,]+\s*(mil|mill\.|M|K)?', line, re.I):
            continue
        candidates.append(line)
    return max(candidates, key=len) if candidates else ""