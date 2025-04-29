# Quantum Executor: A Unified Interface for Quantum Computing

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
[![codecov](https://codecov.io/gh/GBisi/quantum-executor/graph/badge.svg?token=rwQwYpLxXd)](https://codecov.io/gh/GBisi/quantum-executor)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-brightgreen)](https://docs.astral.sh/ruff/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)


**Quantum Executor** is a powerful, extensible, software tool designed to level-up how developers, researchers, and industry practitioners interact with quantum computing platforms. Built on top of [qBraid](https://www.qbraid.com/), Quantum Executor **abstracts away provider-specific complexities**, enabling seamless and scalable quantum experimentation across a diverse landscape of quantum technologies.

## Why Quantum Executor?

### 🧠 The Problem

In today's quantum computing ecosystem, running quantum programs across different providers often means rewriting large portions of your codebase. Even with SDKs that offer multi-provider access, users must typically manage platform-specific objects, languages, and execution paradigms—creating brittle, provider-locked workflows that hinder collaboration, experimentation, and reproducibility.

### 🚀 Our Solution: Unified, Extensible, Scalable

Quantum Executor solves this fragmentation by introducing a **uniform and interchangeable execution interface** that abstracts away provider-specific complexities. With a single, consistent API, you can:

- **Switch platforms and backends without modifying your code**.
- **Parallelize executions** across multiple platforms.
- Run **custom split and merge policies** for dispatching and aggregating quantum results.
- **Perform real-time monitoring and analysis** of your results, even when some of your quantum jobs are still in queue—all while keeping your workflow elegant, portable, and highly maintainable.
- **Easily extend** the Quantum Broker to support new quantum providers.

> 💡 *With Quantum Executor, quantum platform interoperability is not an afterthought—it's the core design principle.*

## ✨ Key Features

Quantum Executor is designed with flexibility, scalability, and usability in mind. It brings a set of powerful features that make it ideal for researchers, developers, and practitioners working across the quantum computing stack.

### ✅ Unified Quantum Execution Layer
Run quantum circuits across different cloud providers and hardware platforms using a single, unified interface. No provider-specific objects. No backend-dependent rewrites. Just seamless interoperability.

Quantum Executor builds on [qBraid](https://www.qbraid.com/) to support all platforms currently integrated with it, and even more, including:
- **Azure Quantum**
- **Amazon Braket**
- **IonQ**
- **Qiskit / IBM Quantum**
- **qBraid Native**
- **Local AER Simulators**

No provider-specific objects. No backend-dependent rewrites. Just seamless interoperability and backend-agnostic execution.

### 🔄 Zero-Code Backend Switching
Change your target device **by configuration**, **not by code refactoring**. Keep your quantum workflow intact while moving between backends.

### ⚙️ Custom Execution Policies
Define your own logic for how and where quantum experiments should run. Whether optimizing for cost, execution time, noise level, or availability, you can control how shots are distributed and how results are aggregated—via a simple user-defined function.

### 🎭 Language-Agnostic by Design
Support for a wide variety of quantum programming languages and circuit formats:
- **Qiskit**
- **Cirq**
- **PennyLane**
- **PyQuil**
- **OpenQASM 2.0 & 3.0**
- **IonQ native format**
...and more!

### 🧵 Asynchronous and Parallel Execution
- Dispatch experiments **asynchronously across multiple providers**.
- **Access partial results** from backends that have completed even if others are still running.
- Monitor and collect live results without blocking your workflow.

### 📦 Cloud-Ready & Hardware-Agnostic
Compatible with both simulators and real quantum hardware, via cloud access to multiple providers. Whether you're testing an algorithm or benchmarking real devices, Quantum Executor adapts to your needs.

### 📊 Results Aggregation & Postprocessing
Gather results from multiple platforms and optionally combine or analyze them using your own aggregation logic. Ideal for ensemble execution, statistical analysis, and benchmarking.

## 🔌 Extensible Provider System
Want to connect a new quantum provider?
**Quantum Executor** is built to be easily extendable. **Reach out to us** if you want your hardware or simulator integrated!

### 🧪 Built for Research & Production
Quantum Executor is designed with reproducibility, modularity, and scientific rigor in mind. It's suitable for academic research, prototyping, benchmarking, and even production workflows in hybrid quantum-classical systems.


## ⚡ Quickstart

Getting started with Quantum Executor is fast and simple. In just a few steps, you’ll be ready to execute your quantum workflows across multiple platforms—locally and in the cloud.

### 🧩 Installation

To install Quantum Executor, simply use `pip`:

```bash
pip install quantum-executor
```
This will automatically install all necessary dependencies, which Quantum Executor builds upon to provide access to a wide range of quantum computing platforms.

> ✅ Note: To use cloud-based providers (e.g., Qiskit, Braket, IonQ), make sure you’ve configured the appropriate credentials via qbraid or the native SDKs. See the [qBraid documentation](https://docs.qbraid.com/sdk/user-guide/overview#local-installation) for platform-specific setup instructions.

## 🛠️ Usage Example

Quantum Executor makes it straightforward to dispatch quantum programs across multiple platforms and backends—without changing your code when switching providers.

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
(For more advanced dynamic dispatching examples, check the [Usage Guide](docs/usage.md)).

We will:
- Run `cirq_circuit` on a local simulator and two IonQ devices,
- Also run `qiskit_circuit` on one IonQ device.

> 💡 In Quantum Executor, the language in which a circuit is defined is completely independent from the backend where it will run.

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

🔬 Dive into our [Usage Guide](docs/usage.md) for a deeper exploration of Quantum Executor’s features, including:
- Advanced dispatching
- How to dynamically split quantum jobs through a split policy
- How to analyse and aggregate quantum results through a merge policy
---

## 🎯 Summary

Quantum Executor provides:
- A high-level, unified interface for executing quantum programs across multiple providers,
- Full backend-agnostic design — **switch platforms without rewriting code**,
- Seamless synchronous or asynchronous execution,
- Advanced dispatching and result aggregation capabilities for maximum flexibility.

Whether you’re a researcher experimenting with quantum algorithms or a developer building production quantum-classical workflows, **Quantum Executor accelerates your journey**.

***✨ Ready to unify your quantum experiments? Install Quantum Executor and start your next quantum project!***
```bash
pip install quantum-executor
```

## 🏛️ Architecture Overview

Curious how it all comes together? Check out the [How It Works](docs/how_it_works.md) section to explore Quantum Executor behind the scenes!

## Contributing

We welcome contributions! Feel free to [open issues](https://github.com/GBisi/quantum-executor/issues), [submit pull requests](https://github.com/GBisi/quantum-executor/pulls), or [suggest improvements](mailto:giuseppe.bisicchia@phd.unipi.it) to help Quantum Executor better serve the quantum computing community.

> 💡 Check out our [Contribution Guidelines](CONTRIBUTING.md) before you start!

---

## Get in Touch

We are excited to see Quantum Executor support your quantum computing journey. For support, feature requests, or discussions, please contact us at:

- **GitHub Issues:** [Quantum Executor Issues](https://github.com/GBisi/quantum-executor/issues)
- **Email:** [giuseppe.bisicchia@phd.unipi.it](mailto:giuseppe.bisicchia@phd.unipi.it)

---

## License
Quantum Executor is released under the **AGPL-3.0** License. See the [LICENSE](LICENSE) for more details.


## Acknowledgments
Quantum Executor leverages the power of existing quantum computing libraries and APIs, notably qBraid, Qiskit, AWS Braket SDK, Azure Quantum SDK, and others. We acknowledge their contributions to the quantum computing ecosystem.

## 📖 How to Cite

If you use **Quantum Executor** in your research, academic work, or commercial projects, please consider to cite us:

> **Quantum Executor: A Unified Interface for Quantum Computing**
> G. Bisicchia
> GitHub Repository: [https://github.com/GBisi/quantum-executor](https://github.com/GBisi/quantum-executor)
> Year: 2025

### 📜 BibTeX Entry

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

## 🌟 Let's Shape the Future of Quantum, Together.

Install it, try it, hack it — and unify your quantum workflows with elegance.

```bash
pip install quantum-executor
```
***Let's quantum innovate, seamlessly!***
