import re

def parse_count(text: str) -> int:
    value = str(text or "").strip().upper().replace(" ", "")

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

        if value.isdigit():
            return int(value)

        cleaned = re.sub(r"[^0-9]", "", value)
        return int(cleaned) if cleaned else 0

    except Exception:
        return 0

def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []

    tags = re.findall(r"#[\wáéíóúÁÉÍÓÚñÑ_]+", text)
    return sorted(set(tags))