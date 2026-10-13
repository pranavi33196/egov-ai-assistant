"""
bhashini/translate.py  (patched)

Changes vs. the original:
  * Honest provider labels: 'bhashini_official_dhruva' | 'mymemory_nmt' | 'untranslated_fallback'
    (the MyMemory fallback used to be labelled 'bhashini_neural_nmt').
  * Long lines are split on sentence boundaries so no chunk exceeds MyMemory's ~500-char limit
    (previously a long 'Procedure:' line was silently left untranslated).
  * A failed/untranslated result is no longer cached; the cache is size-limited.
  * MyMemory quota-warning text is treated as a failure instead of being shown to the user.
"""

import re
import logging
from typing import Dict, List
from bhashini.client import BhashiniClient

logger = logging.getLogger(__name__)

_CACHE_MAX = 500
_TRANSLATION_CACHE: Dict[str, dict] = {}

LANG_MAPPINGS = {
    "te": "te-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "en": "en-GB",
}


def _cache_put(key: str, text: str, provider: str) -> None:
    if len(_TRANSLATION_CACHE) >= _CACHE_MAX:
        _TRANSLATION_CACHE.pop(next(iter(_TRANSLATION_CACHE)))
    _TRANSLATION_CACHE[key] = {"text": text, "provider": provider}


def _split_long_line(line: str, max_chars: int) -> List[str]:
    """Split one long line on sentence ends, then on spaces, so each piece <= max_chars."""
    if len(line) <= max_chars:
        return [line]
    parts, buf = [], ""
    for sentence in re.split(r"(?<=[.!?\u0964])\s+", line):
        while len(sentence) > max_chars:
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if buf:
                parts.append(buf)
                buf = ""
            parts.append(sentence[:cut])
            sentence = sentence[cut:].lstrip()
        if buf and len(buf) + 1 + len(sentence) > max_chars:
            parts.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    if buf:
        parts.append(buf)
    return parts


def _chunk_text_by_paragraphs(text: str, max_chars: int = 450) -> List[str]:
    """Group lines into chunks of at most max_chars, never cutting inside a sentence if avoidable."""
    if len(text) <= max_chars:
        return [text]

    pieces: List[str] = []
    for line in text.split("\n"):
        pieces.extend(_split_long_line(line, max_chars))

    chunks, current, current_len = [], [], 0
    for piece in pieces:
        if current and current_len + len(piece) + 1 > max_chars:
            chunks.append("\n".join(current))
            current, current_len = [piece], len(piece)
        else:
            current.append(piece)
            current_len += len(piece) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def translate_text(text: str, source_lang: str, target_lang: str) -> dict:
    if not text or not text.strip():
        return {"translated_text": text, "provider": "none"}

    src = source_lang.lower().strip().split("-")[0]
    tgt = target_lang.lower().strip().split("-")[0]

    if src == tgt:
        return {"translated_text": text, "provider": "direct_pass"}

    cache_key = f"{src}->{tgt}:{text.strip()}"
    hit = _TRANSLATION_CACHE.get(cache_key)
    if hit:
        return {"translated_text": hit["text"], "provider": f"{hit['provider']}_cached"}

    client = BhashiniClient()

    # 1. Official Bhashini / Dhruva pipeline (only if credentials are configured)
    if client.is_configured():
        try:
            res = client.call_translation_pipeline(text, src, tgt)
            if res.get("success") and res.get("translated_text"):
                _cache_put(cache_key, res["translated_text"], "bhashini_official_dhruva")
                return {"translated_text": res["translated_text"], "provider": "bhashini_official_dhruva"}
            logger.warning("Bhashini returned no translation: %s", res.get("error"))
        except Exception as e:
            logger.warning("Bhashini API call failed: %s", e)

    # 2. Fallback: MyMemory via deep-translator
    src_mapped = LANG_MAPPINGS.get(src, src)
    tgt_mapped = LANG_MAPPINGS.get(tgt, tgt)

    try:
        from deep_translator import MyMemoryTranslator
        translator = MyMemoryTranslator(source=src_mapped, target=tgt_mapped)

        translated_chunks, translated_any = [], False
        for chunk in _chunk_text_by_paragraphs(text, max_chars=450):
            if not chunk.strip():
                translated_chunks.append(chunk)
                continue
            try:
                trans = translator.translate(chunk)
                if trans and trans.strip() and "MYMEMORY WARNING" not in trans.upper():
                    translated_chunks.append(trans)
                    translated_any = True
                else:
                    translated_chunks.append(chunk)
            except Exception as ce:
                logger.debug("Chunk translation error: %s", ce)
                translated_chunks.append(chunk)

        result_text = "\n".join(translated_chunks)
        if translated_any:
            _cache_put(cache_key, result_text, "mymemory_nmt")
            return {"translated_text": result_text, "provider": "mymemory_nmt"}
        return {"translated_text": text, "provider": "untranslated_fallback"}

    except Exception as e:
        logger.error("Translation engine fallback error: %s", e)

    return {"translated_text": text, "provider": "untranslated_fallback"}
