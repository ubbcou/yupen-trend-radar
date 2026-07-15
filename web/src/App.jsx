import { useEffect, useState } from "react";

const GROUP_COPY = {
  主攻: "完整确认",
  试探: "趋势成立，等待确认",
  趋势保持: "趋势未破，不新增",
  等待: "条件不足",
  回避: "趋势失效",
};

const CONDITION_COPY = {
  frontRank: "鱼盆前排",
  aboveMa20: "站上20日线",
  strongerThanBenchmark: "强于大盘",
  continuous: "连续性",
  volumeConfirmed: "量能确认",
};

const STANCE_COPY = {
  support: "支持",
  neutral: "中性",
  oppose: "反对",
};

const AVOID_PREVIEW_COUNT = 6;
const publicPath = (path) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, "")}`;

function formatPercent(value) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatRankMovement(direction) {
  const prefix = `较 ${direction.previousDataDate} `;
  if (direction.rankMovement === 0) {
    return `${prefix}持平`;
  }
  if (direction.rankMovement > 0) {
    return `${prefix}上升 ${direction.rankMovement} 名`;
  }
  return `${prefix}下降 ${Math.abs(direction.rankMovement)} 名`;
}

function LoadingState() {
  return (
    <main className="state-page" aria-live="polite">
      <p>正在读取已校验的项目快照…</p>
    </main>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <main className="state-page error-state" role="alert">
      <strong>项目快照不可用</strong>
      <p>{message}</p>
      <button type="button" onClick={onRetry}>重试</button>
    </main>
  );
}

export function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [avoidExpanded, setAvoidExpanded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch(publicPath("data/project-snapshot.json"), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`读取失败（${response.status}）`);
        }
        return response.json();
      })
      .then((data) => {
        setSnapshot(data);
        setSelectedId(data.directions[0]?.id ?? "");
      })
      .catch((reason) => {
        if (reason.name !== "AbortError") {
          setError(reason.message || "无法读取项目快照");
        }
      });
    return () => controller.abort();
  }, [retryKey]);

  const directionsByName = new Map(snapshot?.directions.map((row) => [row.name, row]) ?? []);

  function selectDirection(id) {
    setSelectedId(id);
    if (window.matchMedia("(max-width: 620px)").matches) {
      window.requestAnimationFrame(() => {
        document
          .querySelector("[data-testid='direction-detail']")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          setError("");
          setSnapshot(null);
          setRetryKey((value) => value + 1);
        }}
      />
    );
  }
  if (!snapshot) {
    return <LoadingState />;
  }

  const { article, fishDataDates, validationStatus } = snapshot.meta;
  const selectedDirection =
    snapshot.directions.find((row) => row.id === selectedId) ?? snapshot.directions[0];
  const mainGroup = snapshot.groups.find((group) => group.name === "主攻");
  const avoidGroup = snapshot.groups.find((group) => group.name === "回避");
  const focusGroups = snapshot.groups.filter((group) => group.name !== "回避");
  const visibleAvoidDirections = avoidExpanded
    ? avoidGroup?.directions ?? []
    : avoidGroup?.directions.slice(0, AVOID_PREVIEW_COUNT) ?? [];
  const marketTitle = mainGroup?.directions.length
    ? `${mainGroup.directions.length} 个主攻方向`
    : "当前无主攻方向";

  function renderDirection(name) {
    const direction = directionsByName.get(name);
    return (
      <button
        type="button"
        className={selectedId === direction.id ? "direction-row selected" : "direction-row"}
        onClick={() => selectDirection(direction.id)}
        key={direction.id}
        aria-pressed={selectedId === direction.id}
        aria-controls="direction-detail"
      >
        <span className="direction-copy">
          <strong>{name}</strong>
          <small>
            {direction.type === "sector" ? "板块" : "指数"} · {direction.action}
          </small>
        </span>
        <small className="direction-rank">第 {direction.rank}</small>
      </button>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">猫笔叨</span>
          <div>
            <h1>猫笔叨鱼盆方向雷达</h1>
            <p>趋势方向复盘 · 只读</p>
          </div>
        </div>
        <dl className="date-ledger" aria-label="数据日期">
          <div>
            <dt>文章</dt>
            <dd>{article.date}</dd>
          </div>
          <div>
            <dt>指数</dt>
            <dd>{fishDataDates.index}</dd>
          </div>
          <div>
            <dt>板块</dt>
            <dd>{fishDataDates.sector}</dd>
          </div>
          <div className="validation-item">
            <dt>校验</dt>
            <dd>{validationStatus === "passed" ? "通过" : "未确认"}</dd>
          </div>
        </dl>
      </header>

      <section className="market-band" aria-labelledby="market-title">
        <div className="section-kicker">
          <span>当前状态</span>
          <time dateTime={article.date}>{article.date}</time>
        </div>
        <h2 id="market-title">{marketTitle}</h2>
        <p>{snapshot.marketSummary}</p>
        <a href={article.url} target="_blank" rel="noreferrer">
          {article.title}
        </a>
      </section>

      <section className="radar-section" aria-labelledby="radar-title">
        <div className="section-heading">
          <div>
            <span className="section-kicker">当前鱼盆数据</span>
            <h2 id="radar-title">趋势方向雷达</h2>
          </div>
          <p>按优先级从左到右；分组表示趋势状态，动作单独判断。</p>
        </div>

        <div
          className={mainGroup?.directions.length ? "radar-grid" : "radar-grid has-empty-main"}
          data-testid="focus-groups"
        >
          {focusGroups.map((group) => (
            <section className={`radar-group group-${group.name}`} key={group.name}>
              <header>
                <h3>{group.name}</h3>
                <span>{GROUP_COPY[group.name]} · {group.directions.length} 个方向</span>
              </header>
              <div className="direction-list">
                {group.directions.length ? (
                  group.directions.map(renderDirection)
                ) : (
                  <p className="empty-group">暂无方向</p>
                )}
              </div>
            </section>
          ))}
        </div>

        {avoidGroup ? (
          <section className="avoid-group group-回避" data-testid="avoid-group">
            <header>
              <div>
                <h3>回避</h3>
                <span>{GROUP_COPY.回避} · {avoidGroup.directions.length} 个方向</span>
              </div>
              {avoidGroup.directions.length > AVOID_PREVIEW_COUNT ? (
                <button
                  type="button"
                  className="avoid-toggle"
                  aria-expanded={avoidExpanded}
                  aria-controls="avoid-direction-list"
                  onClick={() => setAvoidExpanded((value) => !value)}
                >
                  {avoidExpanded ? "收起回避清单" : `查看全部 ${avoidGroup.directions.length} 个`}
                </button>
              ) : null}
            </header>
            <div id="avoid-direction-list" className="direction-list avoid-list">
              {visibleAvoidDirections.map(renderDirection)}
            </div>
          </section>
        ) : null}
      </section>

      {selectedDirection ? (
        <section
          id="direction-detail"
          className="detail-section"
          data-testid="direction-detail"
          aria-labelledby="detail-title"
          aria-live="polite"
        >
          <div className="detail-main">
            <header className="detail-header">
              <div>
                <span className="section-kicker">
                  {selectedDirection.type === "sector" ? "板块方向" : "指数方向"} · {selectedDirection.dataDate}
                </span>
                <h2 id="detail-title">{selectedDirection.name}</h2>
              </div>
              <div className={`group-label label-${selectedDirection.group}`}>
                <strong>{selectedDirection.group}</strong>
                <span>{selectedDirection.action}</span>
              </div>
            </header>

            <dl className="metric-strip">
              <div>
                <dt>当前排名</dt>
                <dd>第 {selectedDirection.rank} 名</dd>
                {selectedDirection.previousDataDate && selectedDirection.rankMovement !== null ? (
                  <small>{formatRankMovement(selectedDirection)}</small>
                ) : null}
              </div>
              <div>
                <dt>20日线偏离</dt>
                <dd>{formatPercent(selectedDirection.deviationPct)}</dd>
              </div>
              <div>
                <dt>当日涨跌</dt>
                <dd>{formatPercent(selectedDirection.changePct)}</dd>
              </div>
              <div>
                <dt>比较基准</dt>
                <dd>{selectedDirection.benchmark}</dd>
              </div>
              <div>
                <dt>量能</dt>
                <dd>量比 {selectedDirection.volumeRatio.toFixed(2)}</dd>
              </div>
            </dl>

            <div className="evidence-matrix" aria-label="趋势条件证据">
              {Object.entries(CONDITION_COPY).map(([key, label]) => {
                const passed = selectedDirection.conditions[key];
                return (
                  <article className={passed ? "condition passed" : "condition pending"} key={key}>
                    <span>{label}</span>
                    <strong>{passed ? "通过" : "待确认"}</strong>
                    {key === "strongerThanBenchmark" ? (
                      <small>
                        {formatPercent(selectedDirection.changePct)} 对比 {formatPercent(selectedDirection.benchmarkChangePct)}
                      </small>
                    ) : null}
                  </article>
                );
              })}
            </div>

            <div className="interpretation-grid">
              <article>
                <span>文章态度</span>
                <strong>{STANCE_COPY[selectedDirection.articleStance]}</strong>
                <p>{selectedDirection.articleEvidence || "最新文章未提供该方向的独立逻辑。"}</p>
              </article>
              <article className="next-check">
                <span>下一次验证点</span>
                <p>{selectedDirection.nextValidation}</p>
              </article>
            </div>
          </div>

          <aside className="trace-panel" aria-label="原始证据和生命周期">
            <figure className="fish-figure">
              <img
                src={publicPath(selectedDirection.sourceImage)}
                alt={`${selectedDirection.type === "sector" ? "板块" : "指数"}鱼盆原始表格，${selectedDirection.name}在${selectedDirection.dataDate}排名第${selectedDirection.rank}，20日线偏离${formatPercent(selectedDirection.deviationPct)}，量比${selectedDirection.volumeRatio.toFixed(2)}`}
              />
              <figcaption>
                鱼盆原始表格 · 数据日 {selectedDirection.dataDate}
              </figcaption>
            </figure>

            <section className="lifecycle-block">
              <span className="section-kicker">信号生命周期</span>
              {selectedDirection.lifecycle ? (
                <dl>
                  <div>
                    <dt>开始</dt>
                    <dd>{selectedDirection.lifecycle.startDate}</dd>
                  </div>
                  <div>
                    <dt>首次主攻</dt>
                    <dd>{selectedDirection.lifecycle.mainDate || "尚未进入"}</dd>
                  </div>
                  <div>
                    <dt>观察次数</dt>
                    <dd>{selectedDirection.lifecycle.observations}</dd>
                  </div>
                  <div>
                    <dt>当前状态</dt>
                    <dd>{selectedDirection.lifecycle.status === "open" ? "进行中" : "已结束"}</dd>
                  </div>
                </dl>
              ) : (
                <p>尚未形成可记录的信号生命周期。</p>
              )}
            </section>

            <section className="history-block" data-testid="direction-history">
              <span className="section-kicker">排名与分组迁移</span>
              <h3>最近 5 次状态</h3>
              <ol>
                {selectedDirection.history.map((item) => (
                  <li key={item.date}>
                    <time dateTime={item.date}>{item.date}</time>
                    <strong>第 {item.rank} 名</strong>
                    <span className={`history-group history-${item.group}`}>{item.group}</span>
                  </li>
                ))}
              </ol>
            </section>
          </aside>
        </section>
      ) : null}

      <footer className="page-note">复盘动作，不构成投资建议。</footer>
    </main>
  );
}
