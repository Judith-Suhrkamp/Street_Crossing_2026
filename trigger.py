"""
trigger.py
----------
Handles synchronization with external hardware.

Current implementation:
    Dummy trigger returning timestamps.

Future implementations:                         # Now handled by the QTMReader class. Only use for dummy coding
    - Qualisys
    - Serial Port
    - Parallel Port
    - Lab Streaming Layer (LSL)
"""

from __future__ import annotations
import time
from config import config
import pygame

class Trigger:
    """
    Trigger interface.

    Currently acts as a dummy trigger by returning timestamps.
    """

    def __init__(self):

        self.enabled = config.use_trigger

    # --------------------------------------------------------

    def wait_for_trigger(self) -> float:
        """
        Wait for an external trigger.

        Returns
        -------
        float
            Timestamp of the trigger.
        """
        # Test run without trigger
        if not self.enabled:
           return time.perf_counter()
        
        quit_key = pygame.key.key_code(config.quit_key)
        trigger_key = pygame.key.key_code(config.trigger_key)

        while True:
        # ----------------------------------------------------
        # Wait for Qualisys trigger here.
        # ----------------------------------------------------
            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    raise SystemExit

                if event.type == pygame.KEYDOWN:

                    if event.key == quit_key:
                        raise SystemExit
                    
                    if event.key == trigger_key:
                        return time.perf_counter()
            time.sleep(0.1)
    # --------------------------------------------------------

    def send_trigger(self) -> float:
        """
        Send a trigger to external hardware.

        Returns
        -------
        float
            Timestamp when the trigger was sent.
        """

        if not self.enabled:
            return time.perf_counter()

        # ----------------------------------------------------
        # Future implementation
        #
        # Example:
        # port.write(...)
        #
        # or
        #
        # parallel.setData(...)
        # ----------------------------------------------------

        return time.perf_counter()

    # --------------------------------------------------------

    def close(self):
        """
        Close trigger connection.
        """

        pass