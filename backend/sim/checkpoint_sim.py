"""Checkpoint simulation utilities for the what-if API."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import simpy


@dataclass(frozen=True)
class SimulationResult:
    mean_wait_min: float
    p95_wait_min: float
    max_queue_len: int
    lane_utilisation: float
    sla_breach_min: int


def simulate_checkpoint(
    arrival_rate_per_min: float,
    service_rate_per_lane: float,
    num_lanes: int,
    duration_min: int,
    sla_target_min: float,
    seed: int,
) -> SimulationResult:
    """Simulate one checkpoint as an M/M/c queue over a fixed duration."""
    if (
        arrival_rate_per_min <= 0
        or service_rate_per_lane <= 0
        or num_lanes <= 0
        or duration_min <= 0
    ):
        return SimulationResult(
            mean_wait_min=0.0,
            p95_wait_min=0.0,
            max_queue_len=0,
            lane_utilisation=0.0,
            sla_breach_min=0,
        )

    env = simpy.Environment()
    lanes = simpy.Resource(env, capacity=num_lanes)
    rng = np.random.default_rng(seed)

    waits: list[float] = []
    breach_minutes: set[int] = set()
    max_queue_len = 0
    busy_time = 0.0

    def passenger() -> simpy.events.Event:
        nonlocal max_queue_len, busy_time

        arrival_at = env.now
        queued = len(lanes.queue) + (1 if lanes.count >= lanes.capacity else 0)
        max_queue_len = max(max_queue_len, queued)

        with lanes.request() as request:
            yield request
            wait_min = env.now - arrival_at
            waits.append(wait_min)
            if wait_min > sla_target_min:
                breach_minutes.add(int(arrival_at))

            service_time = float(rng.exponential(1.0 / service_rate_per_lane))
            busy_time += service_time
            yield env.timeout(service_time)

    def arrivals() -> simpy.events.Event:
        while env.now < duration_min:
            interarrival = float(rng.exponential(1.0 / arrival_rate_per_min))
            yield env.timeout(interarrival)
            env.process(passenger())

    env.process(arrivals())
    env.run(until=duration_min)

    if not waits:
        return SimulationResult(
            mean_wait_min=0.0,
            p95_wait_min=0.0,
            max_queue_len=max_queue_len,
            lane_utilisation=0.0,
            sla_breach_min=0,
        )

    lane_utilisation = min(busy_time / (num_lanes * duration_min), 1.0)
    return SimulationResult(
        mean_wait_min=round(float(np.mean(waits)), 3),
        p95_wait_min=round(float(np.percentile(waits, 95)), 3),
        max_queue_len=max_queue_len,
        lane_utilisation=round(lane_utilisation, 3),
        sla_breach_min=len(breach_minutes),
    )
