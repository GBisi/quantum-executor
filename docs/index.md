# Quantum Executor Documentation

Welcome 👋 to the official documentation of **Quantum Executor**! 🚀

---

***Quantum Executor** is a powerful, extensible tool designed to unify how developers, researchers, and industry practitioners interact with quantum computing platforms.*

Whether you are a researcher, developer, student, or industry practitioner, Quantum Executor provides a seamless and elegant interface to dispatch, manage, and aggregate quantum computations across multiple providers and platforms — with no code rewriting, no provider lock-in, and full control over advanced workflows.

🧠 For a full project description, visit the [GitHub Repository](https://github.com/GBisi/quantum-executor).

---

## ✨ Key Features

- ✅ **Unified Execution Interface:** One simple, backend-agnostic API for all your quantum needs.
- 🔄 **Zero-Code Backend Switching:** Adjust quantum backends purely through configuration—never refactor again.
- ⚙️ **Declarative Workflow Management:** Define quantum workflows in a clear, declarative style—no backend complexity.
- 🧪 **Advanced Dispatching:** Easily split and manage quantum experiments across multiple providers and backends.
- 📊 **Real-Time Monitoring:** Track experiments live and access partial results immediately.
- 🔌 **Extensible by Design:** Effortlessly integrate new quantum providers as your needs evolve.

*Portable, modular, backend-agnostic quantum computing — by design.*

---

## 🚀 Quickstart

Getting started with Quantum Executor is fast and simple. In just a few steps, you'll be ready to execute your quantum workflows across multiple platforms—locally and in the cloud.

### 🔍 Installation

Install Quantum Executor via pip:

```bash
pip install quantum-executor
```

✅ Ensure cloud credentials are configured via [qBraid](https://docs.qbraid.com/sdk/user-guide/overview#local-installation) or provider-specific SDKs.

### 📚 Usage Examples

Quantum Executor allows you to:
- Dispatch quantum jobs across multiple providers
- Execute circuits asynchronously or synchronously, and monitor them in real-time
- Aggregate and analyse results with customizable policies

Let's see a small, full working example to appreciate its power.

### ⚙️ Setting Up a Quantum Workflow

We will:

- Create circuits in **Qiskit** and **Cirq**,
- Run them on **local simulators** and **IonQ devices**,
- Launch everything **asynchronously** through a **unified interface**.

```python
from qiskit import QuantumCircuit
import cirq

# Qiskit circuit
qiskit_circuit = QuantumCircuit(2)
qiskit_circuit.h(0); qiskit_circuit.cx(0, 1); qiskit_circuit.measure_all()

# Cirq circuit
q0, q1 = cirq.LineQubit.range(2)
cirq_circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1))
```
Now we’ll define a custom manual dispatch to describe where and how to run each circuit, in a declarative-style.
(For more advanced dynamic dispatching examples, check the [Usage Guide](usage)).

We will:
- Run `cirq_circuit` on a local simulator and two IonQ devices,
- Also run `qiskit_circuit` on one IonQ device.

💡 In Quantum Executor, the language in which a circuit is defined is completely independent from the backend where it will run.

```python
# Define the dispatch
dispatch = {
    "local_aer": {  # Local Aer provider
        "aer_simulator": [
            {"circuit": cirq_circuit, "shots": 2048},
        ],
    },
    "ionq": {  # IonQ cloud provider
        "qpu.forte-1": [
            {"circuit": cirq_circuit, "shots": 1024},
            {"circuit": qiskit_circuit, "shots": 1024},
        ],
        "qpu.aria-1": [
            {"circuit": cirq_circuit, "shots": 4096},
        ],
    }
}
```
Quantum Executor allows you to choose between synchronous or asynchronous, blocking or non-blocking execution with just two parameters.

```python
# Import QuantumExecutor
from quantum_executor import QuantumExecutor

# Initialize the QuantumExecutor
executor = QuantumExecutor()

# Run the dispatch asynchronously and non-blocking
results = executor.run_dispatch(
    dispatch=dispatch,
    multiprocess=True,  # Multi-process execution
    wait=False          # Non-blocking call
)
```
In this example:
- The three quantum backends (`aer_simulator`, `forte-1`, and `aria-1`) will run their jobs in parallel.
- On `forte-1`, the two circuits (`cirq_circuit` and `qiskit_circuit`) will be executed sequentially.

Because devices may have different run times, Quantum Executor lets you gather available results progressively, even while some jobs are still running.

```python
# Get all available results
results.get_results()
```
This retrieves all finished results immediately, without waiting for all jobs to complete.

### ☁️ Moving the Workflow to the Cloud

If you want to move your entire workflow to the cloud (e.g., IBM Quantum), **you only need to modify the dispatch** — the rest of your code remains unchanged.

```python
dispatch = {
    "qiskit": {  # IBM Cloud Provider
        "ibm_torino": [
            {"circuit": cirq_circuit, "shots": 2048},
        ],
    },
    "ionq": {
        "qpu.forte-1": [
            {"circuit": cirq_circuit, "shots": 1024},
            {"circuit": qiskit_circuit, "shots": 1024},
        ],
        "qpu.aria-1": [
            {"circuit": cirq_circuit, "shots": 4096},
        ],
    }
}
```
Everything else stays the same — a fully **declarative workflow**!

---

### 🎯 Summary

Quantum Executor provides:
- A high-level, unified interface for executing quantum programs across multiple providers,
- Full backend-agnostic design — **switch platforms without rewriting code**,
- Seamless synchronous or asynchronous execution,
- Advanced dispatching and result aggregation capabilities for maximum flexibility.

Whether you’re a researcher experimenting with quantum algorithms or a developer building production quantum-classical workflows, **Quantum Executor accelerates your journey**.

🔬 For more advanced examples, see the , including:
Dive into our [Usage Guide](usage) for a more in-depth exploration of the Quantum Executor's capabilities, including:
- Advanced dispatching
- How to dynamically split quantum jobs through a split policy
- How to analyse and aggregate quantum results through a merge policy

🔎 For an in-depth architectural breakdown, visit [How It Works](how_it_works).

---

## 💌 Get Involved

We welcome contributions, feature requests, and feedback!

- 💻 [GitHub Repository](https://github.com/GBisi/quantum-executor)
- 📧 Email: [giuseppe.bisicchia@phd.unipi.it](mailto:giuseppe.bisicchia@phd.unipi.it)

Check out our [Contributing Guide](https://github.com/GBisi/quantum-executor/blob/main/CONTRIBUTING.md) to get started.

---

## 📖 Citing Quantum Executor

If you use **Quantum Executor** in your research or projects, please consider to cite us:

```bibtex
@misc{quantumexecutor2025,
  title        = {Quantum Executor: A Unified Interface for Quantum Computing},
  author       = {Giuseppe Bisicchia},
  year         = {2025},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/GBisi/quantum-executor}},
}
```
---

## ⚖️ License

Quantum Executor is open-sourced under the [AGPL-3.0 License](https://github.com/GBisi/quantum-executor/blob/main/LICENSE).

🎉 **Join us in shaping the future of quantum computing—**[**start today!**](https://github.com/GBisi/quantum-executor)

---

## 📖 Contents

```{toctree}
:maxdepth: 2
:caption: Contents

home_redirect
usage
how_it_works
api/index
```
---

[Next: Usage Guide →](usage)
