"""Tests for the alert service"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime
from app.services.alert_service import AlertService
from app.services.database_service import DatabaseService


class TestAlertService:
    """Test suite for AlertService"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock database service
        self.mock_db_service = Mock(spec=DatabaseService)
        self.alert_service = AlertService(self.mock_db_service)
    
    def test_create_price_alert(self):
        """Test creating a price alert"""
        # Call the method
        result = asyncio.run(self.alert_service.create_price_alert(1, "AAPL", 150.0, "above"))
        
        # Assertions
        assert "alert_id" in result
        assert "message" in result
        assert result["message"] == "Alert created successfully"
        assert len(self.alert_service.active_alerts) == 1
    
    def test_remove_alert(self):
        """Test removing an alert"""
        # First create an alert
        result = asyncio.run(self.alert_service.create_price_alert(1, "AAPL", 150.0, "above"))
        alert_id = result["alert_id"]
        
        # Verify alert was created
        assert len(self.alert_service.active_alerts) == 1
        
        # Remove the alert
        success = asyncio.run(self.alert_service.remove_alert(alert_id))
        
        # Assertions
        assert success is True
        assert len(self.alert_service.active_alerts) == 0
    
    def test_get_user_alerts(self):
        """Test getting user alerts"""
        # Create alerts for different users
        asyncio.run(self.alert_service.create_price_alert(1, "AAPL", 150.0, "above"))
        asyncio.run(self.alert_service.create_price_alert(2, "GOOGL", 2500.0, "below"))
        asyncio.run(self.alert_service.create_price_alert(1, "MSFT", 300.0, "above"))
        
        # Get alerts for user 1
        result = asyncio.run(self.alert_service.get_user_alerts(1))
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        # Check that all alerts belong to user 1
        for alert in result:
            assert alert["user_id"] == 1
    
    def test_check_alert_condition_above(self):
        """Test checking alert condition for price above target"""
        # Create an alert
        alert = {
            "id": "test_alert",
            "user_id": 1,
            "symbol": "AAPL",
            "target_price": 150.0,
            "alert_type": "above",
            "watchlist_item_id": None,
            "created_at": datetime.now(),
            "active": True
        }
        
        # Test condition met (current price is above target)
        asyncio.run(self.alert_service._check_alert_condition(alert, 160.0))
        
        # Alert should be removed after being triggered
        assert len(self.alert_service.active_alerts) == 0
    
    def test_check_alert_condition_below(self):
        """Test checking alert condition for price below target"""
        # Create an alert
        alert = {
            "id": "test_alert",
            "user_id": 1,
            "symbol": "AAPL",
            "target_price": 150.0,
            "alert_type": "below",
            "watchlist_item_id": None,
            "created_at": datetime.now(),
            "active": True
        }
        
        # Test condition met (current price is below target)
        asyncio.run(self.alert_service._check_alert_condition(alert, 140.0))
        
        # Alert should be removed after being triggered
        assert len(self.alert_service.active_alerts) == 0
    
    def test_check_alert_condition_not_met(self):
        """Test checking alert condition when not met"""
        # Create an alert
        alert = {
            "id": "test_alert",
            "user_id": 1,
            "symbol": "AAPL",
            "target_price": 150.0,
            "alert_type": "above",
            "watchlist_item_id": None,
            "created_at": datetime.now(),
            "active": True
        }
        
        # Store initial alert count
        initial_count = len(self.alert_service.active_alerts)
        
        # Test condition not met (current price is below target)
        asyncio.run(self.alert_service._check_alert_condition(alert, 140.0))
        
        # Alert should still be active
        assert len(self.alert_service.active_alerts) == initial_count
    
    @patch('app.services.alert_service.smtplib.SMTP')
    def test_send_email_notification(self, mock_smtp):
        """Test sending email notification"""
        # Setup mock SMTP
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Create a mock user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        
        # Set email configuration
        self.alert_service.email_username = "test_sender@example.com"
        self.alert_service.email_password = "password123"
        
        # Call the method
        asyncio.run(self.alert_service.send_email_notification(
            mock_user, 
            "Test Subject", 
            "Test Message"
        ))
        
        # Assertions
        mock_smtp.assert_called_once_with(self.alert_service.smtp_server, self.alert_service.smtp_port)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test_sender@example.com", "password123")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])