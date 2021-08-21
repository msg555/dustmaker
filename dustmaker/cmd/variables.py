#!/usr/bin/env python3
"""
Sample script to manipulate level variables.
"""
import argparse
import json
import sys
from typing import Any, Dict, Tuple, Type

from dustmaker import DFReader, DFWriter
from dustmaker.variable import (
    Variable,
    VariableBool,
    VariableStruct,
    VariableInt,
    VariableUInt,
    VariableFloat,
    VariableString,
    VariableVec2,
    VariableArray,
)
from dustmaker.cmd.common import (
    run_utility,
    CliUtility,
)

KNOWN_VAR_FILE_HEADERS = {b"DF_STA", b"DF_CFG", b"DF_FOG"}

_VAR_TYPE_TO_SCHEMA: Dict[Type[Variable], str] = {
    VariableBool: "bool",
    VariableInt: "int",
    VariableUInt: "uint",
    VariableFloat: "float",
    VariableString: "string",
    VariableVec2: "vec2",
}

_SCHEMA_TO_VAR_TYPE: Dict[str, Type[Variable]] = {
    schema: var_type for var_type, schema in _VAR_TYPE_TO_SCHEMA.items()
}


def merge_schema(lhs: Any, rhs: Any) -> Any:
    """Merge two schemas and return the result.

    Arguments:
        lhs (schema): First schema to merge
        rhs (schema): Second schema to merge
    """
    if isinstance(lhs, dict) and isinstance(rhs, dict):
        result = dict(lhs)
        for subkey, subschema in rhs.items():
            r_subschema = result.get(subkey)
            if r_subschema is None:
                result[subkey] = subschema
            else:
                result[subkey] = merge_schema(r_subschema, subschema)
        return result
    if isinstance(lhs, list) and isinstance(rhs, list):
        return [merge_schema(lhs[0], rhs[0])]
    if not isinstance(lhs, str) or not isinstance(rhs, str):
        raise ValueError("unmergable schemas")
    if lhs != rhs:
        raise ValueError(f"differing schemas {lhs} and {rhs}")
    return lhs


def json_to_variables(schema: Any, jvars: Any) -> Variable:
    """Convert JSON variable serialization back into a :class:`Variable`.
    This is the inverse of :meth:`variables_to_json`.

    Arguments:
        schema (schema): The JSON serialized schema as returned from
            :meth:`variables_to_json`
        jvars: The JSON serialized variables as returned from
            :meth:`variables_to_json`

    Returns:
        A :class:`Variable` as the deserialized JSON.
    """
    if isinstance(schema, list):
        element_type: Type[Variable]
        if isinstance(schema[0], list):
            element_type = VariableArray
        elif isinstance(schema[0], dict):
            element_type = VariableStruct
        else:
            element_type = _SCHEMA_TO_VAR_TYPE[schema[0]]

        return VariableArray(
            element_type,
            [json_to_variables(schema[0], elem_jvar) for elem_jvar in jvars],
        )
    if isinstance(schema, dict):
        return VariableStruct(
            {
                key: json_to_variables(schema[key], elem_jvar)
                for key, elem_jvar in jvars.items()
            }
        )
    if schema == "string":
        return VariableString(jvars.encode("latin1"))
    if schema == "vec2":
        return VariableVec2(tuple(jvars))  # type: ignore
    return _SCHEMA_TO_VAR_TYPE[schema](jvars)


def variables_to_json(var: Variable) -> Tuple[Any, Any]:
    """Serialize `var` into a (`schema`, `jvar`) tuple, each of which
    is JSON serializable and human readable.

    Arguments:
        var (Variable): The variable to serialize

    Returns:
        The schema and jvar serialization as a two-tuple.
    """
    if isinstance(var, VariableString):
        return ("string", var.value.decode("latin1"))
    if isinstance(var, VariableVec2):
        return ("vec2", list(var.value))
    if type(var) in _VAR_TYPE_TO_SCHEMA:
        return _VAR_TYPE_TO_SCHEMA[type(var)], var.value

    schema: Any
    if isinstance(var, VariableStruct):
        schema = {}
        jvars = {}
        for subkey, subvar in var.value.items():
            subschema, subjvar = variables_to_json(subvar)
            schema[subkey] = subschema
            jvars[subkey] = subjvar
        return schema, jvars
    if isinstance(var, VariableArray):
        # pylint: disable=redefined-variable-type
        if var.element_type is VariableArray:
            schema = [[]]
        elif var.element_type is VariableStruct:
            schema = [{}]
        else:
            schema = [_VAR_TYPE_TO_SCHEMA[var.element_type]]

        jvar = []
        for elem_var in var.value[1]:
            elem_schema, elem_jvar = variables_to_json(elem_var)
            jvar.append(elem_jvar)
            schema = merge_schema(schema, [elem_schema])
        return schema, jvar

    raise ValueError("unexpected variable type")


class Variables(CliUtility):
    """CLI utility for viewing and modifying level variables"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Read CLI arguments"""
        parser.description = (
            "view or modify DF variables as JSON documents. Strings are "
            "encoded/decoded from their internal byte representation using "
            "latin1 encoding."
        )
        parser.add_argument("object")
        parser.add_argument("new_data", nargs="?")
        parser.add_argument(
            "--header",
            default="",
            required=False,
            help="write file from scratch with given header",
        )
        parser.add_argument(
            "--indent",
            default=4,
            required=False,
            type=int,
            help="JSON indent amount in spaces. Use 0 to do no indentation",
        )

    def main(self, args) -> int:
        """thumbnail CLI entrypoint"""
        if args.new_data:
            return self.update_variables(args)
        return self.output_variables(args)

    @staticmethod
    def update_variables(args) -> int:
        """Update the variables in the object requested"""
        with open(args.new_data, "r") as ndata:
            jdata = json.load(ndata)

        if args.header:
            header = args.header.encode()
            if header not in KNOWN_VAR_FILE_HEADERS:
                sys.stderr.write(f"cannot write {header} file")
                return 1
        else:
            with DFReader(open(args.object, "rb")) as reader:
                header = reader.read_bytes(6)
                reader.bit_seek(0)
                if header == b"DF_LVL":
                    level, region_offsets = reader.read_level_ex()
                    region_data = reader.read_bytes(region_offsets[-1])
                elif header not in KNOWN_VAR_FILE_HEADERS:
                    sys.stderr.write(f"unknown file header {header}\n")
                    return 1

        variables = json_to_variables(jdata["schema"], jdata["vars"])

        with DFWriter(open(args.object, "wb")) as writer:
            if header == b"DF_LVL":
                level.variables = variables.value
                writer.write_level_ex(level, region_offsets, region_data)
            else:
                writer.write_var_file(header, variables.value)

        return 0

    @staticmethod
    def output_variables(args) -> int:
        """Output the variables of the object requested"""
        with DFReader(open(args.object, "rb")) as reader:
            header = reader.read_bytes(6)
            reader.bit_seek(0)
            if header == b"DF_LVL":
                level = reader.read_level(metadata_only=True)
                variables = level.variables
            elif header in KNOWN_VAR_FILE_HEADERS:
                variables = reader.read_var_file(header)
            else:
                sys.stderr.write(f"unknown file header {header}\n")
                return 1

        schema, jvars = variables_to_json(VariableStruct(variables))

        json.dump(
            {
                "vars": jvars,
                "schema": schema,
            },
            sys.stdout,
            indent=args.indent if args.indent else None,
        )

        return 0


if __name__ == "__main__":
    sys.exit(run_utility(Variables))
