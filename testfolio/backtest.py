import yfinance as yf
import pandas as pd
import numpy as np
import pandas_datareader.data as web
from testfolio.utils import _cagr, _rebalance, _sharpe, _sortino

REBALANCE_INTERVALS = ('m', 'q', 'y', 'no')
ALIAS_TO_TICKER = {
    'S&P 500': 'VFINX',
    'Long Term Treasury': 'VUSTX',
    'Total US Bond Market': 'VBMFX',
    'Total US Stock Market': 'VTSMX',
    'Total Intl Stock Market': 'VGTSX',
    'Gold': 'GC=F',
    'Intermediate Term Treasury': 'IEF',
    'Short Term Treasury': 'VFISX',
    'REIT': 'VGSIX',
    'US Small Cap': 'NAESX',
    'US Mid Cap': 'VMCIX'
}


class Backtest(object):
    """The base class for a backtest.

    Given an asset allocation, it will download historical data from Yahoo Finance and calculate its return
    over a time period. CAGR, Sharpe ratio, and Sortino ratios are calculated across the duration of the backtest.

    Attributes:
        name: Name of the portfolio. Defaults to "Portfolio n" where n is the nth portfolio made if not specified.
        invest_dividends: Indicates if the backtests reinvests dividends across the backtest.
        allocation: Dictionary containing str: float pairs that assign a ticker to its allocation within the portfolio.
                    All portfolio allocations must sum to 1. 
        rebalance: String indicating the rebalancing frequency of the portfolio. Must be in REBALANCE_INTERVALS.
        start_val: Starting value of the portfolio. Defaults to 1000 if not specified.
        tickers: List of strings containing tickers in the backtest.
        adj_inflation: True if prices are adjusted for inflation relative to start_date, False if prices are nominal
            NOTE - Inflation data may not be available for the most recent month, in which case there will be no
            adjustment for the most recent data point.
        start_date: String representing the start date of the backtest. Defaults to the earliest possible date for which
                    data for all tickers is available, if not specified.
        end_date: Ending date of the backtest. Defaults to today if not specified
        hist: DataFrame containing the value of the portfolio every month. Columns include each of the
                        tickers, the total portfolio value, and drawdown.
        max_drawdown: Maximum drawdown of the portfolio.
        end_val: Ending value of the portfolio.
        cagr: Compound annual growth rate of the portfolio.
        std: Annualized standard deviation of returns.
        sharpe: Sharpe ratio calculated using the 3-month T-Bill as the risk-free return.
        sortino: Sortino ratio calculated using the 3-month T-Bill as the risk-free return.
        correlation: Pearson correlation coefficient to the S&P 500 over the time period.
    """

    _portfolio_num = 1

    def __init__(
            self,
            allocation,
            rebalance='q',
            start_date=None,
            end_date=None,
            start_val=1000,
            invest_dividends=True,
            name=None,
            adj_inflation=False
    ) -> None:
        if abs(sum(allocation.values()) - 1) >= 1e-6:
            raise ValueError('Allocation percentages must sum to 1.')

        if rebalance.lower() not in REBALANCE_INTERVALS:
            raise ValueError('Invalid rebalance interval. Valid intervals are m (monthly), q (quarterly), y (yearly), '
                             'no (no rebalancing).')

        if name:
            self.name = name
        else:
            self.name = f"Portfolio {Backtest._portfolio_num}"
        Backtest._portfolio_num += 1

        allocation = {(ticker.upper() if ticker not in ALIAS_TO_TICKER else
                       ALIAS_TO_TICKER[ticker]): pct for ticker, pct in allocation.items()}

        self.invest_dividends = invest_dividends
        self.allocation = allocation
        self.rebalance = rebalance.lower()
        self.start_val = start_val
        self.tickers = list(allocation.keys())
        self.adj_inflation = adj_inflation

        # Limit start date to 1985-01-01 at the earliest (T-Bill info unavailable before then)
        if start_date:
            start_date = max(start_date, '1985-01-01')

        history = yf.download(self.tickers, interval='1mo', start=start_date, end=end_date, progress=False)
        prices = history['Adj Close' if invest_dividends else 'Close']

        if len(self.tickers) == 1:
            prices = prices.to_frame()
            prices = prices.set_axis(self.tickers, axis=1)

        # Check for invalid tickers
        for ticker in self.tickers:
            if prices[ticker].isnull().all():
                raise ValueError(f'Ticker {ticker} does not exist.')

        # Clear all NaN rows (dividend dates for 'Adj Close' and dates where a ticker did not exist yet)
        prices = prices.dropna()

        self.start_date = prices.index[0].strftime('%Y-%m-%d')
        self.end_date = prices.index[-1].strftime('%Y-%m-%d')

        if self.start_date >= self.end_date:
            raise ValueError('Time between start date and end date must be more than 1 month.')

        # Divide each row by the one above it to find percent change
        monthly_change = prices / prices.shift(1)

        # Initialize starting values
        hist = pd.DataFrame(index=monthly_change.index, columns=self.tickers + ['Total', 'Drawdown'])
        for ticker in self.tickers:
            hist.at[self.start_date, ticker] = self.allocation[ticker] * self.start_val
        hist.at[self.start_date, 'Total'] = self.start_val
        hist.at[self.start_date, 'Drawdown'] = 0

        # Download inflation data if necessary
        inflation = web.DataReader('CPIAUCSL', 'fred', self.start_date, self.end_date) if adj_inflation else None

        # Populate portfolio history
        prev_date = self.start_date
        max_total = self.start_val
        for date, row in monthly_change.iloc[1:].iterrows():
            for ticker in self.tickers:
                hist.at[date, ticker] = hist.at[prev_date, ticker] * row[ticker]

                # Adjust for inflation if necessary
                if adj_inflation and date in inflation.index:
                    hist.at[date, ticker] *= inflation.at[prev_date, 'CPIAUCSL'] / inflation.at[date, 'CPIAUCSL']

            hist.at[date, 'Total'] = hist.loc[date].sum()

            # Rebalancing
            if (self.rebalance == 'm' or
                    self.rebalance == 'q' and date.is_quarter_start or
                    self.rebalance == 'y' and date.is_year_start):
                _rebalance(hist, date, self.allocation)

            # Drawdowns
            if hist.at[date, 'Total'] >= max_total:
                hist.at[date, 'Drawdown'] = 0
                max_total = hist.at[date, 'Total']
            else:
                hist.at[date, 'Drawdown'] = (hist.at[date, 'Total'] - max_total) / max_total

            prev_date = date

        self.hist = hist
        self.max_drawdown = min(hist['Drawdown'])
        self.end_val = hist.loc[self.end_date]['Total']
        self.cagr = _cagr(self.start_val, self.end_val, self.start_date, self.end_date)
        self.std = np.std(hist['Total'].pct_change().dropna()) * (12 ** 0.5)

        # Calculate excess return using 3-month T-Bill as risk-free return
        tbill_return = yf.download('^IRX', interval='1mo', start=self.start_date, end=self.end_date,
                                   progress=False)['Close'] * 0.01 / 12  # Don't forget to convert to monthly rate
        if adj_inflation:
            tbill_return -= inflation['CPIAUCSL'].pct_change()

        portfolio_return = hist['Total'].pct_change().dropna()
        excess_return = (portfolio_return - tbill_return).dropna()
        self.sharpe = _sharpe(excess_return)
        self.sortino = _sortino(excess_return)

        # Calculate market correlation using S&P 500
        market_history = yf.download('VFINX', interval='1mo', start=self.start_date,
                                     progress=False)['Adj Close'].dropna().pct_change().dropna()
        df = pd.concat([portfolio_return, market_history], axis=1)
        self.correlation = df.corr().iloc[1][0]


    def __str__(self):
        return (
            '------------------- Metrics -------------------\n'
            f'Name: {self.name}\n'
            f'Allocation: {self.allocation}\n'
            f'Starting Value: ${self.start_val:.2f}\n'
            f'Ending Value: ${self.end_val:.2f}\n'
            f'Start Date: {self.start_date}\n'
            f'End Date: {self.end_date}\n'
            f'CAGR: {self.cagr:.2%}\n'
            f'Maximum Drawdown: {self.max_drawdown:.2%}\n'
            f'STD (annualized): {self.std:.2%}\n'
            f'Sharpe Ratio: {self.sharpe:.2f}\n'
            f'Sortino Ratio: {self.sortino:.2f}\n'
            f'Market Correlation: {self.correlation:.2f}\n'
            '-----------------------------------------------\n'
        )
