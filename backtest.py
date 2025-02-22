import backtrader as bt
import pandas as pd
import os
from strategy import AdvancedTradingStrategy  # Import your strategy class

# Define a data feed class for CSV files
class CSVDataFeed(bt.feeds.GenericCSVData):
    params = (
        ('fromdate', None),  # Start date (None means use all data)
        ('todate', None),    # End date (None means use all data)
        ('dtformat', '%Y-%m-%d %H:%M:%S'),  # Date format in CSV
        ('datetime', 0),     # Column index for datetime
        ('open', 1),         # Column index for open price
        ('high', 2),         # Column index for high price
        ('low', 3),          # Column index for low price
        ('close', 4),        # Column index for close price
        ('volume', 5),       # Column index for volume
        ('openinterest', -1), # Column index for open interest (if available)
    )

# Main function to run the backtest
def run_backtest():
    # Create a Cerebro engine instance
    cerebro = bt.Cerebro(exactbars=True)

    # Add your strategy
    cerebro.addstrategy(AdvancedTradingStrategy)

    # Load all CSV files from the GitHub repository
    csv_files = [
        'Trading-bot1/data1.csv',  # Replace with actual file paths
        'Trading-bot1/data2.csv',
        'Trading-bot1/data3.csv',
        'Trading-bot1/data4.csv',
        'Trading-bot1/data5.csv',
    ]

    for file in csv_files:
        if os.path.exists(file):
            data = CSVDataFeed(dataname=file)
            cerebro.adddata(data)
        else:
            print(f"File not found: {file}")

    # Set initial capital
    cerebro.broker.set_cash(100000.0)  # Set your initial capital

    # Set commission (optional)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% commission

    # Run the backtest
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the results (optional)
    cerebro.plot()

# Run the backtest
if __name__ == '__main__':
    run_backtest()
