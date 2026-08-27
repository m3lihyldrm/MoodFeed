"""System Usability Scale (SUS) Score Calculation.

Standard SUS calculation (Brooke, 1996):
- Odd items (1, 3, 5, 7, 9): score - 1
- Even items (2, 4, 6, 8, 10): 5 - score
- Multiplier: sum * 2.5 (Score range: 0 - 100)
"""

from __future__ import annotations


def calculate_sus_score(responses: list[int]) -> float:
    """Calculates standard SUS score from exactly 10 Likert scale responses (1-5)."""
    if len(responses) != 10:
        raise ValueError("SUS anketi tam 10 soru içermelidir.")

    total = 0
    for i, r in enumerate(responses):
        if not isinstance(r, (int, float)) or not (1 <= r <= 5):
            raise ValueError(f"Geçersiz Likert yanıtı: {r}. Yanıtlar 1 ile 5 arasında olmalıdır.")
        score = int(r)
        if i % 2 == 0:  # Tek numaralı soru (1., 3., 5., 7., 9. soru -> index 0, 2, 4, 6, 8)
            total += (score - 1)
        else:  # Çift numaralı soru (2., 4., 6., 8., 10. soru -> index 1, 3, 5, 7, 9)
            total += (5 - score)

    return round(float(total * 2.5), 2)
