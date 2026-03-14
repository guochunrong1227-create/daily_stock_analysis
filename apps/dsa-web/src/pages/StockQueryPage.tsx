import type React from 'react';
import { useState, useEffect,useCallback } from 'react';
import { ApiErrorAlert } from '../components/common';
import { getParsedApiError } from '../api/error';
import {stockqueryApi} from '../api/stockquery';

import type {
    StockRow,
    HistoryQueryItem,
} from '../types/stockquery'

// --- 模拟数据生成工具 (仅用于演示，实际使用时替换为 API 调用) ---
// const generateMockRows = (type: 'fundamental' | 'sentiment' | 'combined', stockCode?: string): StockRow[] => {
//   const count = Math.floor(Math.random() * 5) + 3; // 3~7 条
//   const baseDate = new Date().toISOString().slice(0, 10);
//   const rows: StockRow[] = [];
//   const stocks = stockCode
//     ? [{ name: `示例${stockCode}`, code: stockCode }]
//     : [
//         { name: '贵州茅台', code: '600519' },
//         { name: '腾讯控股', code: '00700' },
//         { name: '苹果', code: 'AAPL' },
//         { name: '阿里巴巴', code: 'BABA' },
//       ];

//   for (let i = 0; i < count; i++) {
//     const stock = stocks[i % stocks.length];
//     rows.push({
//       stockName: stock.name,
//       stockCode: stock.code,
//       date: baseDate,
//       // 根据不同查询类型可附加不同字段，但网格只展示上述三列
//       ...(type === 'fundamental' ? { pe: (Math.random() * 30).toFixed(2) } : {}),
//       ...(type === 'sentiment' ? { hotness: Math.floor(Math.random() * 100) } : {}),
//     });
//   }
//   return rows;
// };

/**
 * 股票查询页面 - 模仿首页样式
 * 左侧：三个独立的历史列表（基本面、人气、综合）
 * 右侧：顶部查询按钮 + 底部网格结果
 */
