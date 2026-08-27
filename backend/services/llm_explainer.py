"""MoodFeed LLM Complementary Explainer Service.

Synthesizes algorithmic ranking signals, score breakdowns, and user interaction context
into concise, transparent 2-3 sentence Turkish natural language explanations.
"""

from __future__ import annotations

from typing import Any


def explain_decision(
    content: dict[str, Any] | Any | None = None,
    scores: dict[str, Any] | Any | None = None,
    context: dict[str, Any] | Any | None = None,
) -> str:
    """Generates a concise (2-3 sentences) natural language explanation of the ranking decision.

    Args:
        content: Content item data (text, title, author, category, etc.).
        scores: Algorithmic scores (toxicity_score, negativity_score, ranks, breakdown, etc.).
        context: User session context (recent interactions, spiral detection, active profile, scenario, etc.).

    Returns:
        A natural, neutral, and empowering Turkish explanation.
    """
    # Normalize content
    if content is None:
        c_dict: dict[str, Any] = {}
    elif isinstance(content, dict):
        c_dict = content
    elif hasattr(content, "model_dump"):
        c_dict = content.model_dump()
    elif hasattr(content, "__dict__"):
        c_dict = content.__dict__
    else:
        c_dict = {"text": str(content)}

    category = c_dict.get("category") or "Genel"

    # Normalize scores
    if scores is None:
        s_dict: dict[str, Any] = {}
    elif isinstance(scores, dict):
        s_dict = scores
    elif hasattr(scores, "model_dump"):
        s_dict = scores.model_dump()
    elif hasattr(scores, "__dict__"):
        s_dict = scores.__dict__
    else:
        s_dict = {}

    tox = float(s_dict.get("toxicity_score", s_dict.get("toxicity", c_dict.get("toxicity_score", 0.0))) or 0.0)
    neg = float(s_dict.get("negativity_score", s_dict.get("negativity", c_dict.get("negativity_score", 0.0))) or 0.0)
    orig_rank = int(s_dict.get("original_rank", c_dict.get("original_rank", c_dict.get("originalRank", 1))) or 1)
    new_rank = int(s_dict.get("new_rank", c_dict.get("new_rank", orig_rank)) or orig_rank)
    diff = orig_rank - new_rank

    # Normalize context
    if context is None:
        ctx_dict: dict[str, Any] = {}
    elif isinstance(context, dict):
        ctx_dict = context
    elif hasattr(context, "model_dump"):
        ctx_dict = context.model_dump()
    elif hasattr(context, "__dict__"):
        ctx_dict = context.__dict__
    else:
        ctx_dict = {}

    spiral_raw = ctx_dict.get("spiral_detected")
    if spiral_raw is None and isinstance(ctx_dict.get("spiral_risk"), dict):
        spiral_raw = ctx_dict["spiral_risk"].get("spiral_detected", False)
    spiral_detected = bool(spiral_raw)
    scenario = str(ctx_dict.get("scenario", "default"))
    recent_count = int(ctx_dict.get("recent_interactions_count", ctx_dict.get("interaction_count", 5)) or 5)

    # 1. Observation Sentence (Gözlem Cümlesi)
    if tox >= 0.4:
        s1 = f"Bu içerik, metninde belirgin saldırganlık ve toksisite (%{int(tox*100)}) sinyalleri barındırıyor."
    elif neg >= 0.6 and (spiral_detected or scenario in ("high_negativity", "highNegativity")):
        s1 = f"Bu içerik, son {recent_count} etkileşiminizde tespit edilen yüksek negatiflik ve stres sinyalleri içeriyor."
    elif neg >= 0.5:
        s1 = f"Bu içerik, yüksek düzeyde şikayet ve olumsuz duygu (%{int(neg*100)}) sinyali taşıyor."
    elif diff > 0:
        s1 = f"Bu içerik, yüksek yapıcı duygu ve olumlu '{category}' etkileşimi sinyalleri içeriyor."
    else:
        s1 = f"Bu içerik, '{category}' kategorisinde dengeli ve bilgilendirici sinyaller barındırıyor."

    # 2. Algorithmic Action Sentence (Aksiyon Cümlesi)
    if diff < 0:
        s2 = f"Akışınızı dengelemek ve olumsuzluk maruziyetini azaltmak için bu içerik {abs(diff)} sıra geriye alındı."
    elif diff > 0:
        s2 = f"Akışınızdaki konu çeşitliliğini zenginleştirmek ve pozitif dengeyi desteklemek için {diff} sıra öne taşındı."
    else:
        s2 = "Akıştaki genel bilgi akışını ve tarafsızlığı korumak adına içeriğin başlangıç sırası korundu."

    # 3. User Empowerment Sentence (Kullanıcı Kontrolü Cümlesi)
    s3 = "Dilediğiniz an 'Sıralamayı Geri Al' butonuyla içeriği orijinal sırasına döndürebilir veya kaynağı sessize alabilirsiniz."

    return f"{s1} {s2} {s3}"
