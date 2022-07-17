import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# A group of functions that may be helpful in visualizing backtests.


def graph_return(*backtests,
                 start_val=None,
                 logarithmic=False,
                 path=None):
    """ Graphs the cumulative return of any number of backtests.

    X-axis corresponds to the date. Y-axis corresponds to the cumulative return on that date. The latest start date
    encompassing the entirety of every backtest will be used, and the graphed return is relative to that start date.

    Args:
        *backtests: Any number of Backtest objects to be graphed.
        start_val: The starting portfolio value for each backtest. Set to None if relative return is desired.
        logarithmic: Y-axis will be logarithmic if True, linear if False.
        path: File path to save the graph as a picture in the working directory. Defaults to None for interactive mode.
    """

    data = []
    headers = []

    for backtest in backtests:
        data.append(backtest.hist['Total'])
        headers.append(backtest.name)

    df = pd.concat(data, axis=1, keys=headers)
    df = df.dropna()
    df = df.div(df.iloc[0])

    if start_val:
        df *= start_val

    ax = df.plot(figsize=(10, 5), kind='line', logy=logarithmic)
    ax.grid(axis='y', which='both')
    ax.grid(axis='x', which='major')

    if logarithmic:
        plt.yscale('log', subs=[2, 4, 6, 8])
        if not start_val:
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
            ax.yaxis.set_minor_formatter(ticker.PercentFormatter(xmax=1.0))

    if start_val:
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
        ax.yaxis.set_minor_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
        ax.hlines(y=start_val, xmin=df.index[0], xmax=df.index[-1], color='k', zorder=0)
        ax.set_ylabel('Value')
    else:
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
        ax.hlines(y=1, xmin=df.index[0], xmax=df.index[-1], color='k', zorder=0)
        ax.set_ylabel('Return')

    ax.margins(x=0)
    ax.set_title("Portfolio Returns")

    if path:
        plt.savefig(path)
    else:
        plt.show()
    plt.close()


def graph_drawdown(*backtests,
                   path=None):
    """ Graphs the drawdowns of any number of backtests.

    X-axis corresponds to the date. Y-axis corresponds to the drawdown of that date. The latest start date
    encompassing the entirety of every backtest will be used. Note that if a backtest is truncated in order to
    encompass all backtests, the drawdowns near the beginning may be relative to a maximum before the start date
    rather than the actual start value. To avoid this, have all Backtest objects start at the same date.

    Args:
        *backtests: Any number of Backtest objects to be graphed.
        path: File path to save the graph as a picture in the working directory. Defaults to None for interactive mode.
    """

    data = []
    headers = []

    for backtest in backtests:
        data.append(backtest.hist['Drawdown'])
        headers.append(backtest.name)

    df = pd.concat(data, axis=1, keys=headers)
    df = df.dropna()

    ax = df.plot(figsize=(10, 5), kind='line')
    ax.grid(axis='y', which='major')
    ax.grid(axis='x', which='major')

    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
    ax.margins(x=0, y=0)
    ax.set_title("Portfolio Drawdowns")

    if path:
        plt.savefig(path)
    else:
        plt.show()
    plt.close()


def graph_rolling_returns(*backtests,
                          interval=12,
                          path=None):
    """ Graphs the annualized rolling returns of any number of backtests over a given interval length.

    X-axis corresponds to the interval ending on that date. Y-axis is the annualized return of that interval. The
    latest start date encompassing the entirety of every backtest will be used. Assumes 1 month = 21 trading days.

    Args:
        *backtests: Any number of Backtest objects to be graphed.
        interval: Number of months for each interval. Must be shorter than the duration of the backtests themselves.
        path: File path to save the graph as a picture in the working directory. Defaults to None for interactive mode.
    """

    data = []
    headers = []

    for backtest in backtests:
        data.append(backtest.get_rolling_returns(interval))
        headers.append(backtest.name)

    df = pd.concat(data, axis=1, keys=headers)
    df = df.dropna()

    ax = df.plot(figsize=(10, 5), kind='line')
    ax.grid(axis='y', which='major')
    ax.grid(axis='x', which='major')
    ax.hlines(y=0, xmin=df.index[0], xmax=df.index[-1], color='k', zorder=0)
    ax.margins(x=0)

    ax.set_ylabel('Annualized Return')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
    ax.set_title(f'Annualized Rolling Returns of {interval} Month Intervals')

    if path:
        plt.savefig(path)
    else:
        plt.show()
    plt.close()