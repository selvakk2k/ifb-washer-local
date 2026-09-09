"""Exceptions for the IFB Washer Local integration and client library."""

from __future__ import annotations


class IFBError(Exception):
    """Base exception for all IFB washer operations."""


class IFBConnectionError(IFBError):
    """Raised when communication with the local washer IP address fails."""


class IFBTimeoutError(IFBConnectionError):
    """Raised when a local HTTP command or query times out."""


class IFBProtocolError(IFBError):
    """Raised when an invalid, corrupted, or unsupported packet is received."""
