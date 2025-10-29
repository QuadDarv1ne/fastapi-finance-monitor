#!/usr/bin/env python3
"""
Demonstration script for technical indicators calculation
"""

import sys
import os
import yfinance as yf
import pandas as pd

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.indicators import TechnicalIndicators

def demonstrate_indicators(symbol="AAPL", period="6mo"):
    """Demonstrate technical indicators calculation"""
    print(f"Technical Indicators Demonstration for {symbol}")
    print("=" * 50)
    
    try:
        # Fetch data
        print(f"Fetching {period} of data for {symbol}...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        
        if df.empty:
            print(f"No data found for {symbol}")
            return
        
        print(f"Retrieved {len(df)} data points")
        print()
        
        # Calculate all indicators
        print("Calculating technical indicators...")
        indicators = TechnicalIndicators.calculate_all_indicators(df)
        
        # Display results
        print("Technical Indicators Results:")
        print("-" * 30)
        
        # RSI
        print(f"RSI (14-period): {indicators['rsi']:.2f}")
        
        # Moving Averages
        print(f"MA (20-period): {indicators['ma_20']:.2f}")
        print(f"MA (50-period): {indicators['ma_50']:.2f}")
        
        # EMA
        print(f"EMA (12-period): {indicators['ema_12']:.2f}")
        print(f"EMA (26-period): {indicators['ema_26']:.2f}")
        
        # MACD
        macd = indicators['macd']
        print(f"MACD: {macd['macd']:.2f}")
        print(f"MACD Signal: {macd['signal']:.2f}")
        print(f"MACD Histogram: {macd['histogram']:.2f}")
        
        # Bollinger Bands
        bb = indicators['bollinger_bands']
        print(f"Bollinger Bands Upper: {bb['upper']:.2f}")
        print(f"Bollinger Bands Middle: {bb['middle']:.2f}")
        print(f"Bollinger Bands Lower: {bb['lower']:.2f}")
        
        # Stochastic Oscillator
        stoch = indicators['stochastic']
        print(f"Stochastic %K: {stoch['k']:.2f}")
        print(f"Stochastic %D: {stoch['d']:.2f}")
        
        # ATR
        print(f"ATR (14-period): {indicators['atr']:.2f}")
        
        print()
        print("Current Price Analysis:")
        print("-" * 20)
        current_price = df['Close'].iloc[-1]
        print(f"Current Price: ${current_price:.2f}")
        
        # Compare with moving averages
        if current_price > indicators['ma_20']:
            print("Price is ABOVE 20-day MA (Bullish signal)")
        else:
            print("Price is BELOW 20-day MA (Bearish signal)")
            
        if current_price > indicators['ma_50']:
            print("Price is ABOVE 50-day MA (Bullish signal)")
        else:
            print("Price is BELOW 50-day MA (Bearish signal)")
        
        # RSI interpretation
        if indicators['rsi'] > 70:
            print("RSI indicates OVERBOUGHT conditions")
        elif indicators['rsi'] < 30:
            print("RSI indicates OVERSOLD conditions")
        else:
            print("RSI indicates NEUTRAL conditions")
            
        # MACD interpretation
        if macd['histogram'] > 0:
            print("MACD Histogram is POSITIVE (Bullish momentum)")
        else:
            print("MACD Histogram is NEGATIVE (Bearish momentum)")
            
    except Exception as e:
        print(f"Error calculating indicators: {e}")

def main():
    """Main function"""
    print("FastAPI Finance Monitor - Technical Indicators Demo")
    print("=" * 55)
    print()
    
    # Demonstrate with Apple stock
    demonstrate_indicators("AAPL")
    
    print()
    print("Try with other symbols:")
    print("  python demonstrate_indicators.py MSFT  # Microsoft")
    print("  python demonstrate_indicators.py GOOGL # Google")
    print("  python demonstrate_indicators.py TSLA  # Tesla")
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        period = sys.argv[2] if len(sys.argv) > 2 else "6mo"
        print()
        print("-" * 50)
        demonstrate_indicators(symbol, period)

if __name__ == "__main__":
    main()