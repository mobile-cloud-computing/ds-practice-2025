import copy
import threading
from typing import Dict, List, Optional


class VectorClock:
    """
    Implementation of vector clock for tracking causality between events
    across distributed services
    """

    def __init__(self, services: List[str]):
        """
        Initialize vector clock with zeros for all services
        """
        self.clock = {service: 0 for service in services}
        self.lock = threading.Lock()

    def increment(self, service: str) -> None:
        """
        Increment the clock value for a specific service
        """
        with self.lock:
            if service in self.clock:
                self.clock[service] += 1

    def update(self, other_clock: Dict[str, int]) -> None:
        """
        Update this clock to the component-wise maximum of itself and another clock
        """
        with self.lock:
            for service, value in other_clock.items():
                if service in self.clock:
                    self.clock[service] = max(self.clock[service], value)

    def get_clock(self) -> Dict[str, int]:
        """
        Get a copy of the current clock state
        """
        with self.lock:
            return copy.deepcopy(self.clock)

    def __str__(self) -> str:
        """
        String representation of the vector clock
        """
        return str(self.clock)

    def is_less_than_or_equal(self, other_clock: Dict[str, int]) -> bool:
        """
        Check if this clock is less than or equal to another clock (component-wise)
        """
        with self.lock:
            for service, value in self.clock.items():
                if value > other_clock.get(service, 0):
                    return False
            return True


class OrderEventTracker:
    """
    Tracks order events and their vector clocks across services
    """

    def __init__(
        self,
        services: List[str] = [
            "orchestrator",
            "suggestions",
            "transaction_verification",
            "fraud_detection",
        ],
    ):
        """
        Initialize the event tracker with the list of services
        """
        self.services = services
        self.orders = {}  # Dict[order_id, Dict[service, VectorClock]]
        self.events_processed = {}  # Dict[order_id, set(event_names)]
        self.lock = threading.Lock()

    def initialize_order(self, order_id: str) -> None:
        """
        Initialize tracking for a new order
        """
        with self.lock:
            if order_id not in self.orders:
                self.orders[order_id] = {
                    service: VectorClock(self.services) for service in self.services
                }
                self.events_processed[order_id] = set()

    def order_exists(self, order_id: str) -> bool:
        """
        Check if an order has been initialized in the tracker

        Args:
            order_id: The unique identifier for the order

        Returns:
            bool: True if the order exists, False otherwise
        """
        with self.lock:
            return order_id in self.orders

    def record_event(
        self,
        order_id: str,
        service: str,
        event_name: str,
        received_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, int]:
        """
        Record an event occurrence for an order, update the vector clock,
        and return the new clock value
        """
        with self.lock:
            if order_id not in self.orders:
                self.initialize_order(order_id)

            # Update clock with received clock if provided
            if received_clock:
                self.orders[order_id][service].update(received_clock)

            # Increment the service's own component
            self.orders[order_id][service].increment(service)

            # Add to processed events
            self.events_processed[order_id].add(event_name)

            # Return a copy of the current clock
            return self.orders[order_id][service].get_clock()

    def get_clock(self, order_id: str, service: str) -> Dict[str, int]:
        """
        Get the current vector clock for a specific order and service
        """
        with self.lock:
            if order_id in self.orders and service in self.orders[order_id]:
                return self.orders[order_id][service].get_clock()
            return None

    def is_event_processed(self, order_id: str, event_name: str) -> bool:
        """
        Check if an event has been processed for an order
        """
        with self.lock:
            return (
                order_id in self.events_processed
                and event_name in self.events_processed[order_id]
            )

    def clear_order(self, order_id: str, final_clock: Dict[str, int] = None) -> bool:
        """
        Clear the order data if the final clock is greater than or equal to local clocks
        Returns True if successful, False if vector clock conditions aren't met
        """
        with self.lock:
            if order_id not in self.orders:
                return True  # Nothing to clear

            if final_clock:
                # Check if all service clocks <= final_clock
                for service, vc in self.orders[order_id].items():
                    if not vc.is_less_than_or_equal(final_clock):
                        return False  # Cannot clear, local clock has events not in final_clock

            # clear data
            del self.orders[order_id]
            if order_id in self.events_processed:
                del self.events_processed[order_id]

            return True
