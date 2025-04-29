# 🛠️ How It Works

Quantum Executor is built around a modular, extensible, and provider-agnostic architecture designed for **scalability**, **portability**, and **flexibility**.
It introduces a clean separation of concerns between circuit management, backend dispatching, and result aggregation.

## 🧩 Quantum Executor Components

At a high level, the core components are:

### 🔹 QuantumExecutor

The main orchestrator class that users interact with.

- Manages quantum **providers** (local, cloud, and hardware).
- Provides methods for both **Dispatch Mode** and **Experiment Mode**.
- Supports **synchronous** and **asynchronous** execution with simple parameters (`multiprocess`, `wait`).
- Allows easy registration of custom **Split Policies** and **Merge Policies**.

> 🧠 **Designed for simplicity:** A single object to control everything.

---

### 🔹 Dispatch

The fundamental unit of quantum work.

- Encapsulates a collection of **jobs**, where each job specifies:
  - The **provider**,
  - The **backend**,
  - The **circuit(s)**,
  - The **shots**,
  - (Optional) **Backend configuration parameters** (e.g., random seed, runtime options).
- Supports manual dispatch creation **or** dynamic generation via **Split Policies**.

> 📦 **Flexible by design:** Build dispatches manually or automatically.

---

### 🔹 ResultCollector

Handles the **collection**, **management**, and **polling** of quantum execution results.

- Supports partial result retrieval for **non-blocking executions**.
- Manages **result aggregation** according to user-defined or default **Merge Policies**.
- Provides methods for accessing **raw results** and **merged results**.

> ⏳ **Robust handling:** Supports concurrent executions across multiple backends.

---

### 🔹 Policy System

Quantum Executor introduces a **pluggable policy system** to allow users to control:

- **Split Policies**: How to split quantum experiments among available backends.
- **Merge Policies**: How to combine results from multiple backends into a single output.

Default policies are available, and users can easily register **custom policies** via simple Python functions.

> ⚙️ **Highly customizable:** Fine-tune execution and aggregation strategies for your specific needs.

---

### 🔹 VirtualProvider

An internal abstraction that **wraps** real providers and manages:

- Platform-specific interactions,
- Backend listing and availability,
- Credential management (via `qBraid` and underlying SDKs).

> 🔌 **Provider-independent:** A unified access layer to diverse quantum ecosystems.

---

## 🛠️ Execution Flow Overview

1. **User defines an experiment or dispatch.**
2. **QuantumExecutor** creates a **Dispatch** object (or uses an existing one).
3. **Dispatch** distributes jobs across selected **providers** and **backends**.
4. **ResultCollector** monitors execution (synchronous or asynchronous).
5. (Optional) **Merge Policy** aggregates the results.
6. Final **results** are presented to the user—either raw or merged.

---

## 📚 Technology Stack

- Python 3.12+
- [qBraid SDK](https://www.qbraid.com/)
- Quantum framework such as Qiskit, Cirq, PennyLane, PyQuil, IonQ SDK, and others as optional backend dependencies
- Multiprocessing for parallel execution
- Async and thread-safe result management

---

Quantum Executor’s architecture ensures it is:

- **Lightweight**: No unnecessary overhead.
- **Extensible**: Easy to plug in new providers, policies, or aggregation strategies.
- **Robust**: Built for high-volume experimentation and production workloads.

[← Previous:  Usage Guide](usage.md) | [Next: API Reference →](api/index)
