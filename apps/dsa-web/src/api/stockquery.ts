import apiClient from './index';
import { toCamelCase } from './utils';

// ============ API ============

import type {
  HistoryQueryItem,
} from '../types/stockquery';

export const stockqueryApi = {
  /**
   * Trigger backtest evaluation
   */
  stockquery: async (paramsType: string,strategy:string): Promise<HistoryQueryItem> => {
    // const requestData: Record<string, unknown> = {};
    // requestData.type = paramsType

    const responseData = await apiClient.post<Record<string, unknown>>(
      '/api/v1/stockquery/run',
      {
        paramType: paramsType,
        paramStrategy:strategy,
      },
    );

    // console.log(responseData.data)

    return toCamelCase<HistoryQueryItem>(responseData.data);
    // return responseData;
  },
  // querySentiment:async (): Promise<HistoryQueryItem> => {
  //   // const requestData: Record<string, unknown> = {};
  //   // const responseData = await apiClient.post<Record<string, unknown>>(
  //   //   '/api/v1/strategy/run',
  //   //   requestData,
  //   // );
  //   const responseData:HistoryQueryItem = {
  //       'id': 'Sentiment',
  //       'type': 'sentiment',
  //       'queryParams':
  //       {
  //           'stockCode':'000001'
  //       },
  //       'resultCount': '10',
  //       'createdAt':'20260331',
  //       'data':[{
  //           'stockName': '贵州茅台',
  //           'stockCode': '600159',
  //           'date': '20260313',
  //           }]
  //   }
  //   // return toCamelCase<HistoryQueryItem>(responseData.data);
  //   return responseData;
  // },
  // queryCombined:async (): Promise<HistoryQueryItem> => {
  //   // const requestData: Record<string, unknown> = {};
  //   // const responseData = await apiClient.post<Record<string, unknown>>(
  //   //   '/api/v1/strategy/run',
  //   //   requestData,
  //   // );
  //    const responseData:HistoryQueryItem = {
  //       'id': 'Combined',
  //       'type': 'combined',
  //       'queryParams':
  //       {
  //           'stockCode':'000001'
  //       },
  //       'resultCount': '10',
  //       'createdAt':'20260331',
  //       'data':[{
  //           'stockName': '贵州茅台',
  //           'stockCode': '600159',
  //           'date': '20260313',
  //           }]
  //   }
  //   // return toCamelCase<HistoryQueryItem>(responseData.data);
  //   return responseData;
  // },
};
