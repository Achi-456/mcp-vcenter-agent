"""
ai_tool_registry.py
===================
Dynamic tool discovery for Claude AI. Scans vcenter_tools.py to auto-generate
Anthropic tool schemas based on Python docstrings and type hints.
"""

import inspect
import importlib
from typing import Any

# Import the module we want to scan
import app.tools.vcenter as vc

def _python_type_to_schema(py_type) -> str:
    """Map python type hints to JSON schema types."""
    if py_type == int:
        return "integer"
    elif py_type == bool:
        return "boolean"
    elif py_type == str:
        return "string"
    elif py_type == float:
        return "number"
    elif hasattr(py_type, "__origin__") and py_type.__origin__ == list:
        return "array"
    # Default to string for unknown/complex types
    return "string"

def get_dynamic_tools() -> tuple[list[dict], dict]:
    """
    Scans vcenter_tools.py and builds the Anthropic AI_TOOLS schema array
    and the dispatch map for execution.
    """
    tools = []
    dispatch_map = {}
    
    # Get all functions defined in the vcenter_tools module
    for name, func in inspect.getmembers(vc, inspect.isfunction):
        # Ignore private functions
        if name.startswith("_"):
            continue
            
        # Ensure the function is actually defined in vcenter_tools (not an import)
        if getattr(func, "__module__", "") != "app.tools.vcenter":
            continue
            
        doc = inspect.getdoc(func) or f"Execute {name}."
        sig = inspect.signature(func)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
                
            param_type = _python_type_to_schema(param.annotation)
            prop = {"type": param_type}
            
            # Check if parameter has a default value
            if param.default != inspect.Parameter.empty:
                # If the type hint was missing but there's a default, infer type
                if param.annotation == inspect.Parameter.empty:
                    prop["type"] = _python_type_to_schema(type(param.default))
            else:
                required.append(param_name)
                
            properties[param_name] = prop
            
        input_schema = {
            "type": "object",
            "properties": properties
        }
        
        if required:
            input_schema["required"] = required
            
        tool_schema = {
            "name": name,
            "description": doc,
            "input_schema": input_schema
        }
            
        tools.append(tool_schema)
        dispatch_map[name] = func

    tools.sort(key=lambda t: t["name"])
    return tools, dispatch_map


def invoke_tool(
    name: str, arguments: dict | None, dispatch_map: dict | None = None
) -> Any:
    """
    Call a vCenter tool by name. Only keyword arguments that match the
    function signature are passed through.
    """
    if arguments is None:
        arguments = {}
    if dispatch_map is None:
        _, dispatch_map = get_dynamic_tools()
    if name not in dispatch_map:
        return {"error": f"Unknown tool: {name}"}
    func = dispatch_map[name]
    sig = inspect.signature(func)
    params = sig.parameters
    kwargs = {k: v for k, v in arguments.items() if k in params}
    return func(**kwargs)


def reload_tools():
    """Hot-reloads the vcenter module from disk while preserving the live vCenter connection singleton."""
    prev_conn = getattr(vc, "_conn", None)
    importlib.reload(vc)
    if prev_conn is not None and getattr(prev_conn, "si", None) is not None:
        new_conn = getattr(vc, "_conn", None)
        if new_conn is not None:
            new_conn.si = prev_conn.si
            new_conn.content = prev_conn.content
