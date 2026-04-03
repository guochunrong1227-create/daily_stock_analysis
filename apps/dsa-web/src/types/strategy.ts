// ============ 策略Request / Response ============
export interface StrategyParamsRequest {
    code: string;
    rsiPeriod: number;
    maShortPeriod: number;
    maLongPeriod: number;
    volumePeriod: number;
    overboughtThreshold: number;
    oversoldThreshold: number;
    stopLossPercent: number;
    takeProfitPercent: number;
}

export interface Metrics {
    totalReturn: number;
    winRate: number;
    maxDrawdown: number;
    sharpeRatio: number;
}
export interface StrategyResultResponse {
    code:string;
    summary: string;
    metrics: Metrics;
    chartUrl: string; // 假设后端返回图片URL
    bestStrategyDescription:string;
}
