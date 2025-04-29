"""VirtualProvider module for managing quantum computing providers.

This module provides the VirtualProvider class, which is responsible for
initializing and managing multiple quantum computing providers.
It allows users to retrieve available backends, filter them based on their
online status, and access specific backends by their identifiers.
"""

import logging
from typing import TYPE_CHECKING
from typing import Any

from qbraid.runtime import AzureQuantumProvider  # type: ignore
from qbraid.runtime import BraketProvider
from qbraid.runtime import DeviceStatus
from qbraid.runtime import IonQProvider
from qbraid.runtime import QbraidProvider
from qbraid.runtime import QiskitRuntimeProvider

from quantum_executor.local_aer import LocalAERProvider

if TYPE_CHECKING:  # pragma: no cover
    from qbraid.runtime.device import QuantumDevice  # type: ignore
    from qbraid.runtime.provider import QuantumProvider  # type: ignore

# Configure a module-level logger
logger = logging.getLogger(__name__)

# Define the available providers.
DEFAULT_PROVIDERS: dict[str, Any] = {
    "azure": AzureQuantumProvider,
    "braket": BraketProvider,
    "ionq": IonQProvider,
    "local_aer": LocalAERProvider,
    "qbraid": QbraidProvider,
    "qiskit": QiskitRuntimeProvider,
}


