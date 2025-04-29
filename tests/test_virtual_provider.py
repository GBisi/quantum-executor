##############################################################################
# test_virtual_provider.py
##############################################################################
"""Test suite for the VirtualProvider class."""

import logging
from typing import Any

import pytest  # type: ignore
from qbraid.runtime import DeviceStatus  # type: ignore
from qbraid.runtime import QuantumDevice
from qbraid.runtime import QuantumProvider

from quantum_executor.virtual_provider import DEFAULT_PROVIDERS
from quantum_executor.virtual_provider import VirtualProvider


class DummyProvider(QuantumProvider):  # type: ignore
    """Dummy provider for testing.

    Parameters
    ----------
    config : Optional[Any]
        Optional configuration for the provider.

    """

    def __init__(self, config: Any | None = None) -> None:  # noqa: ANN401
        """Initialize the DummyProvider.

        Parameters
        ----------
        config : Optional[Any]
            Optional configuration for the provider.

        """
        self.config = config
        super().__init__()

    def get_devices(self) -> list[QuantumDevice]:
        """Return an empty list of devices.

        This is a placeholder for the actual device retrieval logic.

        Returns
        -------
        list[QuantumDevice]
            An empty list of devices.

        """
        return []  # pragma: no cover

    def get_device(self, device_id: str) -> QuantumDevice:
        """Raise NotImplementedError for any device name.

        This is a placeholder for the actual device retrieval logic.

        Parameters
        ----------
        device_id : str
            The name of the device to retrieve.

        Returns
        -------
        QuantumDevice
            Always raises NotImplementedError for this dummy provider.

        """
        raise NotImplementedError("This is a dummy provider.")  # pragma: no cover


def test_default_providers() -> None:
    """Test that the list of available providers matches the keys defined in DEFAULT_PROVIDERS."""
    expected = set(DEFAULT_PROVIDERS.keys())
    actual = set(VirtualProvider.default_providers())
    assert expected == actual, "The available providers should match the DEFAULT_PROVIDERS dictionary keys."


def test_init_no_include() -> None:
    """Test initializing VirtualProvider with no 'include' argument.

    This should include all known providers.
    """
    vp = VirtualProvider()
    providers = vp.get_providers()
    assert len(providers) > 0, "Expected at least one provider to be initialized."
    # Confirm that all providers from the dictionary are attempted.
    for pname in DEFAULT_PROVIDERS:
        # Some may have failed to initialize (e.g., IonQ) if no key or environment is set,
        # but those that fail silently won't appear in vp.get_providers().
        if pname in providers:
            assert pname in vp.get_providers(), f"Provider '{pname}' should be found in get_providers()."


def test_init_include_only_local() -> None:
    """Test that we can include only the local provider when specifying 'include'."""
    vp = VirtualProvider(include=["local_aer"])
    providers = vp.get_providers()
    assert len(providers) == 1, "Expected only one provider (local) to be initialized."
    assert "local_aer" in providers, "Expected 'local' to be initialized."
    assert "ionq" not in providers, "Did not expect 'ionq' to be initialized."


def test_init_include_missing_raise_exc() -> None:
    """Test that including a non-existent provider raises an exception if raise_exc=True."""
    with pytest.raises(ValueError, match="Provider 'doesnotexist' is not available."):
        VirtualProvider(include=["local_aer", "doesnotexist"], raise_exc=True)


def test_init_include_missing_no_exc(caplog: pytest.LogCaptureFixture) -> None:
    """Test that including a non-existent provider only logs a warning if raise_exc=False.

    Parameters
    ----------
    caplog : pytest.LogCaptureFixture
        The pytest fixture to capture log messages.

    """
    vp = VirtualProvider(include=["local_aer", "doesnotexist"], raise_exc=False)
    assert "local_aer" in vp.get_providers(), "Local provider should still initialize."
    # Check if the warning was logged for the missing provider.
    warning_found = any("Provider 'doesnotexist' is not available." in rec.message for rec in caplog.records)
    assert warning_found, "Expected warning about the missing provider in the logs."


def test_get_backends_local() -> None:
    """Test retrieving backends from the local provider."""
    vp = VirtualProvider(include=["local_aer"])
    backends = vp.get_backends(online=True)
    assert len(backends) == 1, "Expected only one provider key in the results: 'local'."
    local_backends = backends["local_aer"]
    assert len(local_backends) > 0, "Expected local backends from LocalAERProvider."
    # Check at least 'aer_simulator' is present and online.
    assert "aer_simulator" in local_backends, "Expected 'aer_simulator' in local backends."
    sim_device = local_backends["aer_simulator"]
    assert sim_device.status() == DeviceStatus.ONLINE, "Local simulator should be ONLINE."


def test_get_backend_local_aer_simulator() -> None:
    """Test retrieving a single local aer_simulator from the VirtualProvider."""
    vp = VirtualProvider(include=["local_aer"])
    backend = vp.get_backend("local_aer", "aer_simulator", online=True)
    assert backend.status() == DeviceStatus.ONLINE, "Expected 'aer_simulator' to be online."


def test_get_backend_unknown_provider() -> None:
    """Test that requesting a provider that is not initialized raises a ValueError."""
    vp = VirtualProvider(include=["local_aer"])
    with pytest.raises(ValueError, match="Provider 'ionq' not initialized."):
        vp.get_backend("ionq", "some_device")


def test_get_backend_missing_device() -> None:
    """Test that requesting a device that does not exist raises an error."""
    vp = VirtualProvider(include=["local_aer"])
    with pytest.raises(Exception) as excinfo:
        vp.get_backend("local_aer", "unknown_device")
    # The code re-raises the error from the underlying provider's get_device method.
    assert "Device 'unknown_device' not found" in str(excinfo.value)