const StockQueryPage: React.FC = () => {
  // --- 本地错误状态（可复用原 store 风格，此处独立管理）---
  const [error, setError] = useState<any>(null);

  // --- 查询输入 ---
  const [stockCodeInput, setStockCodeInput] = useState('');
  const [inputError, setInputError] = useState<string>();

  // --- 按钮加载状态 ---
  const [queryingFundamental, setQueryingFundamental] = useState(false);
  const [queryingSentiment, setQueryingSentiment] = useState(false);
  const [queryingCombined, setQueryingCombined] = useState(false);

  // --- 左侧三个历史列表数据 ---
  const [fundamentalHistory, setFundamentalHistory] = useState<HistoryQueryItem[]>([]);
  const [sentimentHistory, setSentimentHistory] = useState<HistoryQueryItem[]>([]);
  const [combinedHistory, setCombinedHistory] = useState<HistoryQueryItem[]>([]);

  // 各列表加载状态（初次加载模拟）
  const [loadingFundamental, setLoadingFundamental] = useState(false);
  const [loadingSentiment, setLoadingSentiment] = useState(false);
  const [loadingCombined, setLoadingCombined] = useState(false);

  // 是否有更多数据（为了演示设为 true 但不再加载更多，可留作扩展）
  const [hasMoreFundamental] = useState(true);
  const [hasMoreSentiment] = useState(true);
  const [hasMoreCombined] = useState(true);

  // --- 当前选中的历史项（用于高亮和右侧展示）---
  const [selectedItem, setSelectedItem] = useState<{ type: HistoryQueryItem['type']; id: string} | null>(null);

  // --- 右侧网格数据 ---
  const [gridData, setGridData] = useState<StockRow[]>([]);
  const [gridLoading, setGridLoading] = useState(false); // 点击历史或查询时加载

  // --- 移动端侧边栏控制 ---
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // --- 初始加载模拟历史数据 (仅首次) ---
  useEffect(() => {
    const loadInitialHistory = async () => {
      setLoadingFundamental(true);
      setLoadingSentiment(true);
      setLoadingCombined(true);
      try {
        // 模拟接口调用：这里用注释表示实际 API
        // const fundamentalRes = await historyApi.getFundamentalList();
        // const sentimentRes = await historyApi.getSentimentList();
        // const combinedRes = await historyApi.getCombinedList();

        // 模拟数据
        // const mockFundamental: HistoryQueryItem[] = [
        //   {
        //     id: 'f1',
        //     type: 'fundamental',
        //     queryParams: { stockCode: '600519' },
        //     resultCount: '5',
        //     createdAt: new Date(Date.now() - 86400000).toISOString(),
        //     data: generateMockRows('fundamental', '600519'),
        //   },
          // {
          //   id: 'f2',
          //   type: 'fundamental',
          //   queryParams: {},
          //   resultCount: '8',
          //   createdAt: new Date(Date.now() - 172800000).toISOString(),
          //   data: generateMockRows('fundamental'),
          // },
        // ];
        // const mockSentiment: HistoryQueryItem[] = [
        //   {
        //     id: 's1',
        //     type: 'sentiment',
        //     queryParams: { stockCode: '00700' },
        //     resultCount: '6',
        //     createdAt: new Date(Date.now() - 86400000).toISOString(),
        //     data: generateMockRows('sentiment', '00700'),
        //   },
        // ];
        // const mockCombined: HistoryQueryItem[] = [
        //   {
        //     id: 'c1',
        //     type: 'combined',
        //     queryParams: {},
        //     resultCount: '10',
        //     createdAt: new Date(Date.now() - 86400000).toISOString(),
        //     data: generateMockRows('combined'),
        //   },
        // ];

        // setFundamentalHistory(mockFundamental);
        // setSentimentHistory(mockSentiment);
        // setCombinedHistory(mockCombined);
      } catch (err) {
        setError(getParsedApiError(err));
      } finally {
        setLoadingFundamental(false);
        setLoadingSentiment(false);
        setLoadingCombined(false);
      }
    };

    loadInitialHistory();
  }, []);

  // --- 通用的查询执行函数 ---
  const executeQuery = useCallback(async (
    type: 'fundamental' | 'sentiment' | 'combined',
    setLoading: (val: boolean) => void
  ) => {
    // 简单校验股票代码（非必须）
    if (stockCodeInput) {
      // 可调用原项目中的 validateStockCode，这里简单只允许字母数字点
      const isValid = /^[A-Za-z0-9.]{1,20}$/.test(stockCodeInput);
      if (!isValid) {
        setInputError('股票代码格式不正确');
        return;
      }
    }
    setInputError(undefined);
    setLoading(true);
    setError(null);

    try {
      // --- API 调用示例 (注释保留) ---
      let response;
      if (type === 'fundamental') {
        response = await stockqueryApi.stockquery('fundamental');
      } else if (type === 'sentiment') {
        response = await stockqueryApi.stockquery('sentiment');
      } else {
        response = await stockqueryApi.stockquery('combined');
        // response = await stockqueryApi.queryCombined({ stockCode: stockCodeInput || undefined });
      }
      console.log(response.createAt)
      console.log(response)
      const rows = response.data as StockRow[];

    //   // 模拟调用延迟
    //   await new Promise((resolve) => setTimeout(resolve, 800));
    //   const rows = generateMockRows(type, stockCodeInput || undefined);

      // 构建历史记录项
    //   const newItem: HistoryQueryItem = {
    //     id: `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
    //     type,
    //     queryParams: { stockCode: stockCodeInput || undefined },
    //     resultCount: rows.length,
    //     createdAt: new Date().toISOString(),
    //     data: rows,
    //   };

       const newItem: HistoryQueryItem = {
        id: response.id,
        type: response.type,
        queryParams: response.queryParams,
        resultCount: response.resultCount,
        createAt: response.createAt,
        data: rows,
      };

      // 更新对应历史列表（新记录插入顶部）
      if (type === 'fundamental') {
        setFundamentalHistory((prev) => [newItem, ...prev]);
      } else if (type === 'sentiment') {
        setSentimentHistory((prev) => [newItem, ...prev]);
      } else {
        setCombinedHistory((prev) => [newItem, ...prev]);
      }

      // 更新右侧网格数据并选中当前项
      setGridData(rows);
      setSelectedItem({ type, id: newItem.id});
    } catch (err) {
      console.error(`${type} query failed:`, err);
      setError(getParsedApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  // --- 点击历史记录项 ---
  const handleHistoryClick = (item: HistoryQueryItem) => {
    // 模拟可能存在的详情API调用 (注释示例)
    // if (item.type === 'fundamental') {
    //   const detail = await fundamentalApi.getDetail(item.id);
    //   setGridData(detail.rows);
    // } else ...

    setGridLoading(true);
    // 直接使用item中存储的数据（实际项目可能是懒加载，此处模拟立即展示）
    setTimeout(() => {
      setGridData(item.data);
      setSelectedItem({ type: item.type, id: item.id});
      setGridLoading(false);
      setSidebarOpen(false); // 移动端点击后关闭侧边栏
    }, 100);
  };

  // --- 加载更多 (仅为占位，演示中无更多操作) ---
  const handleLoadMoreFundamental = () => {};
  const handleLoadMoreSentiment = () => {};
  const handleLoadMoreCombined = () => {};

  // --- 渲染单个历史列表 (复用原HistoryList样式思路) ---
  const renderHistoryList = (
    title: string,
    items: HistoryQueryItem[],
    loading: boolean,
    hasMore: boolean,
    onLoadMore: () => void
    // ,
    // type: HistoryQueryItem['type']
  ) => (
    <div className="flex flex-col flex-1 min-h-0 mb-2 last:mb-0">
      <h3 className="text-sm font-bold text-secondary mb-1 px-1">{title}</h3>
      <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin scrollbar-thumb-white/10">
        {items.length === 0 && !loading ? (
          <div className="text-center text-muted text-xs py-4">暂无记录</div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              onClick={() => handleHistoryClick(item)}
              className={`
                p-2 rounded border cursor-pointer transition-colors
                ${selectedItem?.type === item.type && selectedItem?.id === item.id
                  ? 'border-cyan/40 bg-cyan/10'
                  : 'border-white/5 hover:bg-white/5'
                }
              `}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium truncate text-white">
                  {item.id || '全市场'}
                </span>
                <span className="text-2xs text-muted ml-2">{item.resultCount}只</span>
              </div>
              <div className="flex items-center justify-between mt-0.5">
                <span className="text-2xs text-secondary">
                  {new Date(item.createAt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="text-2xs text-muted">
                  {item.type === 'fundamental' ? '财务' : item.type === 'sentiment' ? '人气' : '综合'}
                </span>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-center py-2">
            <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
          </div>
        )}
        {/* 简易加载更多触发器 (未实现真实加载) */}
        {hasMore && !loading && items.length > 0 && (
          <button
            onClick={onLoadMore}
            className="w-full text-center text-2xs text-muted hover:text-secondary py-1"
          >
            加载更多
          </button>
        )}
      </div>
    </div>
  );

  // --- 右侧网格组件 (Excel风格) ---
  const renderGrid = () => (
    <div className="border border-white/10 rounded-lg overflow-hidden bg-elevated/50">
      {gridLoading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-6 h-6 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      ) : gridData.length > 0 ? (
        <div className="overflow-auto max-h-150">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-black/20">
                <th className="px-3 py-2 text-left font-medium text-secondary">股票名称</th>
                <th className="px-3 py-2 text-left font-medium text-secondary">代码</th>
                <th className="px-3 py-2 text-left font-medium text-secondary">日期</th>
                {/* 可扩展其他字段，但只展示这三列 */}
              </tr>
            </thead>
            <tbody>
              {gridData.map((row, idx) => (
                <tr key={idx} className="border-b border-white/5 last:border-0 hover:bg-white/5">
                  <td className="px-3 py-2 text-white">{row.stockName}</td>
                  <td className="px-3 py-2 text-secondary font-mono">{row.stockCode}</td>
                  <td className="px-3 py-2 text-secondary">{row.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-48 text-center">
          <div className="w-8 h-8 mb-2 rounded-lg bg-elevated flex items-center justify-center">
            <svg className="w-4 h-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
          </div>
          <p className="text-xs text-muted">点击查询或选择左侧历史记录</p>
        </div>
      )}
    </div>
  );

  // --- 侧边栏内容 (左侧三个列表) ---
  const sidebarContent = (
    <div className="flex flex-col gap-2 overflow-hidden min-h-0 h-full">
      {renderHistoryList('财务指标', fundamentalHistory, loadingFundamental, hasMoreFundamental, handleLoadMoreFundamental)}
      {renderHistoryList('市场人气', sentimentHistory, loadingSentiment, hasMoreSentiment, handleLoadMoreSentiment)}
      {renderHistoryList('综合选股', combinedHistory, loadingCombined, hasMoreCombined, handleLoadMoreCombined)}
    </div>
  );

  return (
    <div
      className="min-h-screen flex flex-col md:grid overflow-hidden w-full"
      style={{ gridTemplateColumns: 'minmax(12px, 1fr) 320px 24px minmax(auto, 800px) minmax(12px, 1fr)', gridTemplateRows: 'auto 1fr' }}
    >
      {/* 顶部操作栏 */}
      <header className="md:col-start-2 md:col-end-5 md:row-start-1 py-3 px-3 md:px-0 border-b border-white/5 flex-shrink-0 flex items-center min-w-0 overflow-hidden">
        <div className="flex items-center gap-2 w-full min-w-0 flex-1 flex-wrap" style={{ maxWidth: 'min(100%, 1144px)' }}>
          {/* 移动端汉堡菜单 */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 -ml-1 rounded-lg hover:bg-white/10 transition-colors text-secondary hover:text-white flex-shrink-0"
            title="历史记录"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* 股票代码输入 */}
          <div className="relative flex-1 min-w-[120px]">
            <input
              type="text"
              value={stockCodeInput}
              onChange={(e) => {
                setStockCodeInput(e.target.value.toUpperCase());
                setInputError(undefined);
              }}
              placeholder="股票代码 (可选)"
              className="input-terminal w-full text-sm"
            />
            {inputError && (
              <p className="absolute -bottom-4 left-0 text-xs text-danger">{inputError}</p>
            )}
          </div>

          {/* 三个查询按钮 */}
          <button
            onClick={() => executeQuery('fundamental', setQueryingFundamental)}
            disabled={queryingFundamental}
            className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1"
          >
            {queryingFundamental ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
            财务指标
          </button>
          <button
            onClick={() => executeQuery('sentiment', setQueryingSentiment)}
            disabled={queryingSentiment}
            className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1"
          >
            {queryingSentiment ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
            择时人气
          </button>
          <button
            onClick={() => executeQuery('combined', setQueryingCombined)}
            disabled={queryingCombined}
            className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1"
          >
            {queryingCombined ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
            择时综合
          </button>
        </div>
      </header>

      {/* 桌面左侧边栏 */}
      <div className="hidden md:flex col-start-2 row-start-2 flex-col overflow-hidden min-h-0">
        {sidebarContent}
      </div>

      {/* 移动端侧边栏 */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setSidebarOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="absolute left-0 top-0 bottom-0 w-72 flex flex-col glass-card overflow-hidden border-r border-white/10 shadow-2xl p-3"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </div>
        </div>
      )}

      {/* 右侧内容区 */}
      <section className="md:col-start-4 md:row-start-2 flex-1 overflow-y-scroll overflow-x-hidden px-3 md:px-0 md:pl-1 min-w-0 min-h-0 max-h-full">
        {error && <ApiErrorAlert error={error} className="mb-3" />}

        {/* 结果网格 */}
        {renderGrid()}
      </section>
    </div>
  );
};

export default StockQueryPage;