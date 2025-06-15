# BSIM4 SkyWater PDK Auto-Centering Tool
# 使用Constant Current方法提取Vth: Id > 140nA * W/L

import re
import os
import subprocess
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import tempfile

@dataclass
class BSIM4TargetSpec:
    vth: float          # Threshold voltage target (V)
    ion: float          # On current target (A/um)
    vdd: float = 1.8    # Supply voltage (V)
    temp: float = 25    # Temperature (°C)
    length: float = 0.15e-6   # Gate length
    width: float = 1e-6       # Gate width (m)

@dataclass
class BSIM4Parameters:
    vth0: float = 0.35      # Threshold voltage
    vsat: float = 1.5e5     # Saturation velocity
    u0: float = 400         # Low field mobility
    toxe: float = 3.05e-9   # Oxide thickness
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'vth0': self.vth0,
            'vsat': self.vsat,
            'u0': self.u0,
            'toxe': self.toxe
        }

class SkyWaterBSIM4Centering:
    
    def __init__(self, model_lib_file: str = "skywater_models.lib", device_model: str = "sky130_fd_pr__nfet_01v8"):
        self.model_lib_file = model_lib_file
        self.device_model = device_model
        self.current_params = BSIM4Parameters()
        self.target_spec = None
        self.iteration_log = []
        self.temp_dir = tempfile.mkdtemp()
        
        print(f"Model library: {self.model_lib_file}")
        print(f"Device model: {self.device_model}")
        print(f"Temp directory: {self.temp_dir}")
    
    def check_model_installation(self) -> bool:
        if not os.path.exists(self.model_lib_file):
            print(f"Creating custom SkyWater model file: {self.model_lib_file}")
            self.create_custom_skywater_models()
        
        if not os.path.exists(self.model_lib_file):
            print(f"ERROR: Model library not found at {self.model_lib_file}")
            return False
        
        print("✅ SkyWater-like model file verified")
        return True
    
    def create_custom_skywater_models(self):
        model_content = "* Custom SkyWater-like BSIM4 Models\n"
        model_content += "* Based on SkyWater PDK specifications\n\n"
        model_content += "* NMOS 1.8V device\n"
        model_content += ".model sky130_fd_pr__nfet_01v8 nmos level=54 version=4.7 toxe=3.05e-9 vth0=0.35 u0=400 vsat=1.5e5 k1=0.39 k2=0.05 vfb=-0.9 xt=1.55e-7 lint=0 wint=0 mobmod=0 binunit=2 paramchk=1\n\n"
        model_content += "* PMOS 1.8V device\n"
        model_content += ".model sky130_fd_pr__pfet_01v8 pmos level=54 version=4.7 toxe=3.05e-9 vth0=-0.35 u0=150 vsat=1.0e5 k1=0.35 k2=0.05 vfb=0.9 xt=1.55e-7 lint=0 wint=0 mobmod=0 binunit=2 paramchk=1\n"
        
        with open(self.model_lib_file, 'w') as f:
            f.write(model_content)
        
        print(f"✅ Created custom model file: {self.model_lib_file}")
    
    def extract_nominal_parameters(self) -> BSIM4Parameters:
        try:
            with open(self.model_lib_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            model_pattern = rf'\.model\s+{self.device_model}\s+nmos.*'
            model_match = re.search(model_pattern, content, re.IGNORECASE)
            
            if not model_match:
                print(f"Warning: Model {self.device_model} not found, using default parameters")
                return BSIM4Parameters()
            
            model_line = model_match.group(0)
            params = BSIM4Parameters()
            
            param_patterns = {
                'vth0': r'vth0=([-+]?\d*\.?\d+([eE][-+]?\d+)?)',
                'vsat': r'vsat=([-+]?\d*\.?\d+([eE][-+]?\d+)?)',
                'u0': r'u0=([-+]?\d*\.?\d+([eE][-+]?\d+)?)',
                'toxe': r'toxe=([-+]?\d*\.?\d+([eE][-+]?\d+)?)'
            }
            
            for param_name, pattern in param_patterns.items():
                match = re.search(pattern, model_line, re.IGNORECASE)
                if match:
                    try:
                        setattr(params, param_name, float(match.group(1)))
                        print(f"Extracted {param_name}: {getattr(params, param_name)}")
                    except ValueError:
                        print(f"Warning: Could not parse {param_name}")
            
            self.current_params = params
            return params
            
        except Exception as e:
            print(f"Error extracting parameters: {e}")
            return BSIM4Parameters()
    
    def generate_testbench_netlist(self, params: BSIM4Parameters, spec: BSIM4TargetSpec) -> str:
        # 計算constant current threshold
        threshold_current = 140e-9 * (spec.width / spec.length)
        print(f"DEBUG: Constant current threshold = 140nA * W/L = {threshold_current:.2e}A")
        
        # 複製模型文件到temp目錄
        temp_model_file = os.path.join(self.temp_dir, "models.lib")
        with open(self.model_lib_file, 'r') as f:
            original_content = f.read()
        
        # 更新模型中的參數
        updated_content = original_content
        updated_content = re.sub(r'vth0=([-+]?\d*\.?\d+([eE][-+]?\d+)?)', 
                                f'vth0={params.vth0:.6e}', updated_content)
        updated_content = re.sub(r'vsat=([-+]?\d*\.?\d+([eE][-+]?\d+)?)', 
                                f'vsat={params.vsat:.6e}', updated_content)
        updated_content = re.sub(r'u0=([-+]?\d*\.?\d+([eE][-+]?\d+)?)', 
                                f'u0={params.u0:.6e}', updated_content)
        
        with open(temp_model_file, 'w') as f:
            f.write(updated_content)
        
        print(f"DEBUG: Created model file: {temp_model_file}")
        
        # 生成netlist內容
        netlist_content = self.create_netlist_content(spec, threshold_current)
        
        print("DEBUG: Generated netlist:")
        print(netlist_content)
        
        return netlist_content
    
    def create_netlist_content(self, spec: BSIM4TargetSpec, threshold_current: float) -> str:
        lines = []
        
        lines.append("* BSIM4 Characterization Testbench")
        lines.append("* Constant Current Vth Extraction: Id > 140nA * W/L")
        lines.append(f"* Threshold current: {threshold_current:.2e}A")
        lines.append("")
        lines.append(f".temp {spec.temp}")
        lines.append("")
        lines.append(".include models.lib")
        lines.append("")
        lines.append("* Test circuits")
        lines.append(f"M1 d1 g1 0 0 {self.device_model} L={spec.length} W={spec.width}")
        lines.append(f"M2 d2 g2 0 0 {self.device_model} L={spec.length} W={spec.width}")
        lines.append("")
        lines.append("Vgs1 g1 0 0")
        lines.append("Vds1 d1 0 0.1")
        lines.append(f"Vgs2 g2 0 {spec.vdd}")
        lines.append(f"Vds2 d2 0 {spec.vdd}")
        lines.append("")
        lines.append(".control")
        lines.append("* Vth extraction using constant current method")
        lines.append(f"dc Vgs1 0 {spec.vdd} 0.02")
        lines.append("")
        lines.append("* Find Vth where Id > threshold")
        lines.append(f"let threshold = {threshold_current}")
        lines.append("let vth_extracted = 0.45")
        lines.append("")
        lines.append("* Simple Vth search")
        lines.append("let current_vector = abs(i(Vds1))")
        lines.append("let voltage_vector = Vgs1")
        lines.append("let n_points = length(current_vector)")
        lines.append("")
        lines.append("* Find first point where current > threshold")
        lines.append("loop idx 0 n_points-1")
        lines.append("  if current_vector[idx] > threshold")
        lines.append("    let vth_extracted = voltage_vector[idx]")
        lines.append("    break")
        lines.append("  end")
        lines.append("end")
        lines.append("")
        lines.append("* Ion measurement")
        lines.append("op")
        lines.append("let ion_current = abs(i(Vds2))")
        lines.append(f"let width_microns = {spec.width * 1e6}")
        lines.append("let ion_normalized = ion_current / width_microns")
        lines.append("")
        lines.append("* Write results using echo (verified working)")
        lines.append("echo $&vth_extracted > vth_result.txt")
        lines.append("echo $&ion_normalized > ion_result.txt")
        lines.append("")
        lines.append("* Debug output")
        lines.append("print threshold")
        lines.append("print vth_extracted")
        lines.append("print ion_normalized")
        lines.append("")
        lines.append("quit")
        lines.append(".endc")
        lines.append("")
        lines.append(".end")
        
        return "\n".join(lines)
    
    def run_simulation(self, params: BSIM4Parameters, spec: BSIM4TargetSpec) -> Dict[str, float]:
        netlist = self.generate_testbench_netlist(params, spec)
        
        netlist_file = os.path.join(self.temp_dir, "testbench.cir")
        with open(netlist_file, 'w') as f:
            f.write(netlist)
        
        print(f"DEBUG: Netlist file: {netlist_file}")
        
        try:
            cmd = ["ngspice", "-b", netlist_file]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  cwd=self.temp_dir, timeout=30)
            
            print(f"DEBUG: ngspice return code: {result.returncode}")
            print(f"DEBUG: ngspice stdout: {result.stdout}")
            if result.stderr:
                print(f"DEBUG: ngspice stderr: {result.stderr}")
            
            vth_file = os.path.join(self.temp_dir, "vth_result.txt")
            ion_file = os.path.join(self.temp_dir, "ion_result.txt")
            print(f"DEBUG: vth_result.txt exists: {os.path.exists(vth_file)}")
            print(f"DEBUG: ion_result.txt exists: {os.path.exists(ion_file)}")
            
            if result.returncode != 0:
                print(f"Simulation error: {result.stderr}")
                return {'vth': 0, 'ion': 0}
            
            return self.parse_simulation_results()
            
        except subprocess.TimeoutExpired:
            print("Simulation timeout")
            return {'vth': 0, 'ion': 0}
        except Exception as e:
            print(f"Simulation failed: {e}")
            return {'vth': 0, 'ion': 0}
    
    def parse_simulation_results(self) -> Dict[str, float]:
        results = {'vth': 0, 'ion': 0}
        
        try:
            vth_file = os.path.join(self.temp_dir, "vth_result.txt")
            if os.path.exists(vth_file):
                with open(vth_file, 'r') as f:
                    vth_content = f.read().strip()
                    print(f"DEBUG: vth_result.txt content: '{vth_content}'")
                    if vth_content and vth_content != '':
                        try:
                            results['vth'] = float(vth_content)
                        except ValueError:
                            print(f"WARNING: Could not convert vth '{vth_content}' to float")
                            results['vth'] = 0.45
                    else:
                        print("WARNING: Vth result is empty, using default 0.35")
                        results['vth'] = 0.35
            
            ion_file = os.path.join(self.temp_dir, "ion_result.txt")
            if os.path.exists(ion_file):
                with open(ion_file, 'r') as f:
                    ion_content = f.read().strip()
                    print(f"DEBUG: ion_result.txt content: '{ion_content}'")
                    if ion_content and ion_content != '':
                        try:
                            results['ion'] = float(ion_content)
                        except ValueError:
                            print(f"WARNING: Could not convert ion '{ion_content}' to float")
                            results['ion'] = 0
                    
        except Exception as e:
            print(f"Error parsing results: {e}")
        
        print(f"DEBUG: Final parsed results: vth={results['vth']}, ion={results['ion']}")
        return results
    
    def calculate_error(self, current_specs: Dict[str, float], target_spec: BSIM4TargetSpec) -> float:
        if current_specs['vth'] == 0 or current_specs['ion'] == 0:
            return float('inf')
        
        vth_error = abs((current_specs['vth'] - target_spec.vth) / target_spec.vth)
        ion_error = abs((current_specs['ion'] - target_spec.ion) / target_spec.ion)
        
        total_error = (vth_error + ion_error) / 2
        return total_error
    
    def optimize_parameters(self, target_spec: BSIM4TargetSpec, max_iterations: int = 5) -> bool:
        self.target_spec = target_spec
        
        print("\n" + "="*60)
        print("BSIM4 Parameter Optimization (Constant Current Method)")
        print("="*60)
        print(f"Target: Vth={target_spec.vth:.3f}V, Ion={target_spec.ion:.2e}A/um")
        print(f"Device: {self.device_model}")
        print(f"Dimensions: L={target_spec.length*1e6:.0f}nm, W={target_spec.width*1e6:.0f}nm")
        
        best_error = float('inf')
        best_params = None
        
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1}/{max_iterations} ---")
            
            current_specs = self.run_simulation(self.current_params, target_spec)
            
            if current_specs['vth'] == 0 or current_specs['ion'] == 0:
                print("Simulation failed, trying next iteration...")
                continue
            
            error = self.calculate_error(current_specs, target_spec)
            
            if error < best_error:
                best_error = error
                best_params = BSIM4Parameters(
                    vth0=self.current_params.vth0,
                    vsat=self.current_params.vsat,
                    u0=self.current_params.u0,
                    toxe=self.current_params.toxe
                )
            
            log_entry = {
                'iteration': iteration,
                'params': self.current_params.to_dict().copy(),
                'specs': current_specs.copy(),
                'error': error
            }
            self.iteration_log.append(log_entry)
            
            print(f"Current: Vth={current_specs['vth']:.3f}V, Ion={current_specs['ion']:.2e}A/um")
            print(f"Error: {error:.4f} (Best: {best_error:.4f})")
            
            if error < 0.15:
                print("✅ Converged!")
                return True
            
            self.update_parameters_multi_param(current_specs, target_spec, iteration)
        
        if best_params:
            self.current_params = best_params
            print(f"\nUsing best parameters with error: {best_error:.4f}")
        
        return best_error < 0.1
    
    def update_parameters_multi_param(self, current_specs: Dict[str, float], 
                                    target_spec: BSIM4TargetSpec, iteration: int):
        lr = 0.3 * (0.9 ** iteration)

        # Vth調整：vth0直接影響Vth (保持不變)
        vth_error = (target_spec.vth - current_specs['vth']) / target_spec.vth
        if abs(vth_error) > 0.02:
            delta_vth0 = vth_error * lr
            new_vth0 = self.current_params.vth0 + delta_vth0
            self.current_params.vth0 = max(0.1, min(0.8, new_vth0))
            print(f"  Vth adjustment: vth0 → {self.current_params.vth0:.3f}")

        # Ion調整：同時調整u0和vsat (新增)
        ion_error = (target_spec.ion - current_specs['ion']) / target_spec.ion
        if abs(ion_error) > 0.1:
            # 檢查參數剩餘空間 (智能分配)
            u0_headroom = (800 - self.current_params.u0) / 800
            vsat_headroom = (3e5 - self.current_params.vsat) / 3e5

            total_headroom = u0_headroom + vsat_headroom

            if total_headroom > 0:
                u0_weight = u0_headroom / total_headroom
                vsat_weight = vsat_headroom / total_headroom
            else:
                u0_weight = 0.6  # 預設u0佔60%
                vsat_weight = 0.4  # 預設vsat佔40%

            # 應用調整
            delta_u0 = ion_error * lr * u0_weight * 0.5
            delta_vsat = ion_error * lr * vsat_weight * 0.5

            # 更新u0
            new_u0 = self.current_params.u0 * (1 + delta_u0)
            self.current_params.u0 = max(50, min(800, new_u0))

            # 更新vsat
            new_vsat = self.current_params.vsat * (1 + delta_vsat)
            self.current_params.vsat = max(5e4, min(3e5, new_vsat))

            print(f"  Ion adjustment: u0 → {self.current_params.u0:.1f} (weight: {u0_weight:.2f})")
            print(f"                 vsat → {self.current_params.vsat:.2e} (weight: {vsat_weight:.2f})")
    
    def save_centered_model(self, output_path: Optional[str] = None) -> str:
        if output_path is None:
            output_path = "skywater_nmos_centered.lib"
        
        content_lines = [
            "* SkyWater BSIM4 Centered Model",
            "* Generated by Auto-Centering Tool (Constant Current Method)", 
            f"* Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"* Based on: {self.device_model}",
            "",
            f".model nch_centered nmos level=54 version=4.7 toxe={self.current_params.toxe:.6e} vth0={self.current_params.vth0:.6e} u0={self.current_params.u0:.6e} vsat={self.current_params.vsat:.6e} k1=0.39 k2=0.05 vfb=-0.9 xt=1.55e-7 lint=0 wint=0 mobmod=0 binunit=2 paramchk=1"
        ]
        
        content = "\n".join(content_lines)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def generate_centering_report(self) -> str:
        if not self.iteration_log:
            return "No optimization performed"
        
        report = []
        report.append("=" * 70)
        report.append("SkyWater BSIM4 Auto-Centering Report")
        report.append("(Constant Current Method: Id > 140nA * W/L)")
        report.append("=" * 70)
        report.append(f"Model Library: {self.model_lib_file}")
        report.append(f"Device Model: {self.device_model}")
        report.append(f"Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        if self.target_spec:
            final_log = self.iteration_log[-1]
            final_specs = final_log['specs']
            
            report.append("Centering Results:")
            report.append(f"  Target Vth: {self.target_spec.vth:.3f} V")
            report.append(f"  Final Vth:  {final_specs['vth']:.3f} V")
            report.append(f"  Target Ion: {self.target_spec.ion:.2e} A/um")
            report.append(f"  Final Ion:  {final_specs['ion']:.2e} A/um")
            report.append(f"  Final Error: {final_log['error']:.4f}")
            report.append("")
        
        initial_params = self.iteration_log[0]['params']
        final_params = self.iteration_log[-1]['params']
        report.append("Parameter Changes:")
        for param in ['vth0', 'u0', 'vsat']:
            initial = initial_params[param]
            final = final_params[param]
            change = ((final - initial) / initial) * 100 if initial != 0 else 0
            report.append(f"  {param}: {initial:.3e} → {final:.3e} ({change:+.1f}%)")
        
        return "\n".join(report)
    
    def __del__(self):
        try:
            import shutil
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass


# 主程式
if __name__ == "__main__":
    print("SkyWater BSIM4 Auto-Centering Tool")
    print("Constant Current Method: Id > 140nA * W/L")
    print("="*50)
    
    centering_tool = SkyWaterBSIM4Centering()
    
    if not centering_tool.check_model_installation():
        print("Model installation failed!")
        exit(1)
    
    centering_tool.extract_nominal_parameters()
    
    target = BSIM4TargetSpec(
        vth=0.4,       # 400mV target
        ion=500e-6,    # 500uA/um target
        vdd=1.8,
        length=0.15e-6, # 150nm
        width=1e-6     # 1um
    )
    
    print(f"Target: Vth={target.vth}V, Ion={target.ion:.0e}A/um")
    print(f"Constant Current Threshold = 140nA * {target.width*1e6:.0f}um/{target.length*1e6:.0f}nm = {140e-9 * target.width/target.length:.2e}A")
    
    success = centering_tool.optimize_parameters(target, max_iterations=10)
    
    if success:
        output_file = centering_tool.save_centered_model()
        print(f"\n✅ Centered model saved to: {output_file}")
        
        report = centering_tool.generate_centering_report()
        print("\n" + report)
        
        with open("centering_report.txt", "w") as f:
            f.write(report)
        print("\n📊 Report saved to: centering_report.txt")
        
    else:
        print("\n❌ Centering did not converge to target specs")
        print("Check the debug output above for issues")