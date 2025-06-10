from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class Option(BaseModel):
    instrument_name: str
    expiration: datetime
    strike: int
    type: Literal['call', 'put']
    open_interest: float
    mark_price: float
    best_ask_amount: float
    best_ask_price: float
    ask_iv: float
    best_bid_price: float
    best_bid_amount: float
    bid_iv: float
    

class Exchange(ABC):
    """
    Abstract base class defining the interface for an options exchange.

    Subclasses must implement the `base_url`, `fetch_calls`, and `fetch_puts` methods.
    """


    @property
    @abstractmethod
    def base_url(self):
        """
        Returns the base URL of the exchange API.

        Returns:
            str: The base URL endpoint for the exchange API.
        """
        ...
    

    @abstractmethod
    def fetch_calls(self, expiration: datetime) -> list[Option]:
        """
        Fetches call option data for the specified expiration datetime.

        Args:
            expiration (datetime): The expiration datetime for which to retrieve call options.

        Returns:
            list[Option]: A list of `Option` instances representing call options.

        Raises:
            ConnectionError: If there is a network issue when contacting the API.
            ValueError: If the `expiration` datetime is invalid or in the past.
        """
        ...

    
    @abstractmethod
    def fetch_puts(self, expiration: datetime) -> list[Option]:
        """
        Fetches put option data for the specified expiration datetime.

        Args:
            expiration (datetime): The expiration datetime for which to retrieve put options.

        Returns:
            list[Option]: A list of `Option` instances representing put options.

        Raises:
            ConnectionError: If there is a network issue when contacting the API.
            ValueError: If the `expiration` datetime is invalid or in the past.
        """
        ...