
// --- 类型定义 ---
/** 单条股票数据（网格行） */
export interface StockRow {
  stockName: string;
  stockCode: string;
  date: string;           // 格式 YYYY-MM-DD
  [key: string]: any;     // 其他可能的字段
}

/** 历史查询记录项 */
export interface HistoryQueryItem {
  id: string;                // 唯一ID，可用 Date.now() 拼上随机数
  type: 'fundamental' | 'sentiment' | 'combined';
  downloadURL: string;
  // queryParams: {
  //   stockCode?: string;       // 查询时输入的股票代码（可为空，代表全市场）
  // };
  resultCount: string;
  createAt: string;          // ISO 字符串
  data: StockRow[];           // 当前记录对应的完整网格数据
}
