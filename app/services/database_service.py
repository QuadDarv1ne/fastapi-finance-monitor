"""Database service for handling database operations"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import User, Watchlist, WatchlistItem, Portfolio, PortfolioItem
from app.database import get_db
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # User operations
    def create_user(self, username: str, email: str, password: str) -> User:
        """Create a new user"""
        try:
            # Validate input
            if not username or not email or not password:
                raise ValueError("Username, email, and password are required")
            
            # Truncate password to 72 bytes if needed (for bcrypt compatibility)
            if len(password.encode('utf-8')) > 72:
                password = password[:72]
            
            # Validate password strength
            is_valid, message = AuthService.validate_password(password)
            if not is_valid:
                raise ValueError(message)
            
            # Validate email format
            if not AuthService.validate_email(email):
                raise ValueError("Invalid email format")
            
            # Check if user already exists
            existing_user = self.get_user_by_username(username)
            if existing_user:
                raise ValueError("Username already registered")
            
            existing_email = self.get_user_by_email(email)
            if existing_email:
                raise ValueError("Email already registered")
            
            # Hash the password
            hashed_password = AuthService.get_password_hash(password)
            
            # Create user
            db_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password
            )
            
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with rate limiting"""
        try:
            # Check rate limiting
            if not AuthService.is_login_allowed(username):
                logger.warning(f"Login rate limit exceeded for user: {username}")
                return None
            
            user = self.get_user_by_username(username)
            if not user:
                # Record failed login attempt
                AuthService.record_failed_login(username)
                return None
            
            # Get the actual hashed password value
            hashed_password = getattr(user, 'hashed_password')
            
            # Check password
            if AuthService.verify_password(password, hashed_password):
                # Reset failed login attempts on successful login
                login_attempts = AuthService.get_login_attempts()
                if username in login_attempts:
                    del login_attempts[username]
                return user
            
            # Record failed login attempt
            AuthService.record_failed_login(username)
            return None
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            return None
    
    def update_user(self, user_id: int, email: Optional[str] = None) -> Optional[User]:
        """Update user information"""
        try:
            user = self.get_user(user_id)
            if not user:
                return None
            
            # Update email if provided
            if email:
                # Validate email format
                if not AuthService.validate_email(email):
                    raise ValueError("Invalid email format")
                
                # Check if email is already taken
                existing_email = self.get_user_by_email(email)
                existing_email_id = getattr(existing_email, 'id', None) if existing_email else None
                user_id_attr = getattr(user, 'id')
                if existing_email and existing_email_id != user_id_attr:
                    raise ValueError("Email already registered")
                setattr(user, 'email', email)
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            # Truncate password to 72 bytes if needed (for bcrypt compatibility)
            if len(new_password.encode('utf-8')) > 72:
                new_password = new_password[:72]
            
            # Validate password strength
            is_valid, message = AuthService.validate_password(new_password)
            if not is_valid:
                raise ValueError(message)
            
            # Hash and update password
            setattr(user, 'hashed_password', AuthService.get_password_hash(new_password))
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating password for user {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            # Delete associated watchlists and portfolios first
            watchlists = self.get_user_watchlists(user_id)
            for watchlist in watchlists:
                # Get the actual ID value, not the column reference
                watchlist_id = getattr(watchlist, 'id')
                self.delete_watchlist(watchlist_id)
            
            portfolios = self.get_user_portfolios(user_id)
            for portfolio in portfolios:
                # Get the actual ID value, not the column reference
                portfolio_id = getattr(portfolio, 'id')
                self.delete_portfolio(portfolio_id)
            
            # Delete user
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    # Watchlist operations
    def create_watchlist(self, user_id: int, name: str) -> Watchlist:
        """Create a new watchlist"""
        try:
            watchlist = Watchlist(user_id=user_id, name=name)
            self.db.add(watchlist)
            self.db.commit()
            self.db.refresh(watchlist)
            return watchlist
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating watchlist for user {user_id}: {e}")
            raise
    
    def get_user_watchlists(self, user_id: int) -> List[Watchlist]:
        """Get all watchlists for a user"""
        try:
            return self.db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting watchlists for user {user_id}: {e}")
            return []
    
    def get_watchlist(self, watchlist_id: int) -> Optional[Watchlist]:
        """Get watchlist by ID"""
        try:
            return self.db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
        except Exception as e:
            logger.error(f"Error getting watchlist {watchlist_id}: {e}")
            return None
    
    def add_to_watchlist(self, watchlist_id: int, symbol: str, name: str, asset_type: str) -> WatchlistItem:
        """Add item to watchlist"""
        try:
            # Check if item already exists
            existing_item = self.db.query(WatchlistItem).filter(
                and_(
                    WatchlistItem.watchlist_id == watchlist_id,
                    WatchlistItem.symbol == symbol
                )
            ).first()
            
            if existing_item:
                return existing_item
            
            # Create new item
            item = WatchlistItem(
                watchlist_id=watchlist_id,
                symbol=symbol,
                name=name,
                asset_type=asset_type
            )
            
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding {symbol} to watchlist {watchlist_id}: {e}")
            raise
    
    def remove_from_watchlist(self, watchlist_id: int, symbol: str) -> bool:
        """Remove item from watchlist"""
        try:
            item = self.db.query(WatchlistItem).filter(
                and_(
                    WatchlistItem.watchlist_id == watchlist_id,
                    WatchlistItem.symbol == symbol
                )
            ).first()
            
            if item:
                self.db.delete(item)
                self.db.commit()
                return True
            
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing {symbol} from watchlist {watchlist_id}: {e}")
            return False
    
    def get_watchlist_items(self, watchlist_id: int) -> List[WatchlistItem]:
        """Get all items in a watchlist"""
        try:
            return self.db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == watchlist_id).all()
        except Exception as e:
            logger.error(f"Error getting items for watchlist {watchlist_id}: {e}")
            return []
    
    def delete_watchlist(self, watchlist_id: int) -> bool:
        """Delete watchlist and all its items"""
        try:
            # Delete all items first
            items = self.get_watchlist_items(watchlist_id)
            for item in items:
                self.db.delete(item)
            
            # Delete watchlist
            watchlist = self.get_watchlist(watchlist_id)
            if watchlist:
                self.db.delete(watchlist)
                self.db.commit()
                return True
            
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting watchlist {watchlist_id}: {e}")
            return False
    
    # Portfolio operations
    def create_portfolio(self, user_id: int, name: str) -> Portfolio:
        """Create a new portfolio"""
        try:
            portfolio = Portfolio(user_id=user_id, name=name)
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
            return portfolio
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating portfolio for user {user_id}: {e}")
            raise
    
    def get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        """Get all portfolios for a user"""
        try:
            return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting portfolios for user {user_id}: {e}")
            return []
    
    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        try:
            return self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        except Exception as e:
            logger.error(f"Error getting portfolio {portfolio_id}: {e}")
            return None
    
    def add_to_portfolio(self, portfolio_id: int, symbol: str, name: str, quantity: float, 
                        purchase_price: float, purchase_date: str, asset_type: str) -> PortfolioItem:
        """Add item to portfolio"""
        try:
            from datetime import datetime
            
            item = PortfolioItem(
                portfolio_id=portfolio_id,
                symbol=symbol,
                name=name,
                quantity=quantity,
                purchase_price=purchase_price,
                purchase_date=datetime.fromisoformat(purchase_date),
                asset_type=asset_type
            )
            
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding {symbol} to portfolio {portfolio_id}: {e}")
            raise
    
    def remove_from_portfolio(self, portfolio_id: int, symbol: str) -> bool:
        """Remove item from portfolio"""
        try:
            item = self.db.query(PortfolioItem).filter(
                and_(
                    PortfolioItem.portfolio_id == portfolio_id,
                    PortfolioItem.symbol == symbol
                )
            ).first()
            
            if item:
                self.db.delete(item)
                self.db.commit()
                return True
            
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing {symbol} from portfolio {portfolio_id}: {e}")
            return False
    
    def get_portfolio_items(self, portfolio_id: int) -> List[PortfolioItem]:
        """Get all items in a portfolio"""
        try:
            return self.db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
        except Exception as e:
            logger.error(f"Error getting items for portfolio {portfolio_id}: {e}")
            return []
    
    def delete_portfolio(self, portfolio_id: int) -> bool:
        """Delete portfolio and all its items"""
        try:
            # Delete all items first
            items = self.get_portfolio_items(portfolio_id)
            for item in items:
                self.db.delete(item)
            
            # Delete portfolio
            portfolio = self.get_portfolio(portfolio_id)
            if portfolio:
                self.db.delete(portfolio)
                self.db.commit()
                return True
            
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting portfolio {portfolio_id}: {e}")
            return False