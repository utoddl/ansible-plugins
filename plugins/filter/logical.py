from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# import os
import re
import inspect

from ansible.errors import AnsibleError
from ansible.plugins.filter.core import flatten
from ansible.module_utils.six import string_types

DOCUMENTATION = """
    lookup: logical
    author: Todd Lewis <todd_lewis@unc.edu>
    version_added: "2.7.10"
    short_description: evaluate if/elif/else/and/or/not in data.
    description:
      - Data embedded with single item dict keys if/elif/else/and/or/not
        are evaluated and the remaining data replaces the top level if.
        Keys prefixed with '<<' will have their contents promoted up
        one level where possible.
    options:
      _terms:
        description:
          - Data containing logical operations.
        required: true
"""

EXAMPLES = """
- name: show evaluated variable
  debug: msg="{{ some_dict | logical | to_nice_yaml(indent=8, width=1337) }}
"""

RETURN = """
_raw:
   description: inputs after logic applied.
"""

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

# A promotion is always prefix by "<<" followed by an optional modifier:
#   "<<"   matching keys are replaced by promoted keys
#   "<<|"  matching keys are deep merged, lists are joined and flattened
#   "<<-"  matching keys are deep merged, lists are joined, flattened, and uniqified

promote_re = re.compile('^(<<[|-]?)(.*)')
show_debug_messages = False


def dbg(msg):
    if show_debug_messages:
        display.vv(msg)