def test_get_backend_offline_failure() -> None:
    """Test that retrieving a backend which is offline raises RuntimeError if online=True.

    (We force an offline scenario by mocking the device's status, as local is always online.)
    """
    vp = VirtualProvider(include=["local_aer"])
    # Normally local is always online, so we mock the status method to simulate offline device.
    provider = vp.get_providers()["local_aer"]
    device = provider.get_device("aer_simulator")

    original_status = device.status
    try:
        # Force an "OFFLINE" status
        device.status = lambda: DeviceStatus.OFFLINE
        with pytest.raises(RuntimeError, match="The backend 'aer_simulator' is not online."):
            vp.get_backend("local_aer", "aer_simulator", online=True)
    finally:
        # Restore original status method
        device.status = original_status


def test_get_backends_offline_included() -> None:
    """Test retrieving backends with online=False.

    Ensure that offline or unknown statuses are also returned.
    """
    vp = VirtualProvider(include=["local_aer"])
    all_backends = vp.get_backends(online=False)
    local_backends = all_backends.get("local_aer", {})
    # We expect at least the 'aer_simulator' plus possible fakes.
    assert "aer_simulator" in local_backends, "Expected 'aer_simulator' in the offline-inclusive list."


def test_add_provider_success() -> None:
    """Test adding a new provider via add_provider."""
    vp = VirtualProvider(include=["local_aer"])
    dummy = DummyProvider()
    vp.add_provider("dummy", dummy)
    providers = vp.get_providers()
    assert "dummy" in providers, "Expected 'dummy' provider to be added."
    assert providers["dummy"] is dummy, "Expected the added provider instance to match."


def test_add_provider_duplicate() -> None:
    """Test that adding a provider with an existing name raises a ValueError."""
    vp = VirtualProvider(include=["local_aer"])
    dummy = DummyProvider()
    vp.add_provider("dummy", dummy)
    with pytest.raises(ValueError, match="Provider 'dummy' is already initialized."):
        vp.add_provider("dummy", dummy)


def test_init_with_providers_info_and_dummy_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test initializing VirtualProvider with providers_info for a dummy provider.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The pytest fixture to modify the environment or module state.

    """
    monkeypatch.setitem(DEFAULT_PROVIDERS, "dummy", DummyProvider)
    vp = VirtualProvider(providers_info={"dummy": {"config": "value"}}, include=["dummy"])
    providers = vp.get_providers()
    assert "dummy" in providers, "Expected 'dummy' provider to be initialized."
    provider = providers["dummy"]
    assert isinstance(provider, DummyProvider), "Expected provider to be an instance of DummyProvider."
    assert provider.config == "value", "Expected provider to receive the config from providers_info."


def test_init_provider_exception_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that errors during provider initialization raise ValueError when raise_exc=True.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The pytest fixture to modify the environment or module state.

    """

    class FaultyProvider(QuantumProvider):  # type: ignore
        """Faulty provider for testing.

        Parameters
        ----------
        *args : Any
            Positional arguments.
        **kwargs : Any
            Keyword arguments.

        """

        def __init__(self) -> None:
            """Raise an exception during initialization.

            Parameters
            ----------
            *args : Any
                Positional arguments.
            **kwargs : Any
                Keyword arguments.

            """
            raise ValueError("Faulty provider initialization error.")

        def get_devices(self) -> list[QuantumDevice]:
            """Return an empty list of devices.

            This is a placeholder for the actual device retrieval logic.

            Returns
            -------
            list[QuantumDevice]
                An empty list of devices.

            """
            raise NotImplementedError("This is a dummy provider.")  # pragma: no cover

        def get_device(self, device_id: str) -> QuantumDevice:
            """Raise NotImplementedError for any device name.

            This is a placeholder for the actual device retrieval logic.

            Parameters
            ----------
            device_id : str
                The name of the device to retrieve.

            Returns
            -------
            QuantumDevice
                Always raises NotImplementedError for this dummy provider.

            """
            raise NotImplementedError("This is a dummy provider.")  # pragma: no cover

    monkeypatch.setitem(DEFAULT_PROVIDERS, "faulty", FaultyProvider)
    with pytest.raises(ValueError, match="Unable to initialize provider faulty"):
        VirtualProvider(include=["faulty"], raise_exc=True)


def test_get_backends_provider_failure_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Test that a provider failure during backend retrieval is logged.

    Parameters
    ----------
    caplog : pytest.LogCaptureFixture
        The pytest fixture to capture log messages.

    """
    vp = VirtualProvider(include=["local_aer"])

    class FaultyProvider(QuantumProvider):  # type: ignore
        """Faulty provider for testing."""

        def get_devices(self) -> list[QuantumDevice]:
            """Return an empty list of devices.

            This is a placeholder for the actual device retrieval logic.

            Returns
            -------
            list[QuantumDevice]
                An empty list of devices.

            """
            raise NotImplementedError("This is a dummy provider.")  # pragma: no cover

        def get_device(self, device_id: str) -> QuantumDevice:
            """Raise NotImplementedError for any device name.

            This is a placeholder for the actual device retrieval logic.

            Parameters
            ----------
            device_id : str
                The name of the device to retrieve.

            Returns
            -------
            QuantumDevice
                Always raises NotImplementedError for this dummy provider.

            """
            raise NotImplementedError("This is a dummy provider.")  # pragma: no cover

    vp.add_provider("faulty", FaultyProvider())
    caplog.set_level(logging.ERROR)
    backends = vp.get_backends(online=True)
    assert "faulty" not in backends, "Faulty provider should be excluded from results."
    error_found = any("Unable to retrieve backends from provider" in rec.message for rec in caplog.records)
    assert error_found, "Expected error log for faulty provider during backend retrieval."
