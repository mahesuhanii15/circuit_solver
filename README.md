# circuit_solver_204_project


---



This repository contains the **Circuit Simulator** project developed for the **EE 204: Circuit Theory** course in the **3rd semester at IIT Guwahati**. The project simulates linear DC circuits using MATLAB and Python and features a GUI to build circuits interactively.

---

## Features

### Backend (MATLAB)
- Implements **Modified Nodal Analysis (MNA)** to solve circuit equations.
- Supports the following components:
  - Resistors (R)
  - Inductors (L)
  - Capacitors (C)
  - Independent Voltage Sources (V)
  - Independent Current Sources (I)
- Performs **DC analysis** and **transient analysis** for circuits involving R, L, and C.
- Generates:
  - Node voltages and branch currents.
  - Graphs for current and voltage across components.
  - Results saved in `Results.txt`.

### Frontend (Python)
- Interactive GUI to design circuits using a **drag-and-drop interface**:
  - Components: Resistors, Capacitors, Inductors, Voltage Sources, Current Sources, and Ground.
  - Connections: Wires between terminals.
- Generates a **netlist** based on the circuit built in the GUI.
- Uses **disjoint sets (Union-Find)** to handle nodal connections and simplify the circuit structure.
- Saves the netlist to `output.txt`.

---

## How to Run

### Requirements
- **MATLAB** (for circuit simulation backend)
- **Python** (for GUI frontend)
  - Required libraries: `tkinter`

### Steps
1. **Frontend**:
   - Run the Python GUI with:
     ```bash
     python Frontend.py
     ```
   - Design the circuit and click `Simulate` to generate the netlist (`output.txt`).

2. **Backend**:
   - Open MATLAB and run:
     ```matlab
     Circuit_Aalysis
     ```
   - Enter the filename of the generated netlist (`output.txt`) when prompted.
   - View the results in the MATLAB console and in the generated graphs.

---

## How It Works

1. **Frontend (Python)**:
   - Uses Tkinter to build a drag-and-drop GUI for circuit components.
   - Generates a netlist by mapping components to nodes and connections.

2. **Backend (MATLAB)**:
   - Parses the netlist and applies MNA to formulate circuit equations.
   - Solves equations for node voltages and branch currents using symbolic solvers (`ode15i` for differential equations).

---

## Sample Workflow

1. Open the GUI and design a circuit:
   - Drag components (R, L, C, V, I) onto the canvas.
   - Connect components with wires.
   - Click `Simulate` to generate the netlist.
   - Or additionly one can write the netlist thmeselves!

2. Run the MATLAB script:
   - Input the generated netlist file.
   - View simulation results and graphs.

  

---

## Files in Repository

| File Name        | Description                                         |
|-------------------|-----------------------------------------------------|
| `Frontend.py`    | Python GUI to design circuits and generate netlists |
| `Circuit_Aalysis.m` | MATLAB script for circuit simulation using MNA    |

---


## Future Work
- Add support for **AC analysis**.
- Improve GUI for better usability (e.g., component rotation, label editing).
- Extend the backend to support non-linear components like diodes.

---
