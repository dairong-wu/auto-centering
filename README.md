# BSIM4 Auto-Centering Tool

A Python tool for automatically centering BSIM4 SPICE models to target specifications using constant current Vth extraction method.

## Features
- Constant current Vth extraction (Id > 140nA × W/L)
- Automated parameter optimization (vth0, vsat)
- SkyWater PDK-like BSIM4 model support
- ngspice integration for real simulation
- Comprehensive centering reports

## Usage
```python
python src/validator.py