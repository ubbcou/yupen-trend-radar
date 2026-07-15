from dataclasses import dataclass


FRONT_RANK_MAX = 3
OVERHEAT_DEVIATION_PCT = 8.0
CONFIRMATION_VOLUME_RATIO = 1.0
CONTINUITY_DAYS = 2


@dataclass(frozen=True)
class DirectionResult:
    group: str
    action: str
    core_trend: bool
    front: bool
    above_twenty_day: bool
    stronger_than_benchmark: bool
    continuous: bool
    volume_confirmed: bool
    article_stance: str


def evaluate_direction(
    *,
    rank: int,
    deviation_pct: float,
    change_pct: float,
    benchmark_change_pct: float,
    volume_ratio: float,
    recent_ranks: list[int],
    article_stance: str | None = None,
) -> DirectionResult:
    if article_stance not in {"support", "neutral", "oppose"}:
        raise ValueError("article_stance must be support, neutral, or oppose")
    front = rank <= FRONT_RANK_MAX
    above_twenty_day = deviation_pct > 0
    stronger_than_benchmark = change_pct > benchmark_change_pct
    continuous = (
        len(recent_ranks) >= CONTINUITY_DAYS
        and all(item <= FRONT_RANK_MAX for item in recent_ranks[-CONTINUITY_DAYS:])
    )
    volume_confirmed = volume_ratio >= CONFIRMATION_VOLUME_RATIO
    core_trend = front and above_twenty_day and stronger_than_benchmark
    confirmed = core_trend and continuous and volume_confirmed

    if confirmed and article_stance == "support":
        group = "主攻"
        action = "不追高" if deviation_pct >= OVERHEAT_DEVIATION_PCT else "可关注"
    elif core_trend and article_stance == "oppose":
        group = "等待"
        action = "文章冲突"
    elif confirmed:
        group = "试探"
        action = "等待文章确认"
    elif core_trend:
        group = "试探"
        action = "等待确认"
    elif front and above_twenty_day and continuous:
        group = "趋势保持"
        action = "不新增"
    elif not above_twenty_day and not front:
        group = "回避"
        action = "不纳入"
    else:
        group = "等待"
        action = "观察"

    if group in {"主攻", "试探"} and deviation_pct >= OVERHEAT_DEVIATION_PCT:
        action = "不追高"

    return DirectionResult(
        group=group,
        action=action,
        core_trend=core_trend,
        front=front,
        above_twenty_day=above_twenty_day,
        stronger_than_benchmark=stronger_than_benchmark,
        continuous=continuous,
        volume_confirmed=volume_confirmed,
        article_stance=article_stance,
    )
