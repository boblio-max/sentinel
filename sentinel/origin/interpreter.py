import re
import math
import random
import sys
import os
import subprocess
from typing import Any, List, Dict, Tuple
from sentinel.nodes.core import WaitNode
from sentinel.nodes.arm import ArmNode
from sentinel.nodes.gpio import GPIONode

class RuntimeException(Exception):
    def __init__(self, err_type: str, message: str, line_no: int = None):
        self.err_type = err_type
        self.raw_message = message
        self.line_no = line_no
        super().__init__(f"{err_type} at line {line_no if line_no else '?'}: {message}")

class OriginInterpreter:
    def __init__(self, context: dict = None):
        self.context = context or {}
        # Environment is a dict of strings -> values
        # Types are tracked separately if needed, but dynamically checked.
        if "_origin_env" not in self.context:
            self.context["_origin_env"] = {}
        if "_origin_consts" not in self.context:
            self.context["_origin_consts"] = set()
            
        self.env = self.context["_origin_env"]
        self.consts = self.context["_origin_consts"]
        
        self.functions = {}
        self.classes = {}
        self.lines = []
        self.current_line_idx = 0

    def run_script(self, code: str):
        self.lines = [line.rstrip() for line in code.split('\n')]
        self.current_line_idx = 0
        try:
            self._execute_block(0, len(self.lines))
        except RuntimeException as e:
            # Re-raise standard format
            raise RuntimeError(str(e))
        except Exception as e:
            # Fallback for unforeseen errors
            raise RuntimeError(f"OriginExecutionError at line {self.current_line_idx + 1}: {str(e)}")

    def _execute_block(self, start: int, end: int):
        idx = start
        while idx < end:
            self.current_line_idx = idx
            line = self.lines[idx]
            stripped = line.strip()
            
            # Skip empty lines and full comments
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue
                
            # Strip inline comments (simplistic)
            if "#" in stripped:
                # Make sure it's not in a string - simplistic approach:
                # Find first '#' not preceded by a quote. We'll use split.
                in_str = False
                hash_pos = -1
                for i, char in enumerate(stripped):
                    if char == '"':
                        in_str = not in_str
                    elif char == '#' and not in_str:
                        hash_pos = i
                        break
                if hash_pos != -1:
                    stripped = stripped[:hash_pos].strip()
                    if not stripped:
                        idx += 1
                        continue

            if stripped.startswith("import "):
                self._handle_import(stripped, idx)
                idx += 1
                
            elif stripped.startswith("from ") and " import " in stripped:
                self._handle_from_import(stripped, idx)
                idx += 1

            elif stripped.startswith("let "):
                self._handle_let(stripped, idx)
                idx += 1

            elif stripped.startswith("const "):
                self._handle_const(stripped, idx)
                idx += 1

            elif stripped.startswith("print "):
                self._handle_print(stripped, idx)
                idx += 1

            elif stripped.startswith("set "):
                self._handle_set_hardware(stripped, idx)
                idx += 1

            elif stripped.startswith("wait "):
                v = self._eval_expr(stripped[5:].strip(), idx)
                try:
                    val = float(v)
                except ValueError:
                    raise RuntimeException("TypeError", "wait expects numeric value", idx+1)
                # wait is in ms usually in DSLs, but Sentinel UI wait is in ms usually? WaitNode is seconds
                # The prompt: wait 500 -> WaitNode(seconds=0.5)
                # So we assume wait is in ms.
                res = WaitNode(seconds=val/1000.0).run(self.context)
                if not res.success:
                    raise RuntimeException("RuntimeError", f"Wait failed: {res.error}", idx+1)
                idx += 1

            elif stripped.startswith("open "):
                self._handle_open(stripped, idx)
                idx += 1

            elif stripped.startswith("exec "):
                self._handle_exec(stripped, idx)
                idx += 1

            elif stripped.startswith("def "):
                idx = self._handle_def(start, end, idx)

            elif stripped.startswith("class "):
                idx = self._handle_class(start, end, idx)

            elif stripped.startswith("if "):
                idx = self._handle_if(start, end, idx)

            elif stripped.startswith("for "):
                idx = self._handle_for(start, end, idx)

            elif stripped.startswith("while "):
                idx = self._handle_while(start, end, idx)

            elif stripped.startswith("try "):
                idx = self._handle_try(start, end, idx)

            elif stripped.startswith("parallel "):
                idx = self._handle_parallel(start, end, idx)

            elif " = " in stripped and not stripped.startswith(("if", "elif", "else", "for", "while", "try", "except", "def", "class", "{", "}")):
                self._handle_assignment(stripped, idx)
                idx += 1

            elif "(" in stripped and ")" in stripped:
                # Function call statement
                self._eval_expr(stripped, idx)
                idx += 1

            elif stripped == "return" or stripped.startswith("return "):
                return  # Return jumps out of block. Actual values handled in eval

            else:
                idx += 1

    def _get_block_bounds(self, start_idx: int, total_end: int) -> Tuple[int, int]:
        # Finds the end of a block enclosed in { } starting on start_idx
        # start_idx might have the opening { on it, or the next line.
        
        line = self.lines[start_idx].strip()
        if not line.endswith("{"):
            raise RuntimeException("SyntaxError", "Expected '{' to start block", start_idx+1)
            
        brace_count = 1
        idx = start_idx + 1
        while idx < total_end:
            s_line = self.lines[idx].strip()
            # Simple brace matching (ignores strings for now to keep it succinct for the prompt reqs)
            if "{" in s_line:
                brace_count += s_line.count("{")
            if "}" in s_line:
                brace_count -= s_line.count("}")
                
            if brace_count == 0:
                return start_idx + 1, idx # block content is between start_idx+1 and idx
            idx += 1
            
        raise RuntimeException("SyntaxError", "Unclosed '{'", start_idx+1)

    def _handle_let(self, stmt: str, line_idx: int):
        # let x: int = 10
        match = re.match(r"let\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_]\w*)\s*=\s*(.*)", stmt)
        if not match:
            raise RuntimeException("SyntaxError", "Invalid let declaration", line_idx+1)
        name, _type, expr = match.groups()
        val = self._eval_expr(expr, line_idx)
        # Type checking could be done here based on _type
        self.env[name] = val

    def _handle_const(self, stmt: str, line_idx: int):
        # const pi: float = 3.14159
        match = re.match(r"const\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_]\w*)\s*=\s*(.*)", stmt)
        if not match:
            raise RuntimeException("SyntaxError", "Invalid const declaration", line_idx+1)
        name, _type, expr = match.groups()
        if name in self.consts:
            raise RuntimeException("ImmutableError", f"Constant {name} already declared", line_idx+1)
        val = self._eval_expr(expr, line_idx)
        self.env[name] = val
        self.consts.add(name)

    def _handle_assignment(self, stmt: str, line_idx: int):
        parts = stmt.split("=", 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        
        val = self._eval_expr(rhs, line_idx)
        
        if "[" in lhs and lhs.endswith("]"): # List assignment
            name, idx_str = lhs[:-1].split("[", 1)
            idx = int(self._eval_expr(idx_str, line_idx))
            if name not in self.env:
                raise RuntimeException("NameError", f"Variable {name} not found", line_idx+1)
            self.env[name][idx] = val
        else:
            if lhs in self.consts:
                raise RuntimeException("ImmutableError", f"Cannot reassign constant {lhs}", line_idx+1)
            if lhs not in self.env:
                raise RuntimeException("NameError", f"Variable {lhs} not declared", line_idx+1)
            self.env[lhs] = val

    def _handle_print(self, stmt: str, line_idx: int):
        expr = stmt[6:].strip()
        val = self._eval_expr(expr, line_idx)
        print(val)

    def _handle_set_hardware(self, stmt: str, line_idx: int):
        # set servo[0] = angle, 90
        # set servo.angle 0, 90
        # set servo.sweep 0, 0, 180, 10
        # set pin[4] = 1
        stmt = stmt[4:].strip()
        
        if stmt.startswith("servo[") or stmt.startswith("servo.angle "):
            if " = " in stmt:
                # set servo[val] = angle, val
                lhs, rhs = stmt.split("=", 1)
                idx_str = lhs[6:-1]
                rhs = rhs.strip()
                if not rhs.startswith("angle,"):
                    raise RuntimeException("SyntaxError", "Expected angle, value", line_idx+1)
                ang_str = rhs[6:].strip()
            else:
                # set servo.angle 0, 90
                parts = stmt[12:].split(",")
                idx_str = parts[0].strip()
                ang_str = parts[1].strip()
                
            idx = int(self._eval_expr(idx_str, line_idx))
            ang = float(self._eval_expr(ang_str, line_idx))
            
            if ang < 0 or ang > 180:
                print(f"[Origin WARN] Servo angle {ang} outside 0-180 range at line {line_idx+1}")
                
            res = ArmNode(joint=idx, angle=ang).run(self.context)
            if not res.success:
                raise RuntimeException("RuntimeError", f"Servo execution failed: {res.error}", line_idx+1)
                
        elif stmt.startswith("pin["):
            # set pin[4] = 1
            lhs, rhs = stmt.split("=", 1)
            pin_idx = int(self._eval_expr(lhs[4:-1], line_idx))
            state = int(self._eval_expr(rhs.strip(), line_idx))
            res = GPIONode(pin=pin_idx, state=state).run(self.context)
            if not res.success:
                raise RuntimeException("RuntimeError", f"GPIO execution failed: {res.error}", line_idx+1)
                
        elif stmt.startswith("servo.sweep "):
            # set servo.sweep 0, 0, 180, 10
            parts = stmt[12:].split(",")
            if len(parts) != 4:
                raise RuntimeException("SyntaxError", "sweep expects 4 arguments", line_idx+1)
            joint = int(self._eval_expr(parts[0], line_idx))
            start_ang = float(self._eval_expr(parts[1], line_idx))
            end_ang = float(self._eval_expr(parts[2], line_idx))
            step = float(self._eval_expr(parts[3], line_idx))
            
            # Simple loop mapped to Sentinel
            curr = start_ang
            while curr <= end_ang:
                res = ArmNode(joint=joint, angle=curr).run(self.context)
                if not res.success:
                    raise RuntimeException("RuntimeError", f"Sweep failed: {res.error}", line_idx+1)
                curr += step

    def _handle_open(self, stmt: str, line_idx: int):
        # open "data.txt" "w" as f
        match = re.match(r'open\s+(".*?"|\'.*?\')\s+(".*?"|\'.*?\')\s+as\s+([a-zA-Z_]\w*)', stmt)
        if not match:
            raise RuntimeException("SyntaxError", "Invalid open statement", line_idx+1)
        filename = self._eval_expr(match.group(1), line_idx)
        mode = self._eval_expr(match.group(2), line_idx)
        var_name = match.group(3)
        try:
            f = open(filename, mode)
            self.env[var_name] = f
        except Exception as e:
            raise RuntimeException("RuntimeError", f"Failed to open file: {e}", line_idx+1)

    def _handle_exec(self, stmt: str, line_idx: int):
        # exec "print('hello from subprocess')"
        cmd = self._eval_expr(stmt[5:].strip(), line_idx)
        try:
            # Execute inline code directly connected to system core python interpreter
            exec(cmd, {}, {})
        except Exception as e:
            raise RuntimeException("RuntimeError", f"Exec failed: {e}", line_idx+1)

    def _handle_if(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        cond_str = self.lines[curr_idx][3:].strip()
        if cond_str.endswith("{"):
            cond_str = cond_str[:-1].strip()
            
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        
        cond_val = self._eval_expr(cond_str, curr_idx)
        executed = False
        
        if cond_val:
            self._execute_block(block_start, block_end)
            executed = True
            
        next_idx = block_end + 1
        # Check for elif/else
        while next_idx < total_end:
            line = self.lines[next_idx].strip()
            if line.startswith("elif ") and not executed:
                c_str = line[5:].strip()
                if c_str.endswith("{"): c_str = c_str[:-1].strip()
                c_val = self._eval_expr(c_str, next_idx)
                b_start, b_end = self._get_block_bounds(next_idx, total_end)
                if c_val:
                    self._execute_block(b_start, b_end)
                    executed = True
                next_idx = b_end + 1
            elif line.startswith("elif ") and executed:
                # skip
                b_start, b_end = self._get_block_bounds(next_idx, total_end)
                next_idx = b_end + 1
            elif line.startswith("else"):
                b_start, b_end = self._get_block_bounds(next_idx, total_end)
                if not executed:
                    self._execute_block(b_start, b_end)
                next_idx = b_end + 1
                break
            else:
                break
                
        return next_idx - 1 # will be incremented in loop

    def _handle_while(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        cond_str = self.lines[curr_idx][6:].strip()
        if cond_str.endswith("{"):
            cond_str = cond_str[:-1].strip()
            
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        
        while self._eval_expr(cond_str, curr_idx):
            self._execute_block(block_start, block_end)
            # return bubbling can be added here if needed
            
        return block_end

    def _handle_for(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        # for i in range(0, 10) {
        match = re.match(r"for\s+([a-zA-Z_]\w*)\s+in\s+range\(\s*(.*?)\s*,\s*(.*?)\s*\)", self.lines[curr_idx])
        if not match:
            raise RuntimeException("SyntaxError", "Invalid for loop syntax", curr_idx+1)
            
        var_name = match.group(1)
        start_val = int(self._eval_expr(match.group(2), curr_idx))
        end_val = int(self._eval_expr(match.group(3), curr_idx))
        
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        
        for i in range(start_val, end_val):
            self.env[var_name] = i
            self._execute_block(block_start, block_end)
            
        return block_end

    def _handle_try(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        try_start, try_end = self._get_block_bounds(curr_idx, total_end)
        
        err_caught = None
        has_error = False
        try:
            self._execute_block(try_start, try_end)
        except RuntimeException as e:
            has_error = True
            err_caught = e
            
        next_idx = try_end + 1
        exec_else = not has_error
        
        while next_idx < total_end:
            line = self.lines[next_idx].strip()
            if line.startswith("except"):
                exc_start, exc_end = self._get_block_bounds(next_idx, total_end)
                if has_error:
                    # Expose .type and .message in a quick object
                    class ExcObj:
                        def __init__(self, t, m):
                            self.type = t
                            self.message = m
                    self.env["error"] = ExcObj(err_caught.err_type, err_caught.raw_message)
                    self._execute_block(exc_start, exc_end)
                next_idx = exc_end + 1
            elif line.startswith("else"):
                else_start, else_end = self._get_block_bounds(next_idx, total_end)
                if exec_else:
                    self._execute_block(else_start, else_end)
                next_idx = else_end + 1
            else:
                break
                
        return next_idx - 1

    def _handle_parallel(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        # parallel (4) {
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        # Sequential mockup for DSL for now, full multiprocessing maps to Workflow parallel nodes natively
        # But Origin script runs functionally here. 
        self._execute_block(block_start, block_end)
        return block_end

    def _handle_def(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        line = self.lines[curr_idx]
        match = re.match(r"def\s+([a-zA-Z_]\w*)\s*\((.*?)\)", line)
        if not match:
            raise RuntimeException("SyntaxError", "Invalid function definition", curr_idx+1)
            
        func_name = match.group(1)
        params_str = match.group(2)
        params = [p.strip() for p in params_str.split(",")] if params_str.strip() else []
        
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        
        self.functions[func_name] = {
            "params": params,
            "start": block_start,
            "end": block_end
        }
        
        return block_end

    def _handle_class(self, start_idx: int, total_end: int, curr_idx: int) -> int:
        line = self.lines[curr_idx]
        match = re.match(r"class\s+([a-zA-Z_]\w*)\s*\((.*?)\)", line)
        if not match:
            raise RuntimeException("SyntaxError", "Invalid class definition", curr_idx+1)
            
        cls_name = match.group(1)
        params_str = match.group(2)
        params = [p.strip() for p in params_str.split(",")] if params_str.strip() else []
        
        block_start, block_end = self._get_block_bounds(curr_idx, total_end)
        
        self.classes[cls_name] = {
            "params": params,
            "start": block_start,
            "end": block_end
        }
        return block_end

    def _handle_import(self, stmt: str, line_idx: int):
        parts = stmt.split()
        if len(parts) > 1:
            mod_name = parts[1]
            if mod_name == "math":
                pass # Native handled
            else:
                 raise RuntimeException("ImportError", f"Module {mod_name} not found", line_idx+1)

    def _handle_from_import(self, stmt: str, line_idx: int):
        # from math import sqrt
        pass # Track exports if needed, _eval_expr will map direct math identifiers.

    def _eval_expr(self, expr: str, line_idx: int) -> Any:
        expr = expr.strip()
        
        if expr.isdigit(): return int(expr)
        try:
            return float(expr)
        except ValueError:
            pass
            
        if expr == "true" or expr == "True": return True
        if expr == "false" or expr == "False": return False
        
        if expr.startswith('"') and expr.endswith('"'): return expr[1:-1]
        if expr.startswith("'") and expr.endswith("'"): return expr[1:-1]
        
        if expr.startswith("input("):
            prompt = expr[6:-1].strip()
            if prompt.startswith('"') and prompt.endswith('"'): prompt = prompt[1:-1]
            return input(prompt)
            
        if expr.startswith("int("):
            return int(self._eval_expr(expr[4:-1], line_idx))
            
        if expr.startswith("sqrt"):
            # sqrt 25 OR sqrt(25)
            arg = expr[4:].strip().strip("(").strip(")")
            return math.sqrt(float(self._eval_expr(arg, line_idx)))
            
        if expr.startswith("math.sqrt"):
            arg = expr[9:].strip().strip("(").strip(")")
            return math.sqrt(float(self._eval_expr(arg, line_idx)))

        if expr.startswith("rand_num"):
            # rand_num(1, 10)
            args = expr[8:].strip("()").split(",")
            return random.randint(int(self._eval_expr(args[0], line_idx)), int(self._eval_expr(args[1], line_idx)))

        if expr.startswith("len("):
            arg = expr[4:-1].strip()
            return len(self._eval_expr(arg, line_idx))
            
        if expr.startswith("[") and expr.endswith("]"):
            items = expr[1:-1].split(",")
            return [self._eval_expr(i, line_idx) for i in items if i.strip()]
            
        if expr.startswith("{") and expr.endswith("}"):
            res = {}
            items = expr[1:-1].split(",")
            for i in items:
                if ":" in i:
                    k, v = i.split(":", 1)
                    k_eval = self._eval_expr(k, line_idx)
                    v_eval = self._eval_expr(v, line_idx)
                    res[k_eval] = v_eval
            return res
            
        # Dictionary access my_dict{"a"}
        if "{" in expr and expr.endswith("}") and not expr.startswith("{"):
            name, key_str = expr[:-1].split("{", 1)
            key = self._eval_expr(key_str, line_idx)
            if name in self.env:
                if type(self.env[name]) is str: # "TypeError" runtime exception mapping backwards
                   raise RuntimeException("TypeError", "Dictionary access on non-dict", line_idx+1) 
                return self.env[name][key]

        # List access my_list[0]
        if "[" in expr and expr.endswith("]") and not expr.startswith("["):
            name, key_str = expr[:-1].split("[", 1)
            key = int(self._eval_expr(key_str, line_idx))
            if name in self.env:
                return self.env[name][key]
                
        # Simple math operators
        for op in ["+", "-", "*", "/"]:
            # Need a robust parser for arbitrary expressions, but simple split handles basic ones.
            # Using eval for simplicity, BUT MUST INJECT variables:
            pass

        # Try mapping to Python Eval safely with replaced variables
        try:
            # Simple token replacement
            tokens = re.split(r'(\+|-|\*|/|>|<|==|!=|<=|>=)', expr)
            res_str = ""
            for t in tokens:
                t = t.strip()
                if t in ["+", "-", "*", "/", ">", "<", "==", "!=", "<=", ">="]:
                    res_str += f" {t} "
                elif t in self.env:
                    v = self.env[t]
                    if isinstance(v, str): res_str += f"'{v}'"
                    else: res_str += str(v)
                elif t in self.consts:
                    v = self.env[t]
                    res_str += str(v)
                else:
                    res_str += t
                    
            if res_str.strip():
                # Call functions? 
                if "(" in res_str and ")" in res_str:
                    # Very basic function calling
                    name = res_str.split("(")[0].strip()
                    if name in self.functions:
                        arg_str = res_str.split("(")[1].split(")")[0]
                        args = [self._eval_expr(a, line_idx) for a in arg_str.split(",") if a]
                        # execute func block
                        f = self.functions[name]
                        # save env
                        old_env = self.env.copy()
                        for i, p in enumerate(f["params"]):
                            self.env[p] = args[i] if i < len(args) else None
                            
                        # Here a return value system requires tweaking _execute_block to bubble up returns.
                        # For now we'll just execute it
                        self._execute_block(f["start"], f["end"])
                        
                        self.env = old_env
                        return 0 # Default return
                        
                # Actually evaluate Python code - safe enough for local robot execution with DSL translation
                if "{" not in res_str: # avoid dict syntax breaking eval
                     return eval(res_str)
        except Exception:
            pass
            
        # Identifier fallback
        if expr in self.env:
            return self.env[expr]
            
        if expr in self.consts:
            return self.env[expr]

        raise RuntimeException("NameError", f"Unknown identifier or expression: {expr}", line_idx+1)
