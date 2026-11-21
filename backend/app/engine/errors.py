"""Provider failures for the retrieval engine."""


class ProviderError(RuntimeError):
    """A model provider was misconfigured or returned an unusable response."""
