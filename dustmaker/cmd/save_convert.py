"""
CLI entrypoint for converting vanilla save files to Dustmod save files.
"""
import argparse
import sys
from typing import Any

from dustmaker import DFReader, DFWriter
from dustmaker.variable import (
    VariableArray,
    VariableBool,
    VariableInt,
    VariableStruct,
    VariableString,
    VariableFloat,
)
from dustmaker.cmd.common import (
    run_utility,
    CliUtility,
)


COPY_KEYS = (
    "citybook",
    "custombook",
    "forestbook",
    "labbook",
    "leveleditorbook",
    "mansionbook",
    "userbook",
    "virtualbookk",
)

LEVEL_KEYS = {
    level: (level_ind // 4) % 4
    for level_ind, level in enumerate(
        (
            b"downhill",
            b"shadedgrove",
            b"dahlia",
            b"fields",
            b"momentum",
            b"fireflyforest",
            b"tunnels",
            b"momentum2",
            b"suntemple",
            b"ascent",
            b"summit",
            b"grasscave",
            b"den",
            b"autumnforest",
            b"garden",
            b"hyperdifficult",
            b"atrium",
            b"secretpassage",
            b"alcoves",
            b"mezzanine",
            b"cave",
            b"cliffsidecaves",
            b"library",
            b"courtyard",
            b"precarious",
            b"treasureroom",
            b"arena",
            b"ramparts",
            b"moontemple",
            b"observatory",
            b"parapets",
            b"brimstone",
            b"vacantlot",
            b"sprawl",
            b"development",
            b"abandoned",
            b"park",
            b"boxes",
            b"chemworld",
            b"factory",
            b"tunnel",
            b"basement",
            b"scaffold",
            b"cityrun",
            b"clocktower",
            b"concretetemple",
            b"alley",
            b"hideout",
            b"control",
            b"ferrofluid",
            b"titan",
            b"satellite",
            b"vat",
            b"venom",
            b"security",
            b"mary",
            b"wiringfixed",
            b"containment",
            b"orb",
            b"pod",
            b"mary2",
            b"coretemple",
            b"abyss",
            b"dome",
        )
    )
}

KEY_NAMES = ["wood", "silver", "gold", "red"]


def _convert_combo(combo_breaks: int) -> int:
    """
    Return a letter grade (5=S, 1=D) given number of combo breaks.
    """
    if combo_breaks < 0:
        return 0
    if combo_breaks == 0:
        return 5
    if combo_breaks <= 1:
        return 4
    if combo_breaks <= 3:
        return 3
    if combo_breaks <= 5:
        return 2
    return 1


def _convert_thorough(thorough: float) -> int:
    """
    Return a letter grade given the percent thoroughness. (5=S, 1=D)
    """
    if thorough >= 100:
        return 5
    if thorough >= 90:
        return 4
    if thorough >= 80:
        return 3
    if thorough >= 60:
        return 2
    if thorough < 0:
        return 0
    return 1


def migrate_stats(stats: dict) -> dict:
    """
    Migrate a stats structure from vanilla format to Dustmod format.
    """
    new_stats = {key: val for key, val in stats.items() if key in COPY_KEYS}

    # new_stats["k_gold_used"] = VariableArray(
    #    VariableInt,
    # print(stats)

    def _get_default(obj: dict, key: str, default: Any) -> Any:
        val = obj.get(key)
        print(val, type(val))
        if val is None:
            return default
        return val.value

    new_scores = []
    keys_earned = [0, 0, 0, 0]
    keys_used = [0, 0, 0, _get_default(stats, "red_used", 0)]
    for score in stats.get("score", []):
        level = score["file_name"].value
        key = LEVEL_KEYS.get(level, -1)
        if key == -1:
            continue
        if key > 0:
            keys_used[key - 1] += 1

        keys_earned[key] += _convert_combo(score["combo"].value) + _convert_thorough(
            score["thorough"].value
        )
        new_scores.append(
            VariableStruct(
                {
                    "rind": VariableInt(0),
                    "file_name": VariableString(level),
                    "combo": VariableInt(score["combo"].value),
                    "time": VariableFloat(score["time"].value),
                    "thorough": VariableFloat(score["thorough"].value),
                    "best_time": VariableFloat(score["best_time"].value),
                    "overall": VariableInt(score["overall"].value),
                    # wood keys have id 4 instead of 0.
                    "key_type": VariableInt(4 if key == 0 else key),
                }
            )
        )

    new_scores.sort(key=lambda score: score.value["file_name"].value)
    new_stats["k_score"] = VariableArray(VariableStruct, new_scores)
    new_stats["k_root"] = VariableArray(VariableString, [VariableString(b"")])
    new_stats["k_wood_used"] = VariableArray(VariableInt, [VariableInt(keys_used[0])])
    new_stats["k_silver_used"] = VariableArray(VariableInt, [VariableInt(keys_used[1])])
    new_stats["k_gold_used"] = VariableArray(VariableInt, [VariableInt(keys_used[2])])
    new_stats["k_red_used"] = VariableArray(VariableInt, [VariableInt(keys_used[3])])
    new_stats["k_ngplus"] = VariableArray(VariableBool, [VariableBool(False)])

    return new_stats


class SaveConvert(CliUtility):
    """CLI utility for convert vanilla saves to Dustmod saves"""

    HEADER = b"DF_STA"

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.description = "convert vanilla save to dustmod save"
        parser.add_argument(
            "stats0",
            help="Path to vanilla stats0 file",
        )
        parser.add_argument(
            "stats1",
            help="Path to write new dustmod stats1 file",
        )

    def main(self, args) -> int:
        with DFReader(open(args.stats0, "rb")) as reader:
            stats = reader.read_var_file(self.HEADER)
        if not isinstance(stats, dict):
            raise ValueError("found unexpected data in stats0")
        stats_new = migrate_stats(stats)
        with DFWriter(open(args.stats1, "wb")) as writer:
            writer.write_var_file(self.HEADER, stats_new)
        return 0


if __name__ == "__main__":
    sys.exit(run_utility(SaveConvert))
