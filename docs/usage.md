
# 📖 Usage Guide

> *Last updated: 29 April 2025*
> This document is an extended walkthrough of every major feature of **Quantum Executor** (QE).
> All examples are executable: open the companion *Usage Guide* notebook in the repository and run the cells line‑by‑line.

---

## 📑 Table of Contents
1. [Installation & Prerequisites](#installation--prerequisites)
2. [Initializing the Quantum Executor](#initializing-the-quantum-executor)
3. [Inspecting Providers & Backends](#inspecting-providers--backends)
4. [Preparing a Dispatch](#preparing-a-dispatch)
   1. [Creating Circuits](#creating-circuits)
   2. [Declarative Dispatch (dict‑style)](#declarative-dispatch-dict-style)
   3. [Programmatic Dispatch (`Dispatch` class)](#programmatic-dispatch-dispatch-class)
5. [Running a Dispatch](#running-a-dispatch)
   1. [Blocking vs Non‑Blocking](#blocking-vs-non-blocking)
   2. [Understanding the `ResultCollector`](#understanding-the-resultcollector)
6. [Designing Split Policies](#designing-split-policies)
7. [Aggregating Data with Merge Policies](#aggregating-data-with-merge-policies)
8. [Advanced Topics](#advanced-topics)

---

## ⚙️ Installation & Prerequisites

```bash
# Recommended: create and activate a fresh virtual‑environment first
python3 -m venv qexec_env && source qexec_env/bin/activate

pip install quantum-executor     # installs QE and core dependencies
# Optional extras for provider SDKs – install only those you need
pip install 'quantum-executor[azure,braket,ionq,qiskit]'
```

> **Python ≥ 3.10** is required.
> Each *cloud* provider (Azure Quantum, Amazon Braket, IonQ, etc.) expects credentials.
> Consult their docs for environment‑variable names, or use QE's `providers_info` parameter (see below).

---

## 🔌 Initializing the Quantum Executor

```python
from quantum_executor import QuantumExecutor

# Show providers that QE can configure out‑of‑the‑box
print(QuantumExecutor.default_providers())
```

```python
['azure', 'braket', 'ionq', 'local_aer', 'qbraid', 'qiskit']
```

### Minimal initialization

```python
executor = QuantumExecutor()          # tries to init **all** providers
```

### Selective initialization

```python
import os
executor = QuantumExecutor(
    providers=["local_aer", "ionq", "azure"],   # use only this subset
    providers_info={
        # Secrets *never* hard‑code them – read from env‑vars or vault instead
        "ionq": {"api_key": os.getenv("IONQ_API_KEY")},
        "azure": {"resource_id": "<GUID>", "location": "westus2"},
    },
)
```

*QE* internally creates a **`VirtualProvider`** that proxies calls to the real SDKs, giving you a *uniform* API across vendors.

---

## 🔎 Inspecting Providers & Backends

```python
# Which providers were successfully configured?
executor.virtual_provider.get_providers()
```

```python
['local_aer', 'ionq', 'azure']
```

```python
# All backends, grouped by provider
from pprint import pprint
pprint(executor.virtual_provider.get_backends())
```

```python
{
 'local_aer': ['aer_simulator', 'fake_torino', ...],
 'ionq':      ['simulator', 'qpu'],
 'azure':     [...]
```

---

## 📦 Preparing a Dispatch
A **Dispatch** is a declarative map that tells QE *what* to run *where*.
Think of it as the “execution plan” for your experiment.

### Creating Circuits

```python
from qiskit import QuantumCircuit

# -- Qiskit circuit (2‑qubit Bell state) --------------------------
qiskit_circuit = QuantumCircuit(2, 2)
qiskit_circuit.h(0)
qiskit_circuit.cx(0, 1)
qiskit_circuit.measure_all()

# -- OPENQASM 2.0 equivalent -------------------------------------
openqasm_circuit = '''
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q -> c;
'''
```

> **Language‑agnostic**: QE will transpile/convert circuits if a backend requires a specific IR.

### Declarative Dispatch (dict‑style)

```python
dispatch = {
    "local_aer": {
        "fake_torino": [
            {   # Job #1
                "circuit": qiskit_circuit,
                "shots":   1024,
                "config":  {"seed": 42},  # passed verbatim to the SDK
            },
            {   # Job #2
                "circuit": openqasm_circuit,
                "shots":   2048,
            }
        ],
        "aer_simulator": [
            {   # Job #3
                "circuit": qiskit_circuit,
                "shots":   1024,
                "config":  {"seed": 24},
            }
        ],
    },
    "ionq": {
        "simulator": [
            {   # Job #4
                "circuit": qiskit_circuit,
                "shots":   1024,
                "config":  {"noise": {"model": "aria-1"}},
            }
        ]
    }
}
```

*Diagram of relationships*

```
provider ─┬─ backend ─┬─ Job 1
          │           └─ Job 2
          └─ backend ─┬─ Job 3
                      └─ ...
```

### Programmatic Dispatch (`Dispatch` class)

When the set of jobs is *dynamic* (e.g., produced in a loop or by a heuristic), the `Dispatch` helper is clearer:

```python
from quantum_executor import Dispatch

dispatch = Dispatch()   # empty container

dispatch.add_job("local_aer", "fake_torino", qiskit_circuit,
                 shots=1024, config={"seed": 42})
dispatch.add_job("local_aer", "fake_torino", openqasm_circuit,
                 shots=2048, config={"seed": 24})
dispatch.add_job("local_aer", "aer_simulator", qiskit_circuit, shots=1024)
dispatch.add_job("ionq", "simulator", qiskit_circuit,
                 shots=1024, config={"noise": {"model": "aria-1"}})

print(dispatch)
```

```python
Dispatch({
  'local_aer': {
     'fake_torino': [
        Job(id='0ca2e105‑...', circuit_type=QuantumCircuit, shots=1024, config={'seed': 42}),
        Job(id='9f16ea90‑...', circuit_type=str,           shots=2048, config={'seed': 24})
     ],
     'aer_simulator': [
        Job(id='10803529‑...', circuit_type=QuantumCircuit, shots=1024, config={})
     ]
  },
  'ionq': {
     'simulator': [
        Job(id='125f447b‑...', circuit_type=QuantumCircuit, shots=1024,
            config={'noise': {'model': 'aria-1'}})
     ]
  }
})
```

---

## 🚀 Running a Dispatch

```python
results = executor.run_dispatch(
    dispatch,
    multiprocess=True,   # one Python process **per backend**
    wait=True            # block until *all* jobs finish
)
```

### Blocking vs Non‑Blocking

| `wait` | Return immediately? | Use‑case                                   |
| ------ | ------------------- | ----------------------------------------- |
| `True` | ❌ (no)             | Simple scripts, CI pipelines              |
| `False`| ✅ (yes)            | Long‑running experiments, dashboards      |

```python
async_results = executor.run_dispatch(dispatch, multiprocess=True, wait=False)
print(async_results)
```

```python
ResultCollector(complete_jobs=0, total_jobs=4, complete=False)
```

Call `async_results.complete` or `async_results.wait_for_completion()` whenever you need to synchronize.

### Understanding the `ResultCollector`

Internally it mirrors the *shape* of the original dispatch:

```python
from pprint import pprint
pprint(results.get_jobs())
```

```python
{
 'local_aer': {
   'fake_torino': [
      JobResult(job=Job(id='c7c59f83‑...', circuit_type=QuantumCircuit, shots=1024, config={'seed':42}),
                status=Complete,
                data={'00': 489, '01': 10, '10': 7, '11': 518}),
      JobResult(job=Job(id='45e7b013‑...', circuit_type=str, shots=2048, config={'seed':24}),
                status=Complete,
                data={'00': 1041, '01': 34, '10': 16, '11': 957})
   ],
   'aer_simulator': [
      JobResult(job=Job(id='d6adfc07‑...', circuit_type=QuantumCircuit, shots=1024, config={'seed':24}),
                status=Complete,
                data={'00': 507, '11': 517})
   ]
 },
 'ionq': {
   'simulator': [
      JobResult(job=Job(id='cdcbf866‑...', circuit_type=QuantumCircuit, shots=1024,
                        config={'noise': {'model':'aria-1'}}),
                status=Complete,
                data={'00': 512, '11': 512})
   ]
 }
}
```

Accessors:

```python
results.get_results()          # dict[str, dict[str, list[dict[str,int]]]]
results.get_jobs()             # same shape but `JobResult` objects
```

---

## ⚖️ Designing Split Policies

Sometimes *one* logical experiment needs to be fanned‑out to many backends.
A **split policy** encapsulates that decision. It must implement:

```python
def split(
    circuit: Any,
    shots: int,
    backends: dict[str, list[str]],
    virtual_provider: VirtualProvider,
    policy_data: Any | None = None,
) -> tuple[Dispatch, Any]:
    ...
```

> **Parameters**
> • `circuit`: single circuit object (any dialect).
> • `shots`: total shots requested by the user.
> • `backends`: the *allow‑list* of backends the executor may use.
> • `virtual_provider`: for querying capabilities, qubit counts, etc.
> • `policy_data`: optional *state* carried across invocations (e.g., for adaptive policies).

### Example — Even‑Split Policy

```python
from typing import Any
from quantum_executor.dispatch import Dispatch
from quantum_executor.virtual_provider import VirtualProvider

def split(
    circuit: Any,
    shots: int,
    backends: dict[str, list[str]],
    virtual_provider: VirtualProvider,
    policy_data: Any | None = None,
) -> tuple[Dispatch, Any]:
    '''
    Distribute `shots` as evenly as possible over all candidate backends.
    '''
    num_backends = sum(map(len, backends.values()))
    base, remainder = divmod(shots, num_backends)

    # Pre‑compute the shot allocation
    allocation = [base + (1 if i < remainder else 0)
                  for i in range(num_backends)]

    dispatch = Dispatch()
    idx = 0
    for provider_name, backend_list in backends.items():
        for backend_name in backend_list:
            dispatch.add_job(
                provider_name=provider_name,
                backend_name=backend_name,
                circuits=circuit.copy(),   # avoid state‑sharing
                shots=allocation[idx],
            )
            idx += 1

    return dispatch, policy_data
```

Register & run:

```python
executor.add_policy("even_split", split)

results = executor.run_experiment(
    circuit=qiskit_circuit,
    shots=1024,
    backends={
        "local_aer": ["fake_torino", "aer_simulator"],
        "ionq":      ["simulator"],
    },
    split_policy="even_split",
    multiprocess=True,
    wait=True,
)
```

```python
ResultCollector({
  'local_aer': {
    'fake_torino': [
      JobResult(...shots=342, data={'00': 150, '01': 4, '10': 5, '11': 183})
    ],
    'aer_simulator': [
      JobResult(...shots=341, data={'00': 173, '11': 168})
    ]
  },
  'ionq': {
    'simulator': [
      JobResult(...shots=342, data={'00': 171, '11': 171})
    ]
  }
})
```

---

## 📊 Aggregating Data with Merge Policies

A **merge policy** post‑processes raw job outputs into an *experiment‑level* result.

```python
def merge(
    results: dict[str, dict[str, list[ResultData]]],
    policy_data: Any,
) -> tuple[Any, Any]:
    ...
```

Where **`ResultData`** is typically a `dict[str, int]` mapping bit‑strings to counts.

### Example — Sum Frequencies

```python
from quantum_executor.job_runner import ResultData

def merge_sum(
    results: dict[str, dict[str, list[ResultData]]],
    policy_data: Any,
) -> tuple[dict[str, int], Any]:
    merged: dict[str, int] = {}
    for provider_results in results.values():
        for backend_results in provider_results.values():
            for data in backend_results:
                for bitstring, count in data.items():
                    merged[bitstring] = merged.get(bitstring, 0) + count
    return merged, policy_data
```

```python
executor.add_policy("sum_freqs", merge_policy=merge_sum)

merged_results = executor.run_dispatch(
    dispatch,
    multiprocess=True,
    wait=True,
    merge_policy="sum_freqs",
)

print(merged_results)
```

```python
MergedResultCollector(
  merged_results = {'00': 2561, '01': 33, '10': 40, '11': 2486},
  initial_policy_data = {},
  final_policy_data   = {}
)
```

### `MergedResultCollector` extras

| Method                         | Purpose                                   |
| ------------------------------ | ----------------------------------------- |
| `get_merged_results()`         | Return whatever the merge policy emitted  |
| `get_initial_policy_data()`    | Any *seed* or *state* passed **in**       |
| `get_final_policy_data()`      | The policy’s updated state **out**        |

---

## 🔥 Advanced Topics

### Multiprocessing Strategies
* `multiprocess=False` – simpler debugging, serial execution.
* `multiprocess=True`  – one worker per backend; beware of pickling limits.

### Provider‑Specific Configuration
Some providers accept extra fields inside the `config` dict:

| Provider | Key             | Example                                              |
| -------- | --------------- | ---------------------------------------------------- |
| IonQ     | `noise`         | `{"model":"aria-1"}`                                 |
| Qiskit   | `optimization`  | `{"level":2}`                                        |
| Braket   | `deviceParams`  | `{"ionq": {"repetitionTime":1e-3}}`                  |

Consult vendor docs—QE simply forwards the blob.

---

← Previous: [Home](index.md) | Next: [How It Works →](how_it_works.md)
