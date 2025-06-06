"""
state.py  – stochastic mood integrator for the inflatable sculpture

Implements five “neuro-chemicals”

    FAST  (phasic)        SLOW  (tonic)
    -------------------   -------------------------
    adrenaline            cortisol
    oxytocin              serotonin
    dopamine              –

Every call to Mood.step(dt, stimuli) advances the state by Δt seconds
using an Euler-Maruyama discretisation:

    X ← X + dt*(-X/τ + gain*stim) + σ*sqrt(dt)*𝒩(0,1)

where `stim` comes from sensor fusion (values in 0‒1).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, MutableMapping
import math, random, time


def _clamp01(x: float) -> float:
    """Clamp to [0, 1]."""
    return 0.0 if x < 0 else 1.0 if x > 1 else x


# --------------------------------------------------------------------------- #
#  Mood dataclass
# --------------------------------------------------------------------------- #

@dataclass
class Mood:
    # --- fast transmitters (0‒1) ---
    adrenaline: float = 0.05
    oxytocin:   float = 0.10
    dopamine:   float = 0.10

    # --- slow transmitters (0‒1.2) ---
    cortisol:   float = 0.10
    serotonin:  float = 0.10

    # personality biases ----------------------------------------------------- #
    threat_bias:  float = 0.00    # +ve → more anxious baseline cortisol
    social_bias:  float = 0.00    # +ve → easier oxytocin release

    # internal bookkeeping --------------------------------------------------- #
    _last_ts: float = field(default_factory=time.time, init=False, repr=False)

    # ----------------------------------------------------------------------- #
    #  CONSTANTS (tweak live if desired)
    # ----------------------------------------------------------------------- #

    # decay constants τ  (seconds)
    TAU: Mapping[str, float] = field(default_factory=lambda: {
        'adrenaline': 8.0,
        'oxytocin':  10.0,
        'dopamine':   4.0,
        'cortisol':  60.0,
        'serotonin': 80.0,
    }, init=False)

    # stimulus gains g
    GAIN: Mapping[str, float] = field(default_factory=lambda: {
        'adrenaline': 1.20,
        'oxytocin':   1.00,
        'dopamine':   1.50,
    }, init=False)

    # noise strength σ  (additive Ornstein-Uhlenbeck)
    SIGMA: Mapping[str, float] = field(default_factory=lambda: {
        'adrenaline': 0.03,
        'oxytocin':   0.02,
        'dopamine':   0.02,
        'cortisol':   0.005,
        'serotonin':  0.005,
    }, init=False)

    # ----------------------------------------------------------------------- #
    #  PUBLIC API
    # ----------------------------------------------------------------------- #

    def step(self, dt: float | None = None,
             stimuli: Mapping[str, float] | None = None) -> None:
        """
        Advance state by `dt` seconds (defaults to wall-clock delta)
        using sensor-fusion `stimuli`:

            stimuli = {
                'alarm':       loudness + approach_speed         (0‒1)
                'warmth':      body_softness / friendly motion   (0‒1)
                'novelty':     first-sight spike                 (0‒1)
            }

        Missing keys default to 0.
        """
        now = time.time()
        dt = (now - self._last_ts) if dt is None else dt
        self._last_ts = now

        if dt <= 0.0:
            return  # nothing to do

        # -------- unpack / default stimuli ---------------------------------- #
        s_alarm   = stimuli.get('alarm',   0.0)  if stimuli else 0.0
        s_warmth  = stimuli.get('warmth',  0.0)  if stimuli else 0.0
        s_novelty = stimuli.get('novelty', 0.0)  if stimuli else 0.0

        sqrt_dt = math.sqrt(dt)

        # -------- convenience ------------------------------------------------ #
        def _update(var: str, stim: float) -> float:
            """Euler-Maruyama for one transmitter."""
            x     = getattr(self, var)
            tau   = self.TAU[var]
            gain  = self.GAIN.get(var, 0.0)
            sigma = self.SIGMA[var]
            dx_dt = -x/tau + gain*stim
            x += dt*dx_dt + sigma*sqrt_dt*random.gauss(0.0, 1.0)
            return _clamp01(x)

        # -------- FAST CHEMISTRY -------------------------------------------- #
        self.adrenaline = _update('adrenaline', s_alarm)
        self.oxytocin   = _update('oxytocin',   s_warmth * (1.0 + self.social_bias))
        self.dopamine   = _update('dopamine',   s_novelty)

        # -------- SLOW CHEMISTRY (integrate fast) --------------------------- #
        #   Cortisol <- integrates *excess* adrenaline
        excess_adren = max(self.adrenaline - 0.30, 0.0)
        self.cortisol  = _clamp01(
            self.cortisol
            + dt*(-self.cortisol/self.TAU['cortisol']
                  + 0.50*excess_adren
                  + self.threat_bias)
            + self.SIGMA['cortisol']*sqrt_dt*random.gauss(0,1)
        )

        #   Serotonin <- integrates *excess* oxytocin
        excess_oxy = max(self.oxytocin - 0.30, 0.0)
        self.serotonin = max(0.0, min(1.2,  # tonic variables may exceed 1
            self.serotonin
            + dt*(-self.serotonin/self.TAU['serotonin']
                  + 0.40*excess_oxy)
            + self.SIGMA['serotonin']*sqrt_dt*random.gauss(0,1)
        ))

        # -------- cross-couplings ------------------------------------------- #
        #   Stress blunts warmth
        if self.cortisol > 0.6:
            self.oxytocin *= 0.95

        #   Safety damps alarm reactivity
        if self.serotonin > 0.5:
            self.adrenaline *= 0.97

    # ----------------------------------------------------------------------- #
    #  HIGH-LEVEL “FEELING” PROPERTIES
    # ----------------------------------------------------------------------- #
    @property
    def is_calm(self) -> bool:
        return self.cortisol < 0.25 and self.adrenaline < 0.20

    @property
    def is_stressed(self) -> bool:
        return self.cortisol > 0.60 or self.adrenaline > 0.50

    @property
    def snapshot(self) -> MutableMapping[str, float]:
        """Return a dict copy (handy for logging or OSC)."""
        return {
            'adrenaline': self.adrenaline,
            'oxytocin':   self.oxytocin,
            'dopamine':   self.dopamine,
            'cortisol':   self.cortisol,
            'serotonin':  self.serotonin,
        }
