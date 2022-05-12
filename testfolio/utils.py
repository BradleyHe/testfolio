# Not intended for external use, only used internally
import numpy as np
from datetime import datetime


def _cagr(start_val, end_val, start_date, end_date):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return (end_val / start_val) ** (365 / (end - start).days) - 1


def _rebalance(prices, date, allocation):
    for ticker in allocation.keys():
        prices.at[date, ticker] = prices.at[date, 'Total'] * allocation[ticker]


def _sharpe(excess_return):
    mean_monthly_return = np.mean(excess_return)
    s = np.std(excess_return)
    monthly_sharpe = mean_monthly_return / s
    sharpe = monthly_sharpe * (12 ** 0.5)
    return sharpe


def _sortino(excess_return):
    temp = np.minimum(0, excess_return) ** 2
    temp_expectation = np.mean(temp)
    downside_dev = temp_expectation ** 0.5
    mean_monthly_return = np.mean(excess_return)
    monthly_sortino = mean_monthly_return / downside_dev
    sortino = monthly_sortino * (12 ** 0.5)
    return sortino
