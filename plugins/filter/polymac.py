#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Todd M. Lewis <utoddl@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

DOCUMENTATION = """
    lookup: polymac
    author: Todd Lewis <utoddl@gmail.com>
    version_added: "2.9.9"
    short_description: duplicate dicts with variable substitutions.
    description:
      - |
        Dict key C(polymac) will replace indicated variables within
        its data section(s) with their values as defined in one or
        more substitution sets. The resulting data is then
        incorporated into the data structure which originally
        contained the "polymac" key.

      - |
        C(polymac) expects to contain a list. The first item should
        contain either a single dict or a list of dicts which are
        themselves key/value pairs in substitution sets. Subsequent
        items should contain arbitrary data structures. Within these
        data structures, substrings consisting of substitution keys
        between '%' characters will be replaced with corresponding
        values from the substitution sets.

      - |
        The "mac" part of the name comes from "macro expansion"
        wherein substrings bounded by '%' get replaced. The "poly"
        part comes from the Greek "polus": much or many, because the
        number of produced data structures will be the product of the
        number of substitution sets and the number of data sections
        in the "polymac".

      - |
        The data structure resulting from a "polymac" may be a dict or
        a list. How it is incorporated back into the containing data
        structure depends on whether it's a single value, a single
        dict, or a list, and how "polymac" itself was positioned in
        its containing data. If "polymac" is the only key at its
        level, then the expanded data can simply replace it.
        But if "polymac" is not the only key at its level, then a
        single dict will be merged with polymac's containing dict,
        while lists of N results (N>1) will cause N copies and merges
        of the containing dict.

    options:
      _terms:
        description:
          - Data possibly containing "polymac" keys.
        required: true
      debug:
        type: bool
        default: False
        description:
          - Dump lots of messages about traversing and modifying the
            data passed to polymac.
"""

EXAMPLES = """
- name: one substitution set, one data section
  debug: msg="{{ some_dict | polymac | to_nice_yaml(indent=2, width=1337) }}
  vars:
    some_dict:
      name: example the first
      fruit: apple
      polymac:
        - season: spring
          color:  green
          pick:   you'd be crazy to try
        - almanac: "In the %season% when they are %color%, %pick% to pick them."

# Produces a single dict with a single key. This dict gets merged into
# the containing dict at the position of the "polymac" key.
#
#   some_dict:
#     name: example the first
#     fruit: apple
#     almanac: In the spring when they are green you'd be crazy to try to pick them.

- name: three substitution sets, one data section
  debug: msg="{{ some_dict | polymac | to_nice_yaml(indent=2, width=1337) }}
  vars:
    some_dict:
      name: example the second
      fruit: apple
      almanac:
        polymac:
          - - season: spring
              color:  green
              pick:   you'd be crazy to try
            - season: summer
              color:  turning
              pick:   it's still too soon
            - season: fall
              color:  red
              pick:   it is time
          - "In the %season% when they are %color%, %pick% to pick them."
# Produces a list of three strings. Since "polymac" is a lone key,
# its dict can be replaced by the list.
#   some_dict:
#     name: example the second
#     fruit: apple
#     almanac:
#       - In the spring when they are green you'd be crazy to try to pick them.
#       - In the summer when they are turning, it's still too soon to pick them.
#       - In the fall when they are red, it is time to pick them.

- name: three substitution sets, one data section
  debug: msg="{{ some_dict | polymac | to_nice_yaml(indent=2, width=1337) }}
  vars:
    some_dict:
      name: This value will be replaced three times.
      fruit: apple
      polymac:
        - - season: spring
            color:  green
            pick:   you'd be crazy to try
          - season: summer
            color:  turning
            pick:   it's still too soon
          - season: fall
            color:  red
            pick:   it is time
        - name: Almanac for %season%
          almanac: "In the %season% when they are %color%, %pick% to pick them."
# Produces a list of three dicts. Because "polymac" has siblings, the
# dict containing it gets duplicated three times with each of the
# produced dicts merged into their respective copies.
#   some_dict:
#     - name: Almanac for spring
#       fruit: apple
#       almanac: In the spring when they are green you'd be crazy to try to pick them.
#     - name: Almanac for summer
#       fruit: apple
#       almanac:  In the summer when they are turning, it's still too soon to pick them.
#     - name: Almanac for fall
#       fruit: apple
#       almanac:  In the fall when they are red, it is time to pick them.

- name: environment strings may contain other environment strings
  debug: msg="{{ some_dict | polymac | to_nice_yaml(indent=2, width=1337) }}"
  vars:
    some_dict:
      title: The Twelve Days of Christmas
      lyrics:
        polymac:
          - DayOf: "day of Christmas my true love gave to me\\n"
            1st:   "a partridge in a pear tree."
            2nd:   "two turtle doves,\\nand %1st%"
            3rd:   "three French hens,\\n%2nd%"
            4th:   "four calling birds,\\n%3rd%"
            5th:   "five golden rings,\\n%4th%"
            6th:   "six geese a laying,\\n%5th%"
            7th:   "seven swans a swimming,\\n%6th%"
            8th:   "eight maids a milking,\\n%7th%"
            9th:   "nine ladies dancing,\\n%8th%"
            10th:  "ten lords a leaping,\\n%9th%"
            11th:  "eleven pipers piping,\\n%10th%"
            12th:  "twelve drummers drumming,\\n%11th%"
          - "On the first %DayOf%%1st%"
          - "On the second %DayOf%%2nd%"
          - "On the third %DayOf%%3rd%"
          - "On the fourth %DayOf%%4th%"
          - "On the fifth %DayOf%%5th%"
          - "On the sixth %DayOf%%6th%"
          - "On the seventh %DayOf%%7th%"
          - "On the eighth %DayOf%%8th%"
          - "On the nineth %DayOf%%9th%"
          - "On the tenth %DayOf%%10th%"
          - "On the eleventh %DayOf%%11th%"
          - "On the twelfth %DayOf%%12th%"
# Produces:
#   some_dict:
#     title: The Twelve Days of Christmas
#     lyrics:
#       - |
#         On the first day of Christmas my true love gave to me
#         a partridge in a pear tree.
#       - |
#         On the second day of Christmas my true love gave to me
#         two turtle doves,
#         and a partridge in a pear tree.
# [...]
#       - |
#         On the twelfth day of Christmas my true love gave to me
#         twelve drummers drumming,
#         eleven pipers piping,
#         ten lords a leaping,
#         nine ladies dancing,
#         eight maids a milking,
#         seven swans a swimming,
#         six geese a laying,
#         five golden rings,
#         four calling birds,
#         three French hens,
#         two turtle doves,
#         and a partridge in a pear tree.
"""

