from typing import List, Dict, Any


REC_WEIGHT = {
    "强烈推荐": 3,
    "推荐": 2,
    "观察": 1,
    "不推荐": 0,
    "无法评估": -1,
    "未提取": -1,
}


def score_band(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = []

    for item in results:
        current = dict(item)
        current["score"] = int(current.get("score", 0) or 0)
        current["recommendation"] = current.get("recommendation", "未提取")
        current["confidence"] = int(current.get("confidence", 0) or 0)
        current["recommendation_weight"] = REC_WEIGHT.get(current["recommendation"], -1)
        current["score_band"] = score_band(current["score"])
        ranked.append(current)

    ranked.sort(
        key=lambda x: (
            x["score"],
            x["recommendation_weight"],
            x.get("confidence", 0),
        ),
        reverse=True,
    )

    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx

    return ranked
