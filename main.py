# Since we don't know where CCS will be installed, we must find files relative
# to this script. To this end, we will need access to os package
import os
# We also need access to re package to use regular expressions
import re
# We also need access to sys package to exit the program with an exit code
import sys
import time
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions

# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.NOTSET)

# Initialize scripting and obtain the main debugger scripting interface
ds = initScripting()

# Configure a 10 second timeout on all operations (by default there is no timeout)
ds.setScriptingTimeout(10000)

# Configure the debugger and open a debug session to the cortex M core
current_dir = os.path.dirname(os.path.abspath(__file__))
ds.configure(os.path.join(current_dir, "target_config.ccxml"))
session = ds.openSession(re.compile(".*cortex.*", re.IGNORECASE))

session.target.connect()

# Load program
# The path provided must be an absolute path. Here we use the current script's location
# to resolve the location.
session.memory.loadProgram(os.path.join(current_dir, "C:\\Users\\john_\\workspace_ccstheia\\hello\\Debug\\hello.elf"))

# Set a breakpoint at ConfigureUART
bp1 = session.breakpoints.add("function1")

# Set a second breakpoint using the address of the function UARTprintf
#bp2Addr = session.expressions.evaluate("function1")
#bp2 = session.breakpoints.add(bp2Addr)
bp2_addr = session.expressions.evaluate("function1 + 0x6")
bp2 = session.breakpoints.add(bp2_addr)


# Let's define a function to run the target and check if it halts at the correct symbol
def expectRunToHaltAt(symbol):
    # Run the target and wait for it to halt
    session.target.run()

    symbolAddr = session.expressions.evaluate(symbol)
    pc = session.registers.read("PC")
    if pc == symbolAddr:
        print(f"Success: target is halted at {symbol} as expected.")
    else:
        print(
            f"Failure: Expected target to be halted at 0x{symbolAddr.toString(16)}, "
            f"but is actually halted at 0x{pc.toString(16)}."
        )
        sys.exit(1)

# If we run, we should hit our first breakpoint at ConfigureUART
expectRunToHaltAt("function1")
print("Now you can see the target halted at function1")

time.sleep(3)

expectRunToHaltAt("function1 + 0x6")
print("Now you can see the target halted at main.c:109")

if session.target.isHalted():
    try:
        # session.expressions.evaluate("option=1")
        # # Verificar
        # nuevo_valor = session.expressions.evaluate("option")
        # print("option nuevo:", nuevo_valor)
        #print("option =", valor_c)

        # 1) Obtener dirección de la variable
        addr_option = session.expressions.evaluate("&option")
        print("Direccion option:", addr_option)

        # 2) Escribir nuevo valor en memoria
        session.memory.write(addr_option, 1)

        # Verificar por memoria
        option_mem = session.memory.readOne(addr_option)
        print("option por memoria:", option_mem)

        # Verificar por expresion C
        option_expr = session.expressions.evaluate("option")
        print("option por expresion:", option_expr)

    except Exception as e:
        print("No se pudo evaluar 'option':", e)

time.sleep(3)

sys.exit(0)

# If we run a second time, we expect to halt at our second breakpoint
expectRunToHaltAt("UARTprintf")

# =========================================================================
# NUEVA LÓGICA: Leer la variable 'valor' antes de que continúe el programa
# =========================================================================
if session.target.isHalted():
    # Evaluamos el símbolo "valor" usando la sesión de debug
    valor_c = session.expressions.evaluate("valor")
    print(f"--- [DEBUG] El valor actual de la variable 'valor' es: {valor_c} ---")
# =========================================================================

# Remove our first breakpoint
session.breakpoints.remove(bp1)

# The program runs in an infinite loop, so running a third time should, once again, halt at the second breakpoint
expectRunToHaltAt("UARTprintf")

# If we remove our second breakpoint as well, we expect to run in a loop until we time out
session.breakpoints.remove(bp2)

# We expect the next run to timeout, let's reduce the timeout duration so we don't have to wait as long
ds.setScriptingTimeout(2000)

try:
    print("Expecting target to not halt for 2 seconds")
    session.target.run()
    print("Failure: Halted unexpectedly after removing both breakpoints.")
except Exception as err:
    # Check if we actually timed out, or if some other error occurred
    if isinstance(err, ScriptingTimeoutError):
        print("Success: we timed out while waiting for the target to halt")
        session.target.halt()
    else:
        print(f"Failure: unexpected error while running {err}")
        
        

# shutdown the debugger

ds.shutdown()