RETURN = """
_raw:
   description: inputs after polymac applied.
"""

__metaclass__ = type

# import os
import re
import inspect
from copy import deepcopy
from ansible.errors import AnsibleError

from ansible.plugins.filter.core import flatten
from ansible.module_utils.six import string_types

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()

show_debug_messages = False

_pd_prefix = ""


def pd(str, delta=0):
    global _pd_prefix
    if delta > 0:
        _pd_prefix = " " + _pd_prefix
    elif delta < 0 and len(_pd_prefix):
        _pd_prefix = _pd_prefix[1:]
    dbg("{}{}".format(_pd_prefix, str))


def dbg(msg):
    if show_debug_messages:
        display.vv(msg)


def polymac(terms, debug=False):
    global show_debug_messages
    show_debug_messages = debug
    polymacd = []
    dbg(u"polymac({}): {}".format(lineno(), terms))
    if isinstance(terms, dict):
        polymacd = polymacdict(terms, 1, {})
    elif isinstance(terms, list):
        polymacd = polymaclist(terms, 1, {})
    else:
        polymacd = terms
    return polymacd


def lineno():
    """Returns the line number whence lineno() was called."""
    return inspect.currentframe().f_back.f_lineno


def polymacdict(mydict, level, env):
    ret = {}
    keycount = len(mydict)
    for key in mydict.keys():
        dbg(u"{}polymacdict({}): level {} {}: {}".format((" " * level), lineno(), level, key, type_or_str(mydict[key])))
        if isinstance(mydict[key], list):
            ret[key] = polymaclist(mydict[key], level + 1, env if key != 'polymac' else {})
        elif isinstance(mydict[key], dict):
            ret[key] = polymacdict(mydict[key], level + 1, env if key != 'polymac' else {})
        else:
            ret[key] = mydict[key]
        if isinstance(key, string_types) and key != "polymac":
            dbg(u"{}polymacdict({}): level {} adding env['{}']='{}'".format((" " * level), lineno(), level, key, mydict[key]))
            env[key] = mydict[key]
    if "polymac" in mydict:
        dbg(u"{}polymacdict({}): {} processing 'polymac' with 'macronate()'".format((" " * level), lineno(), level))
        macronated = macronate(mydict["polymac"], level + 1, env)
        dbg(u"{}polymacdict({}): {} processed: {}".format((" " * level), lineno(), level, macronated))
        if isinstance(macronated, list) and len(macronated) == 1:
            macronated = macronated[0]
            dbg(u"{}polymacdict({}): {} reduced: {}".format((" " * level), lineno(), level, macronated))
        if keycount == 1:
            return macronated
        if isinstance(macronated, list):
            dbg(u"{}polymacdict({}): macronated is a list.".format((" " * level), lineno(), level))
            retl = []
            del ret["polymac"]
            for item in macronated:
                t = deepcopy(ret)
                if isinstance(item, dict):
                    for key in item:
                        t[key] = item[key]
                    retl.append(t)
                else:  # It's a scalar or a list, so we append as a list
                    retl.append([t, item])
            ret = retl
        elif isinstance(macronated, dict):
            del ret["polymac"]
            for mkey in macronated:
                ret[mkey] = macronated[mkey]

        dbg(u"{}polymacdict({}): {} processing 'polymac' with 'macronate()' returned {}".format((" " * level), lineno(), level, type_or_str(macronated)))
        dbg(u"{}polymacdict({}): {}   {}".format((" " * level), lineno(), level, macronated))
    return ret