class VirtualProvider:
    """Manage the initialization of quantum computing providers and retrieval of available backends.

    This class is responsible for:
      - Instantiating provider classes using the supplied API keys (if required).
      - Retrieving all available backends from each provider.
      - Optionally filtering backends based on their online status.

    Instead of specifying which providers to exclude, users can now optionally specify a
    list of provider names to include. If the include list is not provided, all available
    providers will be initialized.

    Parameters
    ----------
    providers_info : Dict[str, Dict[str, Any]], optional
        A dictionary mapping provider names to their respective API keys or configuration.
        The keys should be the provider names (e.g., "ionq", "azure") and the values
        should be dictionaries containing the necessary parameters for initialization.
        For example:
            {
                "ionq": {"api_key": "your-api-key-here"},
                "azure": {"subscription_id": "your-subscription-id", "resource_group": "your-resource-group"},
                "braket": {"aws_access_key_id": "your-access-key-id",
                            "aws_secret_access_key": "your-secret-access-key"},
                "local_aer": {},
                "qbraid": {"api_key": "your-api-key-here"},
            }
    include : list[str], optional
        A list of provider names to include in the initialization.
        Only the providers with names in this list will be initialized.
        Defaults to None, meaning all providers are included.
    raise_exc : bool, optional
        If True, exceptions during provider initialization will be propagated.
        Otherwise, the error is logged and initialization continues.
        Defaults to False.

    Examples
    --------
    >>> vp = VirtualProvider(providers_info={"ionq": "your-api-key-here"}, include=["ionq"])
    >>> providers = vp.get_providers()
    >>> backends = vp.get_backends(online=True)

    """

    def __init__(
        self,
        providers_info: dict[str, dict[str, Any]] | None = None,
        include: list[str] | None = None,
        raise_exc: bool = False,
    ) -> None:
        """Initialize VirtualProvider instance with API keys and an optional list of providers to include.

        Parameters
        ----------
        providers_info : Dict[str, Dict[str, Any]], optional
            A dictionary mapping provider names to their respective API keys or configuration.
            The keys should be the provider names (e.g., "ionq", "azure") and the values
            should be dictionaries containing the necessary parameters for initialization.
            For example:
                {
                    "ionq": {"api_key": "your-api-key-here"},
                    "azure": {"subscription_id": "your-subscription-id", "resource_group": "your-resource-group"},
                    "braket": {"aws_access_key_id": "your-access-key-id",
                                "aws_secret_access_key": "your-secret-access-key"},
                    "local_aer": {},
                    "qbraid": {"api_key": "your-api-key-here"},
                }
        include : list[str], optional
            A list of provider names to include in the initialization.
            Only the providers with names in this list will be initialized.
            Defaults to None, meaning all providers are included.
        raise_exc : bool, optional
            If True, exceptions during provider initialization will be propagated;
            otherwise, errors are logged and initialization continues.
            Defaults to False.

        Examples
        --------
        >>> vp = VirtualProvider(providers_info={"ionq": "your-api-key-here"}, include=["ionq"])
        >>> providers = vp.get_providers()
        >>> backends = vp.get_backends(online=True)

        """
        # Normalize API key names to lowercase.
        self._providers_info: dict[str, dict[str, Any]] = providers_info if providers_info is not None else {}
        self._providers_info = {k.lower(): v for k, v in self._providers_info.items()}

        # Determine which providers to include.
        if include is not None and len(include) > 0:
            self._include: list[str] = [p.lower() for p in include]
        else:
            self._include = [provider.lower() for provider in DEFAULT_PROVIDERS]

        # Filter API keys to only include those specified.
        self._providers_info = {k: v for k, v in self._providers_info.items() if k in self._include}

        self._providers: dict[str, Any] = {}
        self._init_providers(raise_exc)

    def _init_providers(self, raise_exc: bool = False) -> None:
        """Initialize provider instances as defined in the global DEFAULT_PROVIDERS dictionary.

        Providers will be instantiated with any provided API keys or configuration.
        Otherwise, the provider is instantiated with its default constructor.

        Parameters
        ----------
        raise_exc : bool, optional
            If True, any exception during initialization will be raised;
            otherwise, errors are logged. Defaults to False.

        """
        if self._include is not None:
            for provider_name in self._include:
                if provider_name not in DEFAULT_PROVIDERS:
                    if raise_exc:
                        raise ValueError(f"Provider '{provider_name}' is not available.")
                    logger.warning("Provider '%s' is not available.", provider_name)

        for provider_name, provider_cls in DEFAULT_PROVIDERS.items():
            # Only initialize providers that are in the include list.
            if provider_name.lower() not in self._include:
                logger.info("Provider '%s' not included in initialization.", provider_name)
                continue
            try:
                if provider_name.lower() in self._providers_info:
                    instance = provider_cls(**self._providers_info[provider_name.lower()])
                else:
                    instance = provider_cls()
                logger.info("Provider '%s' initialized successfully.", provider_name)
                self._providers[provider_name] = instance
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Unable to initialize provider '%s': %s", provider_name, e)
                if raise_exc:
                    raise ValueError(f"Unable to initialize provider {provider_name}") from e

    def get_providers(self) -> dict[str, "QuantumProvider"]:
        """Get the initialized providers.

        Returns
        -------
        dict[str, QuantumProvider]
            A dictionary mapping provider names to their respective provider instances.
            For example:
                {
                    "local_aer": LocalAERProvider(...),
                    "ionq": IonQProvider(...),
                }

        """
        return self._providers.copy()

    def get_backends(self, online: bool = True) -> dict[str, dict[str, "QuantumDevice"]]:
        """Retrieve available backends for each provider.

        The method retrieves devices from each provider and, if requested,
        filters them based on their online status.

        Parameters
        ----------
        online : bool, optional
            If True, only devices with an online status are returned;
            if False, all devices are returned regardless of status.
            Defaults to True.

        Returns
        -------
        Dict[str, Dict[str, QuantumDevice]]
            A dictionary mapping provider names to dictionaries of backend IDs and QuantumDevice
            instances. For example:
                {
                    "local_aer": {
                        "backend_id_1": QuantumDevice(...),
                        "backend_id_2": QuantumDevice(...),
                    },
                    "ionq": { ... },
                }

        """
        results: dict[str, dict[str, QuantumDevice]] = {}
        for provider_name, provider in self._providers.items():
            try:
                raw_backends = provider.get_devices()
                backends: dict[str, QuantumDevice] = {}
                for backend in raw_backends:
                    metadata = backend.metadata()
                    device_id = metadata.get("device_id")
                    if device_id:
                        backends[device_id] = backend
                if online:
                    # Filter the backends to include only those online.
                    filtered_backends = {
                        b_id: bck for b_id, bck in backends.items() if bck.status() == DeviceStatus.ONLINE
                    }
                    results[provider_name] = filtered_backends
                else:
                    results[provider_name] = backends
                logger.info(
                    "Retrieved %d backends from provider '%s'.",
                    len(backends),
                    provider_name,
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Unable to retrieve backends from provider '%s': %s",
                    provider_name,
                    e,
                )
        return results

    def get_backend(self, provider_name: str, backend_name: str, online: bool = True) -> "QuantumDevice":
        """Retrieve a specific backend from the specified provider.

        The method fetches the backend using its identifier and, if required, checks that
        the backend is online. If the provider is not initialized or the backend is offline,
        an error is raised.

        Parameters
        ----------
        provider_name : str
            The name of the provider from which the backend should be retrieved.
        backend_name : str
            The identifier (device_id) of the backend to retrieve.
        online : bool, optional
            If True, raises an error if the backend is not online.
            Defaults to True.

        Returns
        -------
        QuantumDevice
            An instance of the requested backend.

        Raises
        ------
        ValueError
            If the provider with the given name is not initialized.
        RuntimeError
            If the backend is offline when online status is required, or if another error occurs
            during retrieval.

        """
        try:
            provider = self._providers[provider_name]
            backend = provider.get_device(backend_name)
            if online and backend.status() != DeviceStatus.ONLINE:
                raise RuntimeError(f"The backend '{backend_name}' is not online.")
            return backend
        except KeyError as e:
            logger.error("Provider '%s' not found.", provider_name)
            raise ValueError(f"Provider '{provider_name}' not initialized.") from e
        except Exception as e:
            logger.error(
                "Unable to retrieve backend '%s' from provider '%s': %s",
                backend_name,
                provider_name,
                e,
            )
            raise

    def add_provider(self, provider_name: str, provider: "QuantumProvider") -> None:
        """Add a new provider to the list of initialized providers.

        Parameters
        ----------
        provider_name : str
            The name of the provider to add.
        provider : QuantumProvider
            An instance of the provider to add.

        Raises
        ------
        ValueError
            If the provider name is already in use.

        """
        if provider_name in self._providers:
            raise ValueError(f"Provider '{provider_name}' is already initialized.")
        self._providers[provider_name] = provider

    @staticmethod
    def default_providers() -> list[str]:
        """Get a list of default providers.

        Returns
        -------
        List[str]
            A list of provider names that are available for use.

        """
        return list(DEFAULT_PROVIDERS.keys())
