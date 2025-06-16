import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import queue
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Import your existing auto-centering module
# from auto_centering import SkyWaterBSIM4Centering, BSIM4TargetSpec

class BSIM4CenteringGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BSIM4 SkyWater PDK Auto-Centering Tool")
        self.root.geometry("1200x800")
        
        # Queue for thread communication
        self.queue = queue.Queue()
        
        # Create main container
        main_container = ttk.Frame(root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Left panel - Input parameters
        self.create_input_panel(main_container)
        
        # Right panel - Results and visualization
        self.create_results_panel(main_container)
        
        # Bottom panel - Console output
        self.create_console_panel(main_container)
        
        # Status bar
        self.create_status_bar()
        
    def create_input_panel(self, parent):
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Input Parameters", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Model settings
        ttk.Label(input_frame, text="Model Settings", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Label(input_frame, text="Model Library File:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.model_lib_var = tk.StringVar(value="skywater_models.lib")
        ttk.Entry(input_frame, textvariable=self.model_lib_var, width=30).grid(row=1, column=1, pady=2)
        
        ttk.Label(input_frame, text="Device Model:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.device_model_var = tk.StringVar(value="sky130_fd_pr__nfet_01v8")
        ttk.Entry(input_frame, textvariable=self.device_model_var, width=30).grid(row=2, column=1, pady=2)
        
        # Separator
        ttk.Separator(input_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Target specifications
        ttk.Label(input_frame, text="Target Specifications", font=('Arial', 10, 'bold')).grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # Vth
        ttk.Label(input_frame, text="Vth Target (V):").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.vth_var = tk.StringVar(value="0.4")
        ttk.Entry(input_frame, textvariable=self.vth_var, width=15).grid(row=5, column=1, pady=2)
        
        # Ion
        ttk.Label(input_frame, text="Ion Target (A/μm):").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.ion_var = tk.StringVar(value="5e-4")
        ttk.Entry(input_frame, textvariable=self.ion_var, width=15).grid(row=6, column=1, pady=2)
        
        # Device dimensions
        ttk.Label(input_frame, text="Length (m):").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.length_var = tk.StringVar(value="0.15e-6")
        ttk.Entry(input_frame, textvariable=self.length_var, width=15).grid(row=7, column=1, pady=2)
        
        ttk.Label(input_frame, text="Width (m):").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.StringVar(value="1e-6")
        ttk.Entry(input_frame, textvariable=self.width_var, width=15).grid(row=8, column=1, pady=2)
        
        # VDD
        ttk.Label(input_frame, text="VDD (V):").grid(row=9, column=0, sticky=tk.W, pady=2)
        self.vdd_var = tk.StringVar(value="1.8")
        ttk.Entry(input_frame, textvariable=self.vdd_var, width=15).grid(row=9, column=1, pady=2)
        
        # Temperature
        ttk.Label(input_frame, text="Temperature (°C):").grid(row=10, column=0, sticky=tk.W, pady=2)
        self.temp_var = tk.StringVar(value="25")
        ttk.Entry(input_frame, textvariable=self.temp_var, width=15).grid(row=10, column=1, pady=2)
        
        # Iterations
        ttk.Label(input_frame, text="Max Iterations:").grid(row=11, column=0, sticky=tk.W, pady=2)
        self.iterations_var = tk.StringVar(value="5")
        ttk.Entry(input_frame, textvariable=self.iterations_var, width=15).grid(row=11, column=1, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=20)
        
        self.run_button = ttk.Button(button_frame, text="Run Optimization", command=self.run_optimization)
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_optimization, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Results", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        
    def create_results_panel(self, parent):
        # Results frame
        results_frame = ttk.LabelFrame(parent, text="Results & Visualization", padding="10")
        results_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(results_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Convergence plot tab
        self.create_convergence_tab(notebook)
        
        # Parameter evolution tab
        self.create_parameter_tab(notebook)
        
        # Summary tab
        self.create_summary_tab(notebook)
        
    def create_convergence_tab(self, notebook):
        conv_frame = ttk.Frame(notebook)
        notebook.add(conv_frame, text="Convergence")
        
        # Create matplotlib figure
        self.fig_conv = Figure(figsize=(8, 6), dpi=100)
        self.ax_conv = self.fig_conv.add_subplot(111)
        self.ax_conv.set_xlabel('Iteration')
        self.ax_conv.set_ylabel('Error (%)')
        self.ax_conv.set_title('Optimization Convergence')
        self.ax_conv.grid(True)
        
        self.canvas_conv = FigureCanvasTkAgg(self.fig_conv, conv_frame)
        self.canvas_conv.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_parameter_tab(self, notebook):
        param_frame = ttk.Frame(notebook)
        notebook.add(param_frame, text="Parameter Evolution")
        
        # Create matplotlib figure with subplots
        self.fig_param = Figure(figsize=(8, 6), dpi=100)
        
        # Vth evolution
        self.ax_vth = self.fig_param.add_subplot(221)
        self.ax_vth.set_xlabel('Iteration')
        self.ax_vth.set_ylabel('Vth (V)')
        self.ax_vth.set_title('Vth Evolution')
        self.ax_vth.grid(True)
        
        # Ion evolution
        self.ax_ion = self.fig_param.add_subplot(222)
        self.ax_ion.set_xlabel('Iteration')
        self.ax_ion.set_ylabel('Ion (A/μm)')
        self.ax_ion.set_title('Ion Evolution')
        self.ax_ion.grid(True)
        
        # u0 evolution
        self.ax_u0 = self.fig_param.add_subplot(223)
        self.ax_u0.set_xlabel('Iteration')
        self.ax_u0.set_ylabel('u0 (cm²/V·s)')
        self.ax_u0.set_title('Mobility (u0) Evolution')
        self.ax_u0.grid(True)
        
        # vsat evolution
        self.ax_vsat = self.fig_param.add_subplot(224)
        self.ax_vsat.set_xlabel('Iteration')
        self.ax_vsat.set_ylabel('vsat (cm/s)')
        self.ax_vsat.set_title('Saturation Velocity Evolution')
        self.ax_vsat.grid(True)
        
        self.fig_param.tight_layout()
        
        self.canvas_param = FigureCanvasTkAgg(self.fig_param, param_frame)
        self.canvas_param.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_summary_tab(self, notebook):
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary Report")
        
        # Create text widget for summary
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=20)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_console_panel(self, parent):
        # Console frame
        console_frame = ttk.LabelFrame(parent, text="Console Output", padding="5")
        console_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # Console text widget
        self.console_text = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=10, bg='black', fg='white')
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
    def run_optimization(self):
        # Validate inputs
        try:
            vth = float(self.vth_var.get())
            ion = float(self.ion_var.get())
            length = float(self.length_var.get())
            width = float(self.width_var.get())
            vdd = float(self.vdd_var.get())
            temp = float(self.temp_var.get())
            iterations = int(self.iterations_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values for all parameters.")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Update UI state
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Running optimization...")
        
        # Run optimization in separate thread
        self.optimization_thread = threading.Thread(
            target=self.run_optimization_thread,
            args=(vth, ion, length, width, vdd, temp, iterations)
        )
        self.optimization_thread.start()
        
        # Start monitoring queue
        self.root.after(100, self.check_queue)
        
    def run_optimization_thread(self, vth, ion, length, width, vdd, temp, iterations):
        try:
            # Redirect stdout and stderr to capture print statements
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Import and run the centering tool
                from auto_centering import SkyWaterBSIM4Centering, BSIM4TargetSpec
                
                # Create centering tool instance
                centering_tool = SkyWaterBSIM4Centering(
                    model_lib_file=self.model_lib_var.get(),
                    device_model=self.device_model_var.get()
                )
                
                # Check model installation
                if not centering_tool.check_model_installation():
                    self.queue.put(("error", "Model installation failed!"))
                    return
                
                # Extract nominal parameters
                centering_tool.extract_nominal_parameters()
                
                # Create target specification
                target = BSIM4TargetSpec(
                    vth=vth,
                    ion=ion,
                    vdd=vdd,
                    temp=temp,
                    length=length,
                    width=width
                )
                
                # Run optimization
                success = centering_tool.optimize_parameters(target, max_iterations=iterations)
                
                # Get captured output
                console_output = stdout_capture.getvalue() + stderr_capture.getvalue()
                self.queue.put(("console", console_output))
                
                # Send results
                self.queue.put(("results", {
                    "success": success,
                    "centering_tool": centering_tool,
                    "iteration_log": centering_tool.iteration_log,
                    "report": centering_tool.generate_centering_report()
                }))
                
        except Exception as e:
            self.queue.put(("error", str(e)))
            
    def check_queue(self):
        try:
            while True:
                msg_type, msg_data = self.queue.get_nowait()
                
                if msg_type == "console":
                    self.update_console(msg_data)
                elif msg_type == "results":
                    self.display_results(msg_data)
                elif msg_type == "error":
                    messagebox.showerror("Error", msg_data)
                    self.optimization_complete()
                    
        except queue.Empty:
            pass
            
        # Continue checking if thread is alive
        if hasattr(self, 'optimization_thread') and self.optimization_thread.is_alive():
            self.root.after(100, self.check_queue)
        else:
            self.optimization_complete()
            
    def update_console(self, text):
        self.console_text.insert(tk.END, text)
        self.console_text.see(tk.END)
        self.root.update_idletasks()
        
    def display_results(self, results):
        if not results["iteration_log"]:
            return
            
        # Update convergence plot
        iterations = []
        vth_errors = []
        ion_errors = []
        total_errors = []
        
        target_vth = float(self.vth_var.get())
        target_ion = float(self.ion_var.get())
        
        for log in results["iteration_log"]:
            iterations.append(log["iteration"] + 1)
            
            vth = log["specs"]["vth"]
            ion = log["specs"]["ion"]
            
            vth_error = abs((vth - target_vth) / target_vth) * 100
            ion_error = abs((ion - target_ion) / target_ion) * 100
            
            vth_errors.append(vth_error)
            ion_errors.append(ion_error)
            total_errors.append(log["error"] * 100)
        
        self.ax_conv.clear()
        self.ax_conv.plot(iterations, vth_errors, 'b-o', label='Vth Error')
        self.ax_conv.plot(iterations, ion_errors, 'r-s', label='Ion Error')
        self.ax_conv.plot(iterations, total_errors, 'g-^', label='Total Error')
        self.ax_conv.set_xlabel('Iteration')
        self.ax_conv.set_ylabel('Error (%)')
        self.ax_conv.set_title('Optimization Convergence')
        self.ax_conv.legend()
        self.ax_conv.grid(True)
        self.canvas_conv.draw()
        
        # Update parameter evolution plots
        vth_values = [log["specs"]["vth"] for log in results["iteration_log"]]
        ion_values = [log["specs"]["ion"] for log in results["iteration_log"]]
        u0_values = [log["params"]["u0"] for log in results["iteration_log"]]
        vsat_values = [log["params"]["vsat"] for log in results["iteration_log"]]
        
        # Vth plot
        self.ax_vth.clear()
        self.ax_vth.plot(iterations, vth_values, 'b-o')
        self.ax_vth.axhline(y=target_vth, color='r', linestyle='--', label='Target')
        self.ax_vth.set_xlabel('Iteration')
        self.ax_vth.set_ylabel('Vth (V)')
        self.ax_vth.set_title('Vth Evolution')
        self.ax_vth.legend()
        self.ax_vth.grid(True)
        
        # Ion plot
        self.ax_ion.clear()
        self.ax_ion.plot(iterations, ion_values, 'b-o')
        self.ax_ion.axhline(y=target_ion, color='r', linestyle='--', label='Target')
        self.ax_ion.set_xlabel('Iteration')
        self.ax_ion.set_ylabel('Ion (A/μm)')
        self.ax_ion.set_title('Ion Evolution')
        self.ax_ion.legend()
        self.ax_ion.grid(True)
        
        # u0 plot
        self.ax_u0.clear()
        self.ax_u0.plot(iterations, u0_values, 'g-o')
        self.ax_u0.set_xlabel('Iteration')
        self.ax_u0.set_ylabel('u0 (cm²/V·s)')
        self.ax_u0.set_title('Mobility (u0) Evolution')
        self.ax_u0.grid(True)
        
        # vsat plot
        self.ax_vsat.clear()
        self.ax_vsat.plot(iterations, vsat_values, 'g-o')
        self.ax_vsat.set_xlabel('Iteration')
        self.ax_vsat.set_ylabel('vsat (cm/s)')
        self.ax_vsat.set_title('Saturation Velocity Evolution')
        self.ax_vsat.grid(True)
        
        self.fig_param.tight_layout()
        self.canvas_param.draw()
        
        # Update summary
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, results["report"])
        
        # Save centered model if successful
        if results["success"]:
            output_file = results["centering_tool"].save_centered_model()
            self.summary_text.insert(tk.END, f"\n\n✅ Centered model saved to: {output_file}")
            self.status_var.set(f"Optimization completed successfully! Model saved to {output_file}")
        else:
            self.status_var.set("Optimization did not converge to target specs")
            
    def optimization_complete(self):
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def stop_optimization(self):
        # This would need to be implemented with proper thread interruption
        messagebox.showinfo("Stop", "Stop functionality not yet implemented")
        
    def clear_results(self):
        # Clear plots
        self.ax_conv.clear()
        self.ax_conv.set_xlabel('Iteration')
        self.ax_conv.set_ylabel('Error (%)')
        self.ax_conv.set_title('Optimization Convergence')
        self.ax_conv.grid(True)
        self.canvas_conv.draw()
        
        self.ax_vth.clear()
        self.ax_ion.clear()
        self.ax_u0.clear()
        self.ax_vsat.clear()
        self.fig_param.tight_layout()
        self.canvas_param.draw()
        
        # Clear text
        self.console_text.delete(1.0, tk.END)
        self.summary_text.delete(1.0, tk.END)
        self.status_var.set("Ready")

def main():
    root = tk.Tk()
    app = BSIM4CenteringGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()