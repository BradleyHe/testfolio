# Not intended for external use, only used internally
import numpy as np
import pandas as pd
from datetime import datetime


def _cagr(start_val, end_val, start_date, end_date):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return (end_val / start_val) ** (365 / (end - start).days) - 1


def _rebalance(prices, date, allocation):
    for ticker in allocation.keys():
        prices.at[date, ticker] = prices.at[date, 'Total'] * allocation[ticker]


def _sharpe(excess_return):
    mean_daily_return = np.mean(excess_return)
    s = np.std(excess_return)
    daily_sharpe = mean_daily_return / s
    sharpe = daily_sharpe * (252 ** 0.5)
    return sharpe


def _sortino(excess_return):
    temp = np.minimum(0, excess_return) ** 2
    temp_expectation = np.mean(temp)
    downside_dev = temp_expectation ** 0.5
    mean_daily_return = np.mean(excess_return)
    daily_sortino = mean_daily_return / downside_dev
    sortino = daily_sortino * (252 ** 0.5)
    return sortino


def _interpolate_inflation(dates, inflation):
    # Convert daily inflation figures to daily using linear interpolation (should be a good enough approximation)
    daily_inflation = pd.DataFrame()
    daily_inflation.index = pd.date_range(start=inflation.index[0], end=inflation.index[-1])
    daily_inflation = pd.concat([daily_inflation, inflation], join='outer', axis=1)
    daily_inflation['CPIAUCSL'] = daily_inflation['CPIAUCSL'].interpolate(method='linear')
    daily_inflation = daily_inflation[daily_inflation.index.isin(dates)]
    return daily_inflation


def _is_rebalance_date(prev_date, curr_date, interval):
    if interval == 'd':
        return True
    elif interval == 'w':
        return prev_date.isocalendar().week != curr_date.isocalendar().week
    elif interval == 'm':
        return prev_date.month != curr_date.month
    elif interval == 'q':
        return prev_date.quarter != curr_date.quarter
    elif interval == 'y':
        return prev_date.year != curr_date.year
    elif interval == 'no':
        return False
