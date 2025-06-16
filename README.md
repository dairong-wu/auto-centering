# BSIM4 SkyWater PDK Auto-Centering Tool

A Python-based tool for automatically centering BSIM4 model parameters for SkyWater PDK devices using the constant current method (Id > 140nA * W/L).

## Features

- **Automatic parameter optimization** for BSIM4 models
- **Constant current method** for accurate Vth extraction
- **Multi-parameter optimization** including Vth0, u0, and vsat
- **GUI interface** for easy parameter input and result visualization
- **Real-time convergence monitoring**
- **Comprehensive reporting** with error analysis

## Requirements

- Python 3.7+
- NumPy
- Matplotlib
- Tkinter (usually comes with Python)
- ngspice (must be installed and accessible from command line)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/dairong-wu/auto-centering.git
cd auto-bsim4-skywater-centering
```

2. Install Python dependencies:
```bash
pip install numpy matplotlib
```

3. Install ngspice:
- **Ubuntu/Debian**: `sudo apt-get install ngspice`
- **macOS**: `brew install ngspice`
- **Windows**: Download from [ngspice website](http://ngspice.sourceforge.net/download.html)

## Usage

### GUI Mode (Recommended)

Run the GUI application:
```bash
python bsim4_gui.py
```

The GUI provides:
- Input fields for all parameters
- Real-time visualization of convergence
- Parameter evolution plots
- Console output monitoring
- Automatic report generation


### Command Line Mode

Run the validator directly:
```bash
python validator.py
```

You will be prompted to enter:
- Vth specification (V)
- Ion (Idsat) specification (A/μm)
- Target device length (m)
- Target device width (m)
- Number of iterations

### Example Input

```
Vth Spec(V): 0.4
Ion(Idsat) Spec(A/um): 5e-4
Target Device Length(m): 0.15e-6
Target Device Width(m): 1e-6
Iteration Numbers: 5
```

## How It Works

1. **Model Extraction**: Reads nominal BSIM4 parameters from SkyWater-like model files
2. **Constant Current Method**: Uses Id > 140nA * W/L threshold for accurate Vth extraction
3. **Iterative Optimization**: Adjusts vth0, u0, and vsat parameters to meet target specifications
4. **Convergence Monitoring**: Tracks error metrics and parameter evolution
5. **Model Generation**: Creates optimized model file with centered parameters

## Output Files

- `skywater_nmos_centered.lib` - Centered BSIM4 model file
- `centering_report.txt` - Detailed optimization report
- Temporary simulation files in system temp directory (auto-cleaned)

## GUI Features

### Input Panel
- Model library file selection
- Device model specification
- Target parameters (Vth, Ion, dimensions)
- Optimization settings

### Visualization Tabs
1. **Convergence**: Error vs. iteration plots
2. **Parameter Evolution**: Vth, Ion, u0, vsat trends
3. **Summary Report**: Complete optimization results

### Console Output
- Real-time simulation progress
- Debug information
- Error messages

## Algorithm Details

The tool uses a gradient-based optimization approach with adaptive learning rate:
- Learning rate: `lr = 0.3 * (0.9^iteration)`
- Parameter bounds:
  - vth0: [0.1, 0.9] V
  - u0: [50, 2000] cm²/V·s
  - vsat: [5e4, 2.5e7] cm/s

## Troubleshooting

1. **ngspice not found**: Ensure ngspice is installed and in your PATH
2. **Simulation timeout**: Increase timeout in `run_simulation()` method
3. **Convergence issues**: Try increasing the number of iterations
4. **GUI not starting**: Ensure tkinter is installed (`python -m tkinter`)

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## Author

Dai-Rong(Jeffy) Wu

## Acknowledgments

- SkyWater PDK team for the open-source PDK
- ngspice development team