def polymaclist(mylist, level, env):
    ret = []
    for item in mylist:
        dbg(u"{}polymaclist({}): level {} {}".format((" " * level), lineno(), level, type_or_str(item)))
        if isinstance(item, list):
            ret.append(polymaclist(item, level + 1, env))
        elif isinstance(item, dict):
            dictout = polymacdict(item, level + 1, env)
            if isinstance(dictout, list):
                for ditem in dictout:
                    ret.append(ditem)
            else:
                ret.append(dictout)
        else:
            ret.append(item)
    return ret


def macronate(metadata, level, env):
    pd(">>>macronate[{}]: metadata={},\n level={},\n env={}".format(lineno(), metadata, level, env), 1)
    macrodata = flatten([metadata], 1)
    pd("===macronate[{}]: macrodata={}".format(lineno(), macrodata))
    if len(macrodata) < 2:
        macrodata.insert(0, flatten([env], 1))
        pd("===macronate[{}]: macrodata={}".format(lineno(), macrodata))
    ret = []

    for envn in flatten([macrodata[0]], 1):
        pd("===macronate[{}]: envn={}".format(lineno(), envn))
        for datam in flatten(macrodata[1:], 1):
            pd("==+macronate[{}]: datam={}\n envn={}".format(lineno(), datam, envn))
            datan = update_data(datam, envn)
            pd("=++macronate[{}]: datan={}\n env={}".format(lineno(), datan, env))
            datao = update_data(datan, env)
            ret.append(datao)
    pd("<<<macronate[{}]:".format(lineno()), -1)
    return ret


def update_data_string(data, env):
    pd(">>>update_data_string[{}]:(data={}, env={})".format(lineno(), type_or_str(data), type_or_str(env)), 1,)
    while True:
        changes = 0
        for key in env:
            pd("update_data_string[{}]: env[{}]".format(lineno(), key))
            if data == "%" + key + "%":
                pd("update_data_string[{}]: env[{}]: exact match found ({})".format(lineno(), key, env[key]))
                data = update_data(env[key], env)
                pd("update_data_string[{}]: env[{}] exact match produced '{}'".format(lineno(), key, type_or_str(data)))
                break
            elif isinstance(env[key], string_types):
                chng = re.subn(re.escape("%" + key + "%"), env[key], data, count=0, flags=0)
                if chng[1]:
                    data = chng[0]
                    changes = changes + chng[1]
                    pd("update_data_string[{}]: data='{}'".format(lineno(), data))
        if changes == 0:
            break
    pd("<<<update_data_string[{}]: '{}'".format(lineno(), data), -1)
    return data


