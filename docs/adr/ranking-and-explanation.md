# Architecture Decision Record: Deterministic Ranking & Algorithmic Explanations

- **Status:** Accepted / Implemented
- **Date:** 2026-08-22
- **Context:** Ensuring predictable, transparent, and non-manipulative feed sorting.

---

## Decision

1. **Deterministic Ranking Engine (v1.2.0):**
   $$\text{ranking\_score} = \text{clamp}(S_{\text{orig}} - W_{\text{tox}} \cdot T - W_{\text{neg}} \cdot N \cdot R + W_{\text{div}} \cdot D \cdot R)$$
   - Zero randomness or hidden bias.
   - Stable tie-breaking based on original feed index.
   - Content items are never deleted; ranking order is optimized.
2. **Scorer Architecture:**
   - Default: High-speed, explainable rule-based Turkish keyword frequency scorer (`RuleBasedTurkishScorer`).
   - Optional: Deep learning BERTurk sentiment analyzer (`BerturkTurkishScorer`) with automated graceful fallback to rule-based analysis.
3. **Three-Tier Explanations:**
   - Tier 1: Card badge summary.
   - Tier 2: 4-Pillar Drawer (Observed signals, applied rules, rank delta, user controls).
   - Tier 3: Mathematical score breakdown formula.
4. **Linguistic Neutrality Invariant:**
   - Explanations strictly describe textual signals (e.g., "benzer konu yoğunluğu", "şikayet dili sinyali").
   - Explicit disclaimer: *"Bu açıklama psikolojik veya klinik bir değerlendirme değildir."*

---

## Consequences

- Full algorithmic reproducibility and auditability.
- User retains immediate control via Undo Recommendation and Profile presets.
