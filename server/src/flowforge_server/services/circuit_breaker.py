"""Circuit breaker pattern for external service calls.

Prevents cascading failures by stopping requests to failing services
and allowing them to recover.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from flowforge_server.logging import Loggers

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests flow through
    OPEN = "open"  # Failure threshold reached, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    # Number of failures before opening the circuit
    failure_threshold: int = 5
    # Percentage of failures to trigger open (0-100)
    failure_rate_threshold: float = 50.0
    # Minimum requests before evaluating failure rate
    minimum_requests: int = 10
    # Time in seconds to wait before testing if service recovered
    recovery_timeout: float = 30.0
    # Number of successful requests in half-open to close circuit
    success_threshold: int = 3
    # Sliding window size in seconds for failure rate calculation
    sliding_window_size: float = 60.0


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, name: str, recovery_time: float):
        self.name = name
        self.recovery_time = recovery_time
        super().__init__(
            f"Circuit '{name}' is open. Will retry after {recovery_time:.1f}s"
        )


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single service."""

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    stats: CircuitStats = field(default_factory=CircuitStats)
    _opened_at: float | None = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def _get_failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.stats.total_requests == 0:
            return 0.0
        return (self.stats.failed_requests / self.stats.total_requests) * 100

    def _should_open(self) -> bool:
        """Check if circuit should open based on failures."""
        # Check consecutive failures threshold
        if self.stats.consecutive_failures >= self.config.failure_threshold:
            return True

        # Check failure rate threshold (only after minimum requests)
        if self.stats.total_requests >= self.config.minimum_requests:
            if self._get_failure_rate() >= self.config.failure_rate_threshold:
                return True

        return False

    def _should_close(self) -> bool:
        """Check if circuit should close (after half-open testing)."""
        return self.stats.consecutive_successes >= self.config.success_threshold

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to test recovery."""
        if self._opened_at is None:
            return False
        elapsed = time.time() - self._opened_at
        return elapsed >= self.config.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Get time remaining until recovery attempt."""
        if self._opened_at is None:
            return 0.0
        elapsed = time.time() - self._opened_at
        remaining = self.config.recovery_timeout - elapsed
        return max(0.0, remaining)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        if self.state == new_state:
            return

        log = Loggers.services()
        old_state = self.state
        self.state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            log.warning(
                "circuit_opened",
                circuit=self.name,
                previous_state=old_state.value,
                failure_rate=self._get_failure_rate(),
                consecutive_failures=self.stats.consecutive_failures,
                recovery_timeout=self.config.recovery_timeout,
            )
        elif new_state == CircuitState.HALF_OPEN:
            log.info(
                "circuit_half_open",
                circuit=self.name,
                previous_state=old_state.value,
            )
        elif new_state == CircuitState.CLOSED:
            self._opened_at = None
            # Reset stats on close
            self.stats = CircuitStats()
            log.info(
                "circuit_closed",
                circuit=self.name,
                previous_state=old_state.value,
            )

    async def _before_call(self) -> None:
        """Check if call is allowed, raising if circuit is open."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    raise CircuitOpenError(
                        self.name,
                        self._time_until_recovery(),
                    )

    async def _on_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN and self._should_close():
                await self._transition_to(CircuitState.CLOSED)

    async def _on_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = time.time()

            log = Loggers.services()
            log.debug(
                "circuit_failure_recorded",
                circuit=self.name,
                error=str(error),
                consecutive_failures=self.stats.consecutive_failures,
            )

            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                await self._transition_to(CircuitState.OPEN)
            elif self.state == CircuitState.CLOSED and self._should_open():
                await self._transition_to(CircuitState.OPEN)

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of the function call

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from the function
        """
        await self._before_call()

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "failure_rate": self._get_failure_rate(),
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            },
            "time_until_recovery": (
                self._time_until_recovery() if self.state == CircuitState.OPEN else None
            ),
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config or CircuitBreakerConfig(),
                )
            return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name (non-async)."""
        return self._breakers.get(name)

    def get_all_status(self) -> list[dict[str, Any]]:
        """Get status of all circuit breakers."""
        return [breaker.get_status() for breaker in self._breakers.values()]

    async def reset(self, name: str) -> bool:
        """Reset a circuit breaker to closed state."""
        async with self._lock:
            if name in self._breakers:
                breaker = self._breakers[name]
                async with breaker._lock:
                    breaker.state = CircuitState.CLOSED
                    breaker.stats = CircuitStats()
                    breaker._opened_at = None
                return True
            return False

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for breaker in self._breakers.values():
                async with breaker._lock:
                    breaker.state = CircuitState.CLOSED
                    breaker.stats = CircuitStats()
                    breaker._opened_at = None


# Global registry
_registry: CircuitBreakerRegistry | None = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


async def with_circuit_breaker(
    name: str,
    func: Callable[..., Any],
    *args: Any,
    config: CircuitBreakerConfig | None = None,
    **kwargs: Any,
) -> T:
    """Convenience function to execute with circuit breaker protection.

    Usage:
        result = await with_circuit_breaker(
            "openai",
            client.chat.completions.create,
            model="gpt-4",
            messages=[...],
        )
    """
    registry = get_circuit_breaker_registry()
    breaker = await registry.get_or_create(name, config)
    return await breaker.call(func, *args, **kwargs)