def update_data_list(data, env):
    pd(
        ">>>update_data_list[{}]:(data={}, env={})".format(lineno(), type_or_str(data), type_or_str(env)), 1,
    )
    for i, val in enumerate(data):
        pd("update_data_list[{}]: #{}".format(lineno(), i + 1))
        data[i] = update_data(val, env)
    pd("<<<update_data_list[{}]:".format(lineno()), -1)
    return data


def update_data_dict(data, env):
    pd(">>>update_data_dict[{}]:(data={}, env={})".format(lineno(), data, env), 1)
    # for key in env:
    #     pd("update_data_dict[{}]: env[{}]".format(lineno(), key))
    #     if key in data:
    #         pd("update_data_dict[{}]: env[{}] deepcopy({})".format(lineno(), key, env[key]))
    #         data[key] = deepcopy(env[key])
    for key in data:
        pd("update_data_dict[{}]: data[{}]".format(lineno(), key))
        data[key] = update_data(data[key], env)
    pd("<<<update_data_dict[{}]:".format(lineno()), -1)
    return data


def update_data(data, env):
    ret = deepcopy(data)
    pd(">>>update_data[{}]:(data={}, env={})".format(lineno(), type_or_str(data), type_or_str(env)), 1,)
    if ret:
        if isinstance(ret, dict):
            ret = update_data_dict(ret, env)
        elif isinstance(ret, list):
            ret = update_data_list(ret, env)
        elif isinstance(ret, string_types):
            ret = update_data_string(ret, env)
    pd("<<<update_data[{}]:".format(lineno()), -1)
    return ret


def type_or_str(term):
    if isinstance(term, string_types):
        return term
    else:
        return type(term)


def deepmerge(merge_vals, dedup, recursive_dict_merge, master_key):
    if len(merge_vals) == 0:
        merged = []
    elif isinstance(merge_vals[0], list):
        merged = merge_list(merge_vals, dedup, recursive_dict_merge, master_key)
    elif isinstance(merge_vals[0], dict):
        merged = merge_dict(merge_vals, dedup, recursive_dict_merge, master_key)
    else:
        raise AnsibleError("While handling '{}': Don't know how to merge variables of type: {}".format(master_key, type(merge_vals[0])))
    return merged


def merge_dict(merge_vals, dedup, recursive_dict_merge, master_key):
    """
    To merge dicts, just update one with the values of the next, etc.
    """
    check_type(merge_vals, dict, master_key)
    merged = {}

    for val in merge_vals:
        if not recursive_dict_merge:
            merged.update(val)
        else:
            # Recursive merging of dictionaries with overlapping keys:
            #   LISTS: merge with merge_list
            #   DICTS: recursively merge with merge_dict
            #   any other types: replace (same as usual behaviour)
            for key in val.keys():
                if key not in merged:
                    # first hit of the value - just assign
                    merged[key] = val[key]
                elif isinstance(merged[key], list):
                    merged[key] = merge_list([merged[key], val[key]], dedup, recursive_dict_merge)
                elif isinstance(merged[key], dict):
                    merged[key] = merge_dict([merged[key], val[key]], dedup, recursive_dict_merge)
                else:
                    merged[key] = val[key]
    return merged


def merge_list(merge_vals, dedup, recursive_dict_merge, master_key):
    """ To merge lists, just concat them. Dedup if wanted. """
    check_type(merge_vals, list, master_key)
    flatten_levels = 0
    if recursive_dict_merge:
        flatten_levels = 999
    merged = flatten(merge_vals, flatten_levels)
    if dedup:
        merged = deduplicate(merged)
    return merged


def check_type(mylist, _type, master_key):
    """ Ensure that all members of mylist are of type _type. """
    if not all([isinstance(item, _type) for item in mylist]):
        raise AnsibleError("While handling '{}', all values to merge must be of the same type.".format(master_key))


# def flatten(list_of_lists, levels=None):
#     """
#     Flattens a list of lists:
#         >>> flatten([[1, 2] [3, 4]])
#         [1, 2, 3, 4]
#
#     I wish Python had this in the standard lib :(
#     """
#     return list((x for y in list_of_lists for x in y))


def deduplicate(mylist):
    """
    Just brute force it. This lets us keep order, and lets us dedup unhashable
    things, like dicts. Hopefully you won't run into such big lists that
    this will ever be a performance issue.
    """
    deduped = []
    for item in mylist:
        if item not in deduped:
            deduped.append(item)
    return deduped


class FilterModule(object):
    def filters(self):
        return {"polymac": polymac}
