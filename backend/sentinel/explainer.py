"""
TradeFusion AI - Sentinel Explainer
Generates human-readable reasons for signals
"""

from typing import Dict


def generate_explanation(result: Dict, structure: Dict, symbol: str = "ASSET") -> str:
    signal = result["signal"]
    conf = result["confidence"]
    breakdown = result.get("breakdown", {})
    risk_mode = result.get("risk_mode", "medium")

    lines = []
    lines.append(f"Sentinel Analysis for {symbol}")
    lines.append("=" * 40)
    lines.append(f"Signal      : {signal}")
    lines.append(f"Confidence  : {conf}%")
    lines.append(f"Risk Mode   : {risk_mode.capitalize()}")
    lines.append(f"Structure   : {structure.get('structure', 'unknown').capitalize()}")

    if structure.get("support"):
        lines.append(f"Support     : {structure['support']}")
    if structure.get("resistance"):
        lines.append(f"Resistance  : {structure['resistance']}")

    lines.append("\nIndicator Breakdown:")
    for name, scores in breakdown.items():
        bull = scores["bull"]
        bear = scores["bear"]
        bias = "Bullish" if bull > bear else "Bearish" if bear > bull else "Neutral"
        lines.append(f"  • {name.upper():12} → {bias} (Bull {bull}% / Bear {bear}%)")

    # Summary sentence
    if signal == "BUY":
        lines.append(f"\nSummary: Multiple indicators are aligned bullishly with {conf}% confidence. Structure is {structure.get('structure', 'neutral')}.")
    elif signal == "SELL":
        lines.append(f"\nSummary: Multiple indicators are aligned bearishly with {conf}% confidence. Structure is {structure.get('structure', 'neutral')}.")
    else:
        lines.append(f"\nSummary: Insufficient agreement between indicators (confidence {conf}% below threshold). No trade recommended.")

    return "\n".join(lines)
