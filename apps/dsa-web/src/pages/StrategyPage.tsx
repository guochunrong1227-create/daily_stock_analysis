import type React from 'react';
import { useState, useCallback } from 'react';
import { strategyApi } from '../api/strategy'; // 假设的策略API
import { Card, } from '../components/common';

import type {
  StrategyParamsRequest,
  StrategyResultResponse,
} from '../types/strategy';


// ============ 主页面组件 ============
const StrategyPage: React.FC = () => {
  // 策略参数状态
  const [params, setParams] = useState<StrategyParamsRequest>({
    code: '000001',
    rsiPeriod: 14,
    maShortPeriod: 5,
    maLongPeriod: 20,
    volumePeriod: 20,
    overboughtThreshold: 70,
    oversoldThreshold: 30,
    stopLossPercent: 5.0,
    takeProfitPercent: 10.0,
  });

  // 股票代码状态
  const [code, setCode] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StrategyResultResponse | null>(null);

  // 处理参数输入变化
  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setParams((prev) => ({
      ...prev,
      [name]: value === '' ? '' : Number(value), // 允许清空，但最终会转为数字
    }));
  };

  // 执行策略
  const handleRunStrategy = useCallback(async () => {
    if (!code.trim()) {
      setError('请输入股票代码');
      return;
    }

    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      // 调用策略API（需根据实际后端调整）
      const response = await strategyApi.run(
        {
          code: code.trim().toUpperCase(),
          // 确保数字类型有效
          rsiPeriod: Number(params.rsiPeriod) || 14,
          maShortPeriod: Number(params.maShortPeriod) || 5,
          maLongPeriod: Number(params.maLongPeriod) || 20,
          volumePeriod: Number(params.volumePeriod) || 20,
          overboughtThreshold: Number(params.overboughtThreshold) || 70,
          oversoldThreshold: Number(params.oversoldThreshold) || 30,
          stopLossPercent: Number(params.stopLossPercent) || 5,
          takeProfitPercent: Number(params.takeProfitPercent) || 10,
        }
      );

      console.log(response.metrics.totalReturn)
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : '策略执行失败');
    } finally {
      setIsRunning(false);
    }
  }, [code, params]);

  // 键盘提交
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isRunning) {
      handleRunStrategy();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 第一部分：策略参数填写 */}
      <header className="flex-shrink-0 px-4 py-3 border-b border-white/5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 max-w-4xl">
          {/* RSI周期 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>RSI周期</label>
            <input
              type="number"
              name="rsiPeriod"
              value={params.rsiPeriod}
              onChange={handleParamChange}
              min={2}
              max={50}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 短期均线 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>短期均线</label>
            <input
              type="number"
              name="maShortPeriod"
              value={params.maShortPeriod}
              onChange={handleParamChange}
              min={2}
              max={50}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 长期均线 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>长期均线</label>
            <input
              type="number"
              name="maLongPeriod"
              value={params.maLongPeriod}
              onChange={handleParamChange}
              min={5}
              max={200}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 量能周期 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>量能周期</label>
            <input
              type="number"
              name="volumePeriod"
              value={params.volumePeriod}
              onChange={handleParamChange}
              min={5}
              max={100}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 超买阈值 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>超买阈值</label>
            <input
              type="number"
              name="overboughtThreshold"
              value={params.overboughtThreshold}
              onChange={handleParamChange}
              min={50}
              max={90}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 超卖阈值 */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>超卖阈值</label>
            <input
              type="number"
              name="oversoldThreshold"
              value={params.oversoldThreshold}
              onChange={handleParamChange}
              min={10}
              max={50}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 止损% */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>止损%</label>
            <input
              type="number"
              name="stopLossPercent"
              value={params.stopLossPercent}
              onChange={handleParamChange}
              min={0.1}
              max={20}
              step={0.1}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 止盈% */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>止盈%</label>
            <input
              type="number"
              name="takeProfitPercent"
              value={params.takeProfitPercent}
              onChange={handleParamChange}
              min={0.1}
              max={50}
              step={0.1}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 默认手数% */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>默认手数</label>
            <input
              type="number"
              name="defaultRoundLot "
              value={params.stopLossPercent}
              onChange={handleParamChange}
              min={0.1}
              max={20}
              step={0.1}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
          {/* 回撤天数% */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted" style={{color: 'white'}}>回测天数</label>
            <input
              type="number"
              name="backtestDays"
              value={params.takeProfitPercent}
              onChange={handleParamChange}
              min={0.1}
              max={50}
              step={0.1}
              className="input-terminal w-full"
              disabled={isRunning}
            />
          </div>
        </div>
      </header>

      {/* 第二部分：股票代码输入和提交 */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2 max-w-4xl">
          <div className="flex-1 relative">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              placeholder="输入股票代码，如 000001"
              disabled={isRunning}
              className="input-terminal w-full"
            />
          </div>
          <button
            type="button"
            onClick={handleRunStrategy}
            disabled={isRunning}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {isRunning ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                执行中...
              </>
            ) : (
              '执行策略'
            )}
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-danger">{error}</p>}
      </div>

      {/* 第三部分：结果展示 */}
      <main className="flex-1 overflow-y-auto p-3">
        {result ? (
          <div className="space-y-3 animate-fade-in">
            {/* 上半部分：文字结果 */}
            <Card variant="gradient" padding="md">
              <h3 className="label-uppercase mb-3">执行结果摘要</h3>
              <div className="grid grid-cols-2 gap-4">
                {/* 左侧列 */}
                <div className="flex flex-col gap-4">
                  {/* 上半部分：两个指标组（原第一列+第二列）并列 */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* 原第一列：总回报 + 胜率 */}
                    <div>
                      <div>
                        <p className="text-xs text-muted mb-1">总回报</p>
                        <p className={`text-base font-mono font-semibold ${result.metrics.totalReturn >= 0.0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {result.metrics.totalReturn}
                        </p>
                      </div>
                      <div className="mt-2">
                        <p className="text-xs text-muted mb-1">胜率</p>
                        <p className="text-base font-mono font-semibold text-cyan">
                          {result.metrics.winRate.toFixed(1)}%
                        </p>
                      </div>
                    </div>

                    {/* 原第二列：最大回撤 + 夏普比率 */}
                    <div>
                      <div>
                        <p className="text-xs text-muted mb-1">最大回撤</p>
                        <p className="text-base font-mono font-semibold text-amber-400">
                          {result.metrics.maxDrawdown.toFixed(2)}%
                        </p>
                      </div>
                      <div className="mt-2">
                        <p className="text-xs text-muted mb-1">夏普比率</p>
                        <p className="text-base font-mono font-semibold text-white">
                          {result.metrics.sharpeRatio.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                  {/* 下半部分：summary 链接列表 */}
                  <div className="p-2 bg-elevated/50 rounded border border-white/5">
                    {(() => {
                      const urls = result.summary.split(',');
                      return (
                        <>
                          {urls[0] && (
                            <div className="text-base text-white">
                              <a href={urls[0]} target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-400">
                                仪表盘
                              </a>
                            </div>
                          )}
                          {urls[1] && (
                            <div className="text-base text-white mt-1">
                              <a href={urls[1]} target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-400">
                                报告
                              </a>
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </div>

                {/* 右侧列：历史最佳策略描述 */}
                <div>
                  <p className="text-xs text-muted mb-1">历史最佳操作策略</p>
                  <p
                      className="text-base font-mono text-white break-words"
                      dangerouslySetInnerHTML={{ __html: result.bestStrategyDescription || '双均线策略' }}
                    />
                </div>
              </div>
            </Card>

            {/* 下半部分：图片结果 */}
            <Card variant="default" padding="md" className="flex flex-col items-center">
              <h3 className="label-uppercase w-full mb-3">策略回测图表</h3>
              {result.chartUrl ? (
                <img
                  src={result.chartUrl}
                  alt="策略回测图表"
                  className="max-w-full h-auto rounded-lg border border-white/5"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              ) : (
                <div className="py-8 text-center text-muted">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p>暂无图表数据</p>
                </div>
              )}
            </Card>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-12 h-12 mb-3 rounded-xl bg-elevated flex items-center justify-center">
              <svg className="w-6 h-6 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-base font-medium text-white mb-1.5">等待策略执行</h3>
            <p className="text-xs text-muted max-w-xs">
              输入股票代码并点击执行按钮，查看策略回测结果
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default StrategyPage;