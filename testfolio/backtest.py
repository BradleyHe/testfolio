import yfinance as yf
import pandas as pd
import numpy as np
from testfolio.utils import _cagr, _rebalance, _sharpe, _sortino

REBALANCE_INTERVALS = ('m', 'q', 'y', 'no')


class Backtest(object):
    _portfolio_num = 1

    def __init__(
            self,
            allocation=None,
            rebalance='y',
            start_date=None,
            end_date=None,
            start_val=1000,
            invest_dividends=True,
            name=None
    ) -> None:
        if sum(allocation.values()) != 1:
            raise ValueError('Allocation percentages must sum to 1.')

        if rebalance.lower() not in REBALANCE_INTERVALS:
            raise ValueError('Invalid rebalance interval. Valid intervals are m (monthly), q (quarterly), y (yearly), '
                             'no (no rebalancing).')

        if name:
            self.name = name
        else:
            self.name = f"Portfolio {Backtest._portfolio_num}"
        Backtest._portfolio_num += 1

        self.invest_dividends = invest_dividends
        self.allocation = allocation
        self.rebalance = rebalance.lower()
        self.start_val = start_val
        self.tickers = list(allocation.keys())

        # Limit start date to 1985-01-01 at the earliest (T-Bill info unavailable before then)
        if start_date:
            start_date = max(start_date, '1985-01-01')

        history = yf.download(self.tickers, interval='1mo', start=start_date, end=end_date, progress=False)
        prices = history['Adj Close' if invest_dividends else 'Close']

        if len(self.tickers) == 1:
            prices = prices.to_frame()
            prices = prices.set_axis(self.tickers, axis=1)

        # TODO: Check for any invalid tickers and raise error (column of all NaN)

        # Clear all NaN rows (dividend dates for 'Adj Close' and dates where a ticker did not exist yet)
        prices = prices.dropna()

        self.start_date = prices.index[0].strftime('%Y-%m-%d')
        self.end_date = prices.index[-1].strftime('%Y-%m-%d')

        # Divide each row by the one above it to find percent change
        daily_change = prices / prices.shift(1)

        # Initialize starting values
        portfolio_hist = pd.DataFrame(index=daily_change.index, columns=self.tickers + ['Total'])
        for ticker in self.tickers:
            portfolio_hist.at[self.start_date, ticker] = self.allocation[ticker] * self.start_val
        portfolio_hist.at[self.start_date, 'Total'] = self.start_val

        # Populate portfolio history
        prev_date = self.start_date
        for date, row in daily_change.iloc[1:].iterrows():
            for ticker in self.tickers:
                portfolio_hist.at[date, ticker] = portfolio_hist.at[prev_date, ticker] * row[ticker]
            portfolio_hist.at[date, 'Total'] = portfolio_hist.loc[date].sum()

            # Rebalancing
            if (self.rebalance == 'm' or
                    self.rebalance == 'q' and date.is_quarter_start or
                    self.rebalance == 'y' and date.is_year_start):
                _rebalance(portfolio_hist, date, self.allocation)

            prev_date = date

        self.portfolio_hist = portfolio_hist
        self.end_val = portfolio_hist.loc[self.end_date]['Total']
        self.cagr = _cagr(self.start_val, self.end_val, self.start_date, self.end_date)
        self.std = np.std(portfolio_hist['Total'].pct_change().dropna()) * (12 ** 0.5)

        # Calculate excess return using 3-month T BILL as risk-free return
        tbill_return = yf.download('^IRX', interval='1mo', start=self.start_date, end=self.end_date,
                                   progress=False)['Close'] * 0.01 / 12  # Don't forget to convert to monthly rate
        portfolio_return = portfolio_hist['Total'].pct_change()
        excess_return = (portfolio_return - tbill_return).dropna()
        self.sharpe = _sharpe(excess_return)
        self.sortino = _sortino(excess_return)


    def __str__(self):
        return (
            f'Name: {self.name}\n'
            f'Allocation: {self.allocation}\n'
            f'Starting Value: ${self.start_val:.2f}\n'
            f'Ending Value: ${self.end_val:.2f}\n'
            f'Start Date: {self.start_date}\n'
            f'End Date: {self.end_date}\n'
            f'CAGR: {self.cagr:.2%}\n'
            f'STD (annularized): {self.std:.2%}\n'
            f'Sharpe Ratio: {self.sharpe:.2f}\n'
            f'Sortino Ratio: {self.sortino:.2f}'
        )
