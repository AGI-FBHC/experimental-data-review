#!/usr/bin/env python3
"""
GRIM, GRIMMER, and DEBIT Tests v2
- GRIM only runs when scale_type is "integer" or explicitly marked discrete
- GRIMMER is labeled as heuristic; references scrutiny::grimmer_map() for formal
- DEBIT only runs when manuscript reports binary SD (not auto-computed)
- Unknown scales default to SKIP, not FAIL
"""

import json
import math
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


def decimal_places(value: float) -> int:
    s = str(value)
    if "." in s:
        return len(s.split(".")[1].rstrip("0"))
    return 0


def grim_test(mean: float, n: int, scale_min: float = 1.0, scale_max: float = 5.0,
              prec: Optional[int] = None) -> Dict[str, Any]:
    if prec is None:
        prec = decimal_places(mean)

    # P0-4: compact output — don't save full possible_means list
    lo, hi = int(n * scale_min), int(n * scale_max)
    granularity = 1.0 / n
    grim_pass = False
    closest = None
    next_possible = None
    best_diff = float("inf")

    for s in range(lo, hi + 1):
        m = round(s / n, prec)
        diff = abs(mean - m)
        if diff < 10**(-prec - 1):
            grim_pass = True
        if diff < best_diff:
            best_diff = diff
            next_possible = closest
            closest = m
        elif diff < best_diff + 1e-9 and next_possible is None:
            next_possible = m

    return {
        "mean": mean, "n": n, "scale_min": scale_min, "scale_max": scale_max,
        "mean_prec": prec, "granularity": granularity,
        "grim_pass": grim_pass, "closest_possible": closest,
        "next_possible": next_possible,
    }


def grimmer_heuristic(mean: float, sd: float, n: int, scale_min: float = 1.0,
                      scale_max: float = 5.0) -> Dict[str, Any]:
    """Lightweight heuristic — NOT equivalent to scrutiny::grimmer_map().
    
    P0-1 defense: if mean is outside scale bounds, skip instead of crashing.
    P0-1 defense: clamp boundary_ratio to [0, 1] to prevent math domain error.
    """
    # Defense: mean outside scale bounds indicates wrong scale inference
    if mean < scale_min - 0.5 or mean > scale_max + 0.5:
        return {
            "mean": mean, "sd": sd, "n": n,
            "scale_min": scale_min, "scale_max": scale_max,
            "overall_pass": None,
            "status": "skipped",
            "reason": f"mean={mean} outside inferred scale [{scale_min}, {scale_max}]; "
                      f"scale inference likely wrong. Skipping GRIMMER.",
        }

    grim = grim_test(mean, n, scale_min, scale_max)
    variance = sd ** 2
    max_var = ((scale_max - scale_min) ** 2) / 4
    sd_variance_pass = variance <= max_var + 1e-9

    mean_center = (scale_min + scale_max) / 2
    dist_from_center = abs(mean - mean_center)
    max_dist = (scale_max - scale_min) / 2
    if max_dist > 0:
        boundary_ratio = dist_from_center / max_dist
        # P0-1: clamp boundary_ratio to prevent math domain error
        boundary_ratio = max(0.0, min(1.0, boundary_ratio))
        max_sd_at_mean = (scale_max - scale_min) * math.sqrt(1 - boundary_ratio**2) / 2
        sd_mono_pass = sd <= max_sd_at_mean + 1e-9 or boundary_ratio < 0.3
    else:
        sd_mono_pass = True

    overall = grim["grim_pass"] and sd_variance_pass and sd_mono_pass
    details = []
    if not grim["grim_pass"]:
        details.append(f"GRIM failed: mean {mean} not possible with N={n} on {scale_min}-{scale_max}")
    if not sd_variance_pass:
        details.append(f"SD variance exceeds max possible ({math.sqrt(max_var):.3f}) for this scale")
    if not sd_mono_pass:
        details.append("SD inconsistent with mean position on bounded scale")

    return {
        **{k: v for k, v in grim.items() if k != "granularity"},
        "sd": sd,
        "sd_prec": decimal_places(sd),
        "sd_variance_pass": sd_variance_pass,
        "sd_monotonicity_pass": sd_mono_pass,
        "overall_pass": overall,
        "note": "This is a lightweight heuristic. For formal forensic analysis, use scrutiny::grimmer_map() in R.",
        "discrepancy_details": "; ".join(details) if details else None,
    }


