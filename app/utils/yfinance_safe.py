"""Safe import wrapper for yfinance with fallback stub

This module provides a centralized, safe import mechanism for yfinance that handles
compatibility issues with newer Python versions (e.g., Python 3.14+ ssl.wrap_socket removal).

The wrapper automatically:
1. Disables curl_cffi usage which can cause ssl/eventlet conflicts
2. Falls back to a minimal stub if import fails
3. Provides consistent interface across all modules

Usage:
    from app.utils.yfinance_safe import get_yf
    
    yf = get_yf()
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period="1d", interval="5m")
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_yf_instance = None
_import_failed = False


def get_yf() -> Any:
    """
    Get yfinance module with safe import and fallback
    
    Returns:
        yfinance module or stub if import fails
        
    Note:
        This function caches the result to avoid repeated import attempts
    """
    global _yf_instance, _import_failed
    
    # Return cached instance if available
    if _yf_instance is not None:
        return _yf_instance
    
    # Don't retry if import previously failed
    if _import_failed:
        return _create_stub()
    
    try:
        # Disable curl_cffi usage to prevent eventlet/ssl issues
        os.environ.setdefault("YFINANCE_NO_CURL", "1")
        
        import yfinance as yf  # type: ignore
        
        logger.info("yfinance module imported successfully")
        _yf_instance = yf
        return yf
        
    except Exception as e:
        logger.warning(f"yfinance import failed: {e}; using lightweight stub")
        _import_failed = True
        stub = _create_stub()
        _yf_instance = stub
        return stub


def _create_stub() -> Any:
    """
    Create a minimal yfinance stub for testing/fallback
    
    Returns:
        Stub object with minimal Ticker interface
    """
    try:
        import pandas as pd
        has_pandas = True
    except ImportError:
        has_pandas = False
        pd = None
    
    class _YFStub:
        """Minimal stub implementing yfinance.Ticker interface"""
        
        def Ticker(self, symbol: str):
            """Create a stub ticker object"""
            
            class _Ticker:
                """Stub ticker with minimal history method"""
                
                def __init__(self, symbol: str):
                    self.symbol = symbol
                
                def history(self, period: str = "1d", interval: str = "1m"):
                    """Return empty or minimal DataFrame"""
                    if has_pandas and pd is not None:
                        # Return minimal deterministic DataFrame for tests
                        return pd.DataFrame({
                            "Open": [100.0],
                            "High": [101.0],
                            "Low": [99.0],
                            "Close": [100.0],
                            "Volume": [1000000]
                        })
                    else:
                        # Return empty list if pandas not available
                        return []
            
            return _Ticker(symbol)
    
    return _YFStub()
