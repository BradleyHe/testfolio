import testfolio as tsf

allocation_1 = {
    'SPY': 0.6,
    'TLT': 0.4
}

backtest_1 = tsf.Backtest(allocation_1, rebalance='q', name='60/40 Portfolio')
print(backtest_1)

allocation_2 = {
    'Total US Stock Market': 0.60,
    'Total Intl Stock Market': 0.20,
    'Total US Bond Market': 0.20
}

backtest_2 = tsf.Backtest(allocation_2, rebalance='q', name='Three Fund Portfolio')
tsf.graph_return(backtest_1, backtest_2, start_val=1000, logarithmic=True, path='returns.png')
tsf.graph_drawdown(backtest_1, backtest_2, path='drawdowns.png')