def debit_test(proportion: float, reported_sd: Optional[float], n: int) -> Optional[Dict[str, Any]]:
    """DEBIT only runs when manuscript explicitly reports binary SD."""
    if reported_sd is None:
        return {
            "status": "skipped",
            "reason": "DEBIT skipped: no reported binary SD found in manuscript. "
                      "Auto-computed SD from proportion provides no independent check.",
        }

    theoretical_sd = (proportion * (1 - proportion)) ** 0.5
    sd_prec = decimal_places(reported_sd)
    tol = 0.5 * (10 ** (-sd_prec)) + 0.001

    count = round(proportion * n)
    recon_p = count / n
    recon_sd = (recon_p * (1 - recon_p)) ** 0.5

    var_pass = abs(reported_sd - theoretical_sd) <= tol
    mono_pass = abs(reported_sd - recon_sd) <= tol
    overall = var_pass and mono_pass

    details = []
    if not var_pass:
        details.append(f"Reported SD {reported_sd:.4f} != theoretical {theoretical_sd:.4f}")
    if not mono_pass:
        details.append(f"SD inconsistent with integer count {count}/{n}")

    return {
        "proportion": proportion,
        "reported_sd": reported_sd,
        "theoretical_sd": theoretical_sd,
        "n": n,
        "sd_variance_pass": var_pass,
        "sd_monotonicity_pass": mono_pass,
        "overall_pass": overall,
        "status": "run",
        "discrepancy_details": "; ".join(details) if details else None,
    }


def run_all_tests(extracted_stats: Dict[str, Any]) -> Dict[str, Any]:
    grim_results = []
    grimmer_results = []
    debit_results = []
    summary = {"grim_pass": 0, "grim_fail": 0, "grim_skip": 0,
               "grimmer_pass": 0, "grimmer_fail": 0,
               "debit_pass": 0, "debit_fail": 0, "debit_skip": 0}

    for location, stats in extracted_stats.items():
        for desc in stats.get("descriptives", []):
            mean = desc.get("mean")
            n = desc.get("n")
            sd = desc.get("sd")
            scale_type = desc.get("scale_type", "unknown")
            scale_min = desc.get("scale_min", 1.0)
            scale_max = desc.get("scale_max", 5.0)

            if mean is None or n is None or n <= 0:
                continue

            # P0-5: Only run GRIM on confirmed integer/discrete scales
            if scale_type not in ("integer",):
                grim_results.append({
                    "status": "skipped",
                    "location": location,
                    "raw_text": desc.get("raw_text", ""),
                    "mean": mean, "n": n,
                    "scale_type": scale_type,
                    "reason": f"Scale type is '{scale_type}', not 'integer'. "
                              f"GRIM only applies to discrete/integer scales (Likert, counts). "
                              f"Continuous scales (VAS, reaction time, age) should NOT be GRIM-tested.",
                })
                summary["grim_skip"] += 1
                continue

            grim = grim_test(mean, n, scale_min or 1.0, scale_max or 5.0)
            grim["location"] = location
            grim["raw_text"] = desc.get("raw_text", "")
            grim["status"] = "run"
            grim["scale_type"] = scale_type
            grim_results.append(grim)
            if grim["grim_pass"]:
                summary["grim_pass"] += 1
            else:
                summary["grim_fail"] += 1

            # GRIMMER
            if sd is not None and sd > 0:
                grimmer = grimmer_heuristic(mean, sd, n, scale_min or 1.0, scale_max or 5.0)
                grimmer["location"] = location
                grimmer["raw_text"] = desc.get("raw_text", "")
                grimmer["scale_type"] = scale_type
                grimmer_results.append(grimmer)
                if grimmer.get("status") == "skipped":
                    summary["grim_skip"] += 1  # Count as skip
                elif grimmer.get("overall_pass"):
                    summary["grimmer_pass"] += 1
                else:
                    summary["grimmer_fail"] += 1

        # DEBIT — P0-7: only when manuscript reports binary SD
        for prop in stats.get("proportions", []):
            p_val = prop.get("proportion", 0)
            n = prop.get("total_n", 0)
            reported_sd = prop.get("reported_sd")

            if n > 0:
                debit = debit_test(p_val, reported_sd, n)
                if debit.get("status") == "run":
                    debit["location"] = location
                    debit["raw_text"] = prop.get("raw_text", "")
                    debit_results.append(debit)
                    if debit["overall_pass"]:
                        summary["debit_pass"] += 1
                    else:
                        summary["debit_fail"] += 1
                else:
                    debit["location"] = location
                    debit["raw_text"] = prop.get("raw_text", "")
                    debit_results.append(debit)
                    summary["debit_skip"] += 1

    return {
        "grim": grim_results,
        "grimmer": grimmer_results,
        "debit": debit_results,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="GRIM/GRIMMER/DEBIT tests")
    parser.add_argument("--input", "-i", required=True, help="Input JSON from extractor")
    parser.add_argument("--output", "-o", default="grim_results.json", help="Output JSON")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = run_all_tests(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    s = results["summary"]
    print(f"GRIM: {s.get('grim_pass', 0)} pass, {s.get('grim_fail', 0)} fail, {s.get('grim_skip', 0)} skip")
    print(f"GRIMMER: {s.get('grimmer_pass', 0)} pass, {s.get('grimmer_fail', 0)} fail")
    print(f"DEBIT: {s.get('debit_pass', 0)} pass, {s.get('debit_fail', 0)} fail, {s.get('debit_skip', 0)} skip")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
