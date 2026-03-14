import apiClient from './index';
import { toCamelCase } from './utils';

// ============ API ============

import type {
  StrategyParamsRequest,
  StrategyResultResponse,
} from '../types/strategy';

export const strategyApi = {
  /**
   * Trigger backtest evaluation
   */
  run: async (params: StrategyParamsRequest): Promise<StrategyResultResponse> => {
    const requestData: Record<string, unknown> = {};
    requestData.code = params.code;
    requestData.maLongPeriod = params.maLongPeriod;
    requestData.maShortPeriod = params.maShortPeriod;
    requestData.overboughtThreshold = params.overboughtThreshold;
    requestData.oversoldThreshold = params.oversoldThreshold;
    requestData.rsiPeriod = params.rsiPeriod;
    requestData.stopLossPercent = params.stopLossPercent;
    requestData.takeProfitPercent = params.takeProfitPercent;
    requestData.volumePeriod = params.volumePeriod;

    if (params.code) console.log(requestData)
    const responseData = await apiClient.post<Record<string, unknown>>(
      '/api/v1/strategy/run',
      requestData,
    );
    // const responseData:StrategyResultResponse = {
    //     'code': '000001',
    //     'summary': 'report',
    //     'metrics':{
    //         'totalReturn': 50,
    //         'maxDrawdown': 25,
    //         'sharpeRatio': 30,
    //         'winRate':55
    //         },
    //     'chartUrl':'./images/demo.png'
    // }
    console.log(responseData.data)
    return toCamelCase<StrategyResultResponse>(responseData.data);
    //return responseData;
  },
};
