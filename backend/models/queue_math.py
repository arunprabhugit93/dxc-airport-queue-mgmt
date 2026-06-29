"""M/M/c queueing math shared by ETL wait derivation, staffing, and SimPy.

Implements the Erlang-C expected waiting time (Wq) for an M/M/c queue:
Poisson arrivals at rate lambda, c identical servers each at exponential service
rate mu. Used to derive `wait_min_est` in the disaggregation step and to size
lanes in the staffing heuristic (D2, D4-B). All waits are in minutes and clamped
to [0, 120].
"""

from __future__ import annotations

import math


def mm_c_wait(
    arrival_rate_per_min: float,
    service_rate_per_lane: float,
    c: int,
) -> float:
    """Expected wait time in queue (Wq) for an M/M/c queue, in minutes.

    Args:
        arrival_rate_per_min: lambda, passenger arrivals per minute.
        service_rate_per_lane: mu, passengers served per minute per lane.
        c: number of open lanes (servers).

    Returns:
        Expected time a passenger waits in queue before service, in minutes.
        Returns 0.0 when there is no load or no servers. Returns 120.0 (the
        clamp ceiling) when the system is saturated (utilisation >= 1).
    """
    if c <= 0 or arrival_rate_per_min <= 0 or service_rate_per_lane <= 0:
        return 0.0

    rho = arrival_rate_per_min / (service_rate_per_lane * c)  # utilisation
    if rho >= 1.0:
        return 120.0  # saturated — clamp to ceiling

    a = arrival_rate_per_min / service_rate_per_lane  # offered load (Erlangs)

    # Erlang-C: probability that an arriving passenger must wait.
    sum_term = sum((a ** n) / math.factorial(n) for n in range(c))
    last_term = (a ** c) / (math.factorial(c) * (1 - rho))
    p0 = 1.0 / (sum_term + last_term)
    prob_wait = last_term * p0

    wq = prob_wait / (c * service_rate_per_lane - arrival_rate_per_min)
    return min(max(wq, 0.0), 120.0)


def min_lanes_for_sla(
    arrival_rate_per_min: float,
    service_rate_per_lane: float,
    sla_target_min: float,
    max_lanes: int,
) -> int:
    """Smallest lane count c (1..max_lanes) whose M/M/c wait <= sla_target_min.

    If no lane count within the physical cap meets the SLA, returns max_lanes
    (the best achievable). Returns at least 1 lane whenever there is any demand.
    """
    if arrival_rate_per_min <= 0:
        return 0
    for c in range(1, max_lanes + 1):
        if mm_c_wait(arrival_rate_per_min, service_rate_per_lane, c) <= sla_target_min:
            return c
    return max_lanes