def logical(terms, debug=False):
    global show_debug_messages
    show_debug_messages = debug
    logicked = []
    if isinstance(terms, dict):
        logicked = logicdict(terms, 1)
    elif isinstance(terms, list):
        logicked = logiclist(terms, 1)
    else:
        logicked = terms
        # raise AnsibleError(
        #     "logical filter doesn't know how to process variables of type '{}'.".format(type(terms))
        # )
    return logicked


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def logicdict(mydict, level=0, inkey=''):
    ret = {}
    keycount = len(mydict)
    for key in mydict.keys():
        if key == 'and':
            dbg(u"{}logicdict({}): {} processing 'and'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'and' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicand(mydict[key], level+1)
        elif key == 'or':
            dbg(u"{}logicdict({}): {} processing 'or'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'or' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicor(mydict[key], level+1)
        elif key == 'xor':
            dbg(u"{}logicdict({}): {} processing 'xor'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'xor' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicxor(mydict[key], level+1)
        elif key == 'not':
            dbg(u"{}logicdict({}): {} processing 'not'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'not' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicnot(mydict[key], level+1)
        elif key == 'if':
            dbg(u"{}logicdict({}): {} processing 'if'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'if' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicif(mydict[key], level+1, key)
        elif key == 'elif':
            dbg(u"{}logicdict({}): {} processing 'elif'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'elif' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicif(mydict[key], level+1, key)
        elif key == 'else':
            dbg(u"{}logicdict({}): {} processing 'else'".format((' '*level), lineno(), level))
            if keycount > 1:
                raise AnsibleError("Key 'else' must be the only key; found {} keys: {}.".format(keycount, ','.join(mydict.keys())))
            ret = logicif(mydict[key], level+1, key)
        elif isinstance(mydict[key], list):
            dbg(u"{}logicdict({}): found {} {}->(list)".format((' '*level), lineno(), level, key))
            ret[key] = logiclist(mydict[key], level+1, key)
        elif isinstance(mydict[key], dict):
            dbg(u"{}logicdict({}): found {} {}->(dict)".format((' '*level), lineno(), level, key))
            ret[key] = logicdict(mydict[key], level+1, key)
        else:
            dbg(u"{}logicdict({}): found {} {}->{}".format((' '*level), lineno(), level, key, type_or_str(mydict[key])))
            ret[key] = mydict[key]
    if isinstance(ret, dict):
        for key in list(ret):  # rather than ret.keys() b/c we'll be changing these
            mo = promote_re.match("{}".format(key))
            if mo:
                dedup = False
                merge = False
                if mo.group(1) == '<<-':
                    dedup = True
                    merge = True
                elif mo.group(1) == '<<|':
                    merge = True
                tmp = ret.pop(key)
                dbg(u"{}logicdict({}): {} promoting {} tmp:{}".format((' '*level), lineno(), level, key, tmp))
                if not isinstance(tmp, list):
                    tmp = [tmp]
                for i in reversed(range(len(tmp))):
                    if isinstance(tmp[i], dict):
                        for k in list(tmp[i]):  # rather than tmp[i].keys()
                            dbg(u"{}logicdict({}): {} promoting mo.group(1): '{}'".format((' '*level), lineno(), level, mo.group(1)))
                            dbg(u"--- k in ret:{}".format(k in ret))
                            if k in ret:
                                dbg(u"--- isinstance(ret[k], type(tmp[i][k])) ({}, {})".format(type(ret[k]), type(tmp[i][k])))
                                dbg(u"--- type(ret[k]) in [dict, list] ({})".format(type(ret[k])))
                            if merge and k in ret:
                                ret[k] = deepmerge([ret.pop(k), tmp[i].pop(k)], dedup, merge, key)    # merge_vals, dedup, recursive_dict_merge, key
                            else:
                                ret[k] = tmp[i].pop(k)
                        del tmp[i]
                if len(tmp) > 0 and len(mo.group(2)) > 0:
                    if merge and mo.group(2) in ret:
                        tmp = deepmerge([ret.pop(mo.group(2)), tmp], dedup, merge, key)
                    if len(tmp) == 1:
                        ret[mo.group(2)] = tmp[0]
                    else:
                        ret[mo.group(2)] = tmp

    return ret


def promotable(mydata):
    if isinstance(mydata, list):
        for item in mydata:
            if isinstance(item, dict) and len(item) != 1:
                return False


def logiclist(mylist, level=0, in_key=''):
    ret = []
    ifcount = 0
    if_state = 'looking'   # also 'found', 'clearing'
    for item in mylist:
        dbg(u"{}logiclist({}): {} top of list item:'{}' if_state:{}".format((' '*level), lineno(), level, item, if_state))
        if isinstance(item, list):
            val = logiclist(item, level+1)
            dbg(u"{}logiclist({}): {} logiclist returned val:'{}'".format((' '*level), lineno(), level, val))
            ret.append(val)
            if_state = 'looking'
            dbg(u"{}logiclist({}): {} if_state(looking)".format((' '*level), lineno(), level))
        elif isinstance(item, dict):
            if_kw = ''
            # 'if', 'elif', 'else' are special. Other list elements can pass just fine, but
            # if we're looking at a dict with one key and it's one of these, then we've got work to do.
            if len(item) == 1 and list(item.keys())[0] in ['if', 'elif', 'else']:
                if_kw = list(item.keys())[0]
                dbg(u"{}logiclist({}): {} found if_kw:'{}'".format((' '*level), lineno(), level, if_kw))
            val = logicdict(item, level+1)
            dbg(u"{}logiclist({}): {} logicdict returned val:{} if_state:{} if_kw:{}".format((' '*level), lineno(), level, val, if_state, if_kw))
            if if_kw in ['if', 'elif'] and not (isinstance(val, list) and len(val) > 1 and isinstance(val[0], bool)):
                raise AnsibleError("'{}' expects list of a boolean followed by value(s); instead found '{}'.".format(if_kw, val))
            if if_state == 'looking':
                if if_kw == 'if':
                    if_state = 'found'
                    ifcount += 1
                    if val.pop(0):
                        while len(val) > 0:
                            ret.append(val.pop(0))
                        if_state = 'clearing'
                    dbg(u"{}logiclist({}): {} if_state(if:looking->clearing) val:{}".format((' '*level), lineno(), level, val))
                elif if_kw == 'elif' or if_kw == 'else':
                    raise AnsibleError("Found '{}' before 'if'.".format(if_kw))
                else:
                    ret.append(val)
                    dbg(u"{}logiclist({}): {} if_state:{} if_kw:{})".format((' '*level), lineno(), level, if_state, if_kw))
            elif if_state == 'found':
                if if_kw == 'if':
                    if val.pop(0):
                        while len(val) > 0:
                            ret.append(val.pop(0))
                        if_state = 'clearing'
                    dbg(u"{}logiclist({}): {} if_state(if:found->clearing) val:{}".format((' '*level), lineno(), level, val))
                elif if_kw == 'elif':
                    if val.pop(0):
                        while len(val) > 0:
                            ret.append(val.pop(0))
                        if_state = 'clearing'
                    dbg(u"{}logiclist({}): {} if_state(elif:found->clearing) val:{}".format((' '*level), lineno(), level, val))
                elif if_kw == 'else':
                    if isinstance(val, list):
                        while len(val) > 0:
                            ret.append(val.pop(0))
                    else:
                        ret.append(val)
                    if_state = 'looking'
                    dbg(u"{}logiclist({}): {} if_state(else:found->looking) val:{}".format((' '*level), lineno(), level, val))
                else:
                    ret.append(val)
                    if_state = 'looking'
                    dbg(u"{}logiclist({}): {} if_state({}:found->looking) val:{}".format((' '*level), lineno(), level, if_kw, val))
            elif if_state == 'clearing':
                if if_kw == 'if':
                    if val.pop(0):
                        while len(val) > 0:
                            ret.append(val.pop(0))
                        if_state = 'clearing'
                    else:
                        if_state = 'found'
                    dbg(u"{}logiclist({}): {} if_state({}:clearing->{})".format((' '*level), lineno(), level, if_kw, if_state))
                elif if_kw == 'elif':
                    if_state = 'clearing'
                    dbg(u"{}logiclist({}): {} if_state({}:clearing->{}) val:{}".format((' '*level), lineno(), level, if_kw, if_state, val))
                elif if_kw == 'else':
                    if_state = 'looking'
                    dbg(u"{}logiclist({}): {} if_state({}:clearing->{}) val:{}".format((' '*level), lineno(), level, if_kw, if_state, val))
                else:
                    ret.append(val)
                    if_state = 'looking'
                    dbg(u"{}logiclist({}): {} if_state({}:clearing->{})".format((' '*level), lineno(), level, if_kw, if_state))
            else:
                dbg(u"{}logiclist({}): {} THIS SHOULDN'T HAPPEN if_state{}, if_kw{}".format((' '*level), lineno(), level, if_state, if_kw))
                ret.append(val)
                if_state == 'looking'
                dbg(u"{}logiclist({}): {} if_state(clearing->looking)".format((' '*level), lineno(), level))
        else:
            ret.append(item)
            if_state = 'looking'
            dbg(u"{}logiclist({}): {} if_state(looking)".format((' '*level), lineno(), level))
        dbg(u"{}logiclist({}): {} bottom of list, ret:{}".format((' '*level), lineno(), level, ret))
    return ret


def logicand(item, level):
    dbg(u"{}_logicand({}): {} initial item:{}".format((' '*level), lineno(), level, item))
    if isinstance(item, list):
        ret = logiclist(item, level+1)
    elif isinstance(item, dict):
        ret = logicdict(item, level+1)
    else:
        ret = [item]
    net = True
    dbg(u"{}_logicand({}): {} checking ret:{}".format((' '*level), lineno(), level, ret))
    for i in ret:
        if isinstance(i, list):
            i = logicand(i, level+1)
        if not isinstance(i, bool):
            raise AnsibleError("Values for 'and' must be boolean; found {}.".format(type_or_str(i)))
        if not i:
            net = False
    dbg(u"{}_logicand({}): {} final item:{}".format((' '*level), lineno(), level, net))
    return net


def logicor(item, level):
    dbg(u"{}__logicor({}): {} initial item:{}".format((' '*level), lineno(), level, item))
    if isinstance(item, list):
        ret = logiclist(item, level+1)
    elif isinstance(item, dict):
        ret = logicdict(item, level+1)
    else:
        ret = [item]
    net = False
    dbg(u"{}__logicor({}): {} checking ret:{}".format((' '*level), lineno(), level, ret))
    for i in ret:
        if isinstance(i, list):
            i = logicor(i, level+1)
        if not isinstance(i, bool):
            raise AnsibleError("Values for 'or' must be boolean; found {}.".format(type_or_str(i)))
        if i:
            net = True
    dbg(u"{}__logicor({}): {} final item:{}".format((' '*level), lineno(), level, net))
    return net


def logicxor(item, level):
    dbg(u"{}_logicxor({}): {} initial item:{}".format((' '*level), lineno(), level, item))
    if isinstance(item, list):
        ret = logiclist(item, level+1)
    elif isinstance(item, dict):
        ret = logicdict(item, level+1)
    else:
        ret = [item]
    net = 0
    dbg(u"{}_logicxor({}): {} checking ret:{}".format((' '*level), lineno(), level, ret))
    for i in ret:
        if isinstance(i, list):
            i = logicxor(i, level+1)
        if not isinstance(i, bool):
            raise AnsibleError("Values for 'xor' must be boolean; found {}.".format(type_or_str(i)))
        if i:
            net = net + 1
    dbg(u"{}_logicxor({}): {} final item:{}".format((' '*level), lineno(), level, (net == 1)))
    return net == 1


def logicnot(item, level):
    dbg(u"{}_logicnot({}): {} initial item:{}".format((' '*level), lineno(), level, item))
    if isinstance(item, list):
        ret = logiclist(item, level+1)
        ret = list(map(lambda i: logicnot(i, level+1), ret))  # logiclist(item, level+1)
        if len(ret) == 1:
            ret = ret[0]
    elif isinstance(item, dict):
        ret = logicdict(item, level+1)
        ret = {k: logicnot(v, level+1) for k, v in ret.items()}
    else:
        ret = item
        dbg(u"{}_logicnot({}): {} checking ret:{}".format((' '*level), lineno(), level, ret))
        if isinstance(ret, bool):
            # raise AnsibleError("Values for 'not' must be boolean; found {}.".format(type_or_str(i)))
            ret = not ret  # net.append(not i)
    dbg(u"{}_logicnot({}): {} final item:{}".format((' '*level), lineno(), level, ret))
    return ret


def logicif(item, level, in_key):
    if isinstance(item, list):
        ret = logiclist(item, level+1)
        dbg(u"{}__logicif({}): {} logiclist returned {}".format((' '*level), lineno(), level, ret))
    elif isinstance(item, dict):
        ret = logicdict(item, level+1)
        dbg(u"{}__logicif({}): {} logicdict returned {}".format((' '*level), lineno(), level, ret))
    else:
        ret = item
    dbg(u"{}__logicif({}): {} ret:{}, in_key:{}".format((' '*level), lineno(), level, ret, in_key))
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
        raise AnsibleError(
            "While handling '{}': Don't know how to merge variables of type: {}".format(master_key, type(merge_vals[0]))
        )
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
        return {'logical': logical}
