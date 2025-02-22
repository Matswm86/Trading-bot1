import backtrader as bt
import pytz
from datetime import datetime

class AdvancedTradingStrategy(bt.Strategy):
    params = (
        ('rr_ratio', 3.0),  # Risk-Reward ratio set to 3.0
        ('rsi_period', 14),  # RSI period
        ('volume_threshold', 1.5),  # Volume threshold for zones
        ('fvg_threshold', 0.5),  # Fair Value Gap threshold
        ('engulfing_lookback', 2),  # Lookback period for engulfing patterns
        ('stop_loss_buffer', 0.995),  # Buffer for stop-loss calculation
        ('trade_start_time', '08:00'),  # Start time for trading (Oslo time)
        ('trade_end_time', '22:00'),  # End time for trading (Oslo time)
        ('use_atr', False),  # Toggle for ATR-based stop loss and take profit
        ('atr_period', 14),  # ATR period
        ('atr_multiplier', 2.0),  # Multiplier for ATR-based stop loss
    )

    def __init__(self):
        # Define indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.stochastic = bt.indicators.Stochastic(self.data)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        # Calculate average volume dynamically using SMA
        self.avg_volume = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)

        # Track trades to ensure only one trade per day
        self.last_trade_date = None

    def log(self, txt: str):
        """Logging function for debugging."""
        dt = self.data.datetime.datetime()
        print(f'{dt}, {txt}')

    def is_demand_zone(self, index: int) -> bool:
        """
        Identify demand zones based on swing lows and volume.
        """
        # Check for swing low
        if (self.data.low[index] < self.data.low[index - 1] and
            self.data.low[index] < self.data.low[index + 1]):
            # Check for high volume
            if self.data.volume[index] > self.avg_volume[index] * self.params.volume_threshold:
                return True
        return False

    def is_supply_zone(self, index: int) -> bool:
        """
        Identify supply zones based on swing highs and volume.
        """
        # Check for swing high
        if (self.data.high[index] > self.data.high[index - 1] and
            self.data.high[index] > self.data.high[index + 1]):
            # Check for high volume
            if self.data.volume[index] > self.avg_volume[index] * self.params.volume_threshold:
                return True
        return False

    def is_fair_value_gap(self, index: int) -> bool:
        """
        Identify Fair Value Gaps (FVGs).
        """
        # Calculate the gap between the current candle and the previous candle
        gap = abs(self.data.close[index] - self.data.open[index - 1])
        return gap > self.params.fvg_threshold

    def is_engulfing_pattern(self, index: int) -> str:
        """
        Identify engulfing patterns and return type ('bullish' or 'bearish').
        """
        # Bullish engulfing
        if (self.data.close[index] > self.data.open[index - 1] and
            self.data.open[index] < self.data.close[index - 1]):
            return 'bullish'
        # Bearish engulfing
        elif (self.data.close[index] < self.data.open[index - 1] and
              self.data.open[index] > self.data.close[index - 1]):
            return 'bearish'
        return None

    def is_within_trading_hours(self):
        """
        Check if the current time is within trading hours (08:00-22:00 Oslo time).
        """
        oslo_tz = pytz.timezone('Europe/Oslo')
        current_time = self.data.datetime.datetime().astimezone(oslo_tz).time()
        start_time = datetime.strptime(self.params.trade_start_time, '%H:%M').time()
        end_time = datetime.strptime(self.params.trade_end_time, '%H:%M').time()
        return start_time <= current_time <= end_time

    def next(self):
        # Skip if outside trading hours or already traded today
        if not self.is_within_trading_hours():
            return
        if self.last_trade_date == self.data.datetime.date():
            return

        # Check for entry conditions
        for i in range(self.params.engulfing_lookback, len(self.data) - 1):
            engulfing_type = self.is_engulfing_pattern(i)
            if (engulfing_type == 'bullish' and self.is_demand_zone(i) and
                self.is_bullish_momentum() and self.is_fair_value_gap(i)):
                self.enter_trade('long', i)
                self.last_trade_date = self.data.datetime.date()
                break  # Only one trade per day
            elif (engulfing_type == 'bearish' and self.is_supply_zone(i) and
                  self.is_bearish_momentum() and self.is_fair_value_gap(i)):
                self.enter_trade('short', i)
                self.last_trade_date = self.data.datetime.date()
                break  # Only one trade per day

    def enter_trade(self, direction: str, index: int):
        """
        Enter a trade with stop-loss and take-profit based on RR ratio or ATR.
        """
        entry_price = self.data.close[index]
        if self.params.use_atr:
            # ATR-based stop loss and take profit
            atr_value = self.atr[index]
            stop_loss = self.calculate_atr_stop_loss(entry_price, direction, atr_value)
            take_profit = self.calculate_atr_take_profit(entry_price, direction, atr_value)
        else:
            # RR ratio-based stop loss and take profit
            stop_loss = self.calculate_stop_loss(entry_price, direction)
            take_profit = self.calculate_take_profit(entry_price, stop_loss, direction)

        if direction == 'long':
            self.buy()
            self.sell(exectype=bt.Order.Stop, price=stop_loss)
            self.sell(exectype=bt.Order.Limit, price=take_profit)
            self.log(f'Entered LONG at {entry_price}, SL: {stop_loss}, TP: {take_profit}')
        elif direction == 'short':
            self.sell()
            self.buy(exectype=bt.Order.Stop, price=stop_loss)
            self.buy(exectype=bt.Order.Limit, price=take_profit)
            self.log(f'Entered SHORT at {entry_price}, SL: {stop_loss}, TP: {take_profit}')

    def calculate_stop_loss(self, entry_price: float, direction: str) -> float:
        """
        Calculate stop-loss level based on supply/demand zones.
        """
        if direction == 'long':
            # Find nearest demand zone below entry
            for i in range(len(self.data)):
                if self.is_demand_zone(i) and self.data.low[i] < entry_price:
                    return self.data.low[i] * self.params.stop_loss_buffer  # Use parameter
        elif direction == 'short':
            # Find nearest supply zone above entry
            for i in range(len(self.data)):
                if self.is_supply_zone(i) and self.data.high[i] > entry_price:
                    return self.data.high[i] * (2 - self.params.stop_loss_buffer)  # Use parameter
        # Default to 2% stop loss if no suitable zones found
        return entry_price * 0.98 if direction == 'long' else entry_price * 1.02

    def calculate_take_profit(self, entry_price: float, stop_loss: float, direction: str) -> float:
        """
        Calculate take-profit level based on RR ratio.
        """
        if direction == 'long':
            return entry_price + (entry_price - stop_loss) * self.params.rr_ratio
        elif direction == 'short':
            return entry_price - (stop_loss - entry_price) * self.params.rr_ratio

    def calculate_atr_stop_loss(self, entry_price: float, direction: str, atr_value: float) -> float:
        """
        Calculate ATR-based stop loss.
        """
        if direction == 'long':
            return entry_price - atr_value * self.params.atr_multiplier
        elif direction == 'short':
            return entry_price + atr_value * self.params.atr_multiplier

    def calculate_atr_take_profit(self, entry_price: float, direction: str, atr_value: float) -> float:
        """
        Calculate ATR-based take profit.
        """
        if direction == 'long':
            return entry_price + atr_value * self.params.atr_multiplier * self.params.rr_ratio
        elif direction == 'short':
            return entry_price - atr_value * self.params.atr_multiplier * self.params.rr_ratio

    def is_bullish_momentum(self):
        """
        Check for bullish momentum using RSI and Stochastic indicators.
        """
        return self.rsi < 30 and self.stochastic.percK < 20

    def is_bearish_momentum(self):
        """
        Check for bearish momentum using RSI and Stochastic indicators.
        """
        return self.rsi > 70 and self.stochastic.percK > 80
