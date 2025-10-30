"""Database service for handling database operations"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import User, Watchlist, WatchlistItem, Portfolio, PortfolioItem
from app.database import get_db
from app.services.auth_service import AuthService


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # User operations
    def create_user(self, username: str, email: str, password: str) -> User:
        """Create a new user"""
        # Validate password
        is_valid, message = AuthService.validate_password(password)
        if not is_valid:
            raise ValueError(message)
        
        # Validate email
        if not AuthService.validate_email(email):
            raise ValueError("Invalid email format")
        
        # Check if username already exists
        existing_user = self.get_user_by_username(username)
        if existing_user:
            raise ValueError("Username already exists")
        
        # Check if email already exists
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
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        # Check password
        if AuthService.verify_password(password, str(user.hashed_password)):
            return user
        
        return None
    
    def update_user(self, user_id: int, email: Optional[str] = None) -> Optional[User]:
        """Update user information"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        # Update email if provided
        if email:
            # Validate email format
            if not AuthService.validate_email(email):
                raise ValueError("Invalid email format")
            
            # Check if email is already taken by another user
            existing_email = self.get_user_by_email(email)
            if existing_email and existing_email.id != user_id:
                raise ValueError("Email already registered")
            
            user.email = email
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Validate password
        is_valid, message = AuthService.validate_password(new_password)
        if not is_valid:
            raise ValueError(message)
        
        # Hash and update password
        user.hashed_password = AuthService.get_password_hash(new_password)
        self.db.commit()
        return True
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Delete associated watchlists and portfolios first
        watchlists = self.get_user_watchlists(user_id)
        for watchlist in watchlists:
            self.delete_watchlist(int(watchlist.id))
        
        portfolios = self.get_user_portfolios(user_id)
        for portfolio in portfolios:
            self.delete_portfolio(int(portfolio.id))
        
        # Delete user
        self.db.delete(user)
        self.db.commit()
        return True
    
    # Watchlist operations
    def create_watchlist(self, user_id: int, name: str) -> Watchlist:
        """Create a new watchlist"""
        watchlist = Watchlist(user_id=user_id, name=name)
        self.db.add(watchlist)
        self.db.commit()
        self.db.refresh(watchlist)
        return watchlist
    
    def get_user_watchlists(self, user_id: int) -> List[Watchlist]:
        """Get all watchlists for a user"""
        return self.db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    
    def get_watchlist(self, watchlist_id: int) -> Optional[Watchlist]:
        """Get watchlist by ID"""
        return self.db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    
    def add_to_watchlist(self, watchlist_id: int, symbol: str, name: str, asset_type: str) -> WatchlistItem:
        """Add item to watchlist"""
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
    
    def remove_from_watchlist(self, watchlist_id: int, symbol: str) -> bool:
        """Remove item from watchlist"""
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
    
    def get_watchlist_items(self, watchlist_id: int) -> List[WatchlistItem]:
        """Get all items in a watchlist"""
        return self.db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == watchlist_id).all()
    
    def delete_watchlist(self, watchlist_id: int) -> bool:
        """Delete watchlist and all its items"""
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
    
    # Portfolio operations
    def create_portfolio(self, user_id: int, name: str) -> Portfolio:
        """Create a new portfolio"""
        portfolio = Portfolio(user_id=user_id, name=name)
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio
    
    def get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        """Get all portfolios for a user"""
        return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    
    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    def add_to_portfolio(self, portfolio_id: int, symbol: str, name: str, quantity: float, 
                        purchase_price: float, purchase_date: str, asset_type: str) -> PortfolioItem:
        """Add item to portfolio"""
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
    
    def remove_from_portfolio(self, portfolio_id: int, symbol: str) -> bool:
        """Remove item from portfolio"""
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
    
    def get_portfolio_items(self, portfolio_id: int) -> List[PortfolioItem]:
        """Get all items in a portfolio"""
        return self.db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    
    def delete_portfolio(self, portfolio_id: int) -> bool:
        """Delete portfolio and all its items"""
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