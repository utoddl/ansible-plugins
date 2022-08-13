from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
import re
import inspect

from ansible.errors import AnsibleError
# from ansible.plugins.lookup import LookupBase
# from ansible.utils.vars import merge_hash
# from ansible.module_utils.six.moves import reduce
# from ansible.plugins.filter.core import combine
# from ansible.plugins.filter.core import flatten
from ansible.module_utils.six import string_types

# from ansible.module_utils._text import to_bytes, to_text
# from ansible.template import generate_ansible_template_vars


DOCUMENTATION = """
    lookup: allow2te
    author: Todd Lewis <todd_lewis@unc.edu>
    version_added: "2.7.10"
    short_description: create .te file contents from allow rules.
    description:
      - Turns a list of allow rules into a .te stream with the allow
        rules deduped and canonicalized.
    options:
      _terms:
        description:
          - list of allow rules
        required: true
      te_name:
        description: The expected filename for this set of allow rules.
          The path and '.te' extension are optional.
        required: true
      te_version:
        description: Version number, defaults to "1.0"
        required: false
"""

EXAMPLES = """
- name: show evaluated variable
  debug: msg="{{ allow_list | allow2te(te_name='/tmp/my_allows.te' }}"
"""

RETURN = """
_raw:
   description: contents of a .te file
"""

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

re_grouping = re.compile("^([^{]*){([^}]*)}(.*)")
re_allowprime = re.compile("^\s*(allow)\s+([^\s]+)\s+([^\s:]+)\s*:\s*([^\s]+)\s*([^\s;]+)\s*;?\s*$")
#                           ($allow, $src_t, $tgt_t, $tgt_c, $action) = ($1, $2, $3, $4, $5);

show_debug_messages = False
allows = {}
src_types = []
tgt_types = []
tgt_classes = {}


def dbg(msg):
    if show_debug_messages:
        display.vv(msg)


def allow2te(rules, te_name, te_version='1.0', debug=False):
    if not isinstance(rules, list):
        raise AnsibleError("allow2te expects a list; got {} instead.".format(type_or_str(rules)))
    global show_debug_messages
    show_debug_messages = debug
    te_name_path, te_name_file = os.path.split(te_name)
    te_name_stem = os.path.splitext(te_name_file)[0]
    dbg(u"allow2te({}): looking at {} rules.".format(lineno(), len(rules)))
    degroup(rules)
    dbg(u"allow2te({}): allows (sorted and degrouped): {}".format(lineno(), allows))
    te_stream = []
    te_stream.extend(["", "module " + te_name_stem + " " + te_version + ";", "", "require {"])
    for type_t in sorted(list(set(src_types + tgt_types))):
        if type_t != "self":
            dbg(u"allow2te({}): declaring type {}".format(lineno(), type_t))
            te_stream.append("  type " + type_t + ";")
    for tgt_class in sorted(list(tgt_classes)):
        dbg(u"allow2te({}): declaring class {}".format(lineno(), tgt_class))
        te_stream.append("  class {} {};".format(tgt_class, regroup(tgt_classes[tgt_class])))
    te_stream.extend(["}"])
    for src_type in sorted(list(allows)):
        dbg(u"allow2te({}): allow block for src_type {}".format(lineno(), src_type))
        te_stream.extend(["", "#============= " + src_type + " ============="])
        for tgt_type in sorted(list(allows[src_type])):
            dbg(u"allow2te({}): block for {} {}".format(lineno(), src_type, tgt_type))
            for tgt_class in sorted(list(allows[src_type][tgt_type])):
                dbg(u"allow2te({}): block for {} {} {}".format(lineno(), src_type, tgt_type, tgt_class))
                te_stream.append(" ".join(["allow", src_type, tgt_type + ':' + tgt_class, regroup(allows[src_type][tgt_type][tgt_class])]) + ";")
    return "\n".join(te_stream)


def lineno():
    """Returns the line number lineno() was called from."""
    return inspect.currentframe().f_back.f_lineno


def regularize(rule):
    mo = re_allowprime.match(rule)
    dbg(u"regularize({}): '{}'".format(lineno(), rule))
    if mo:
        allow_kw = mo.group(1)
        src_t = mo.group(2)
        tgt_t = mo.group(3)
        tgt_c = mo.group(4)
        action = mo.group(5)
        dbg(u"regularize({}): allow_kw:'{}' src_t:'{}' tgt_t:'{}' tgt_c:'{}' action:'{}'".format(lineno(), allow_kw, src_t, tgt_t, tgt_c, action))
        if src_t not in src_types:
            src_types.append(src_t)
            dbg(u"regularize({}): appending '{}' to src_types array".format(lineno(), src_t))
        if tgt_t not in tgt_types:
            tgt_types.append(tgt_t)
            dbg(u"regularize({}): appending '{}' to tgt_types array".format(lineno(), tgt_t))
        if tgt_c not in tgt_classes:
            tgt_classes[tgt_c] = []
            dbg(u"regularize({}): adding empty list at tgt_classes['{}']".format(lineno(), tgt_c))
        if action not in tgt_classes[tgt_c]:
            dbg(u"regularize({}): appending '{}' to tgt_classes['{}']".format(lineno(), action, tgt_c))
            tgt_classes[tgt_c].append(action)
        if src_t not in allows:
            dbg(u"regularize({}): adding empty dict at allows['{}']".format(lineno(), src_t))
            allows[src_t] = {}
        if tgt_t not in allows[src_t]:
            dbg(u"regularize({}): adding empty dict at allows['{}']['{}']".format(lineno(), src_t, tgt_t))
            allows[src_t][tgt_t] = {}
        if tgt_c not in allows[src_t][tgt_t]:
            dbg(u"regularize({}): adding empty list at allows['{}']['{}']['{}']".format(lineno(), src_t, tgt_t, tgt_c))
            allows[src_t][tgt_t][tgt_c] = []
        if action not in allows[src_t][tgt_t][tgt_c]:
            dbg(u"regularize({}): appending {} to allows['{}']['{}']['{}']".format(lineno(), action, src_t, tgt_t, tgt_c))
            allows[src_t][tgt_t][tgt_c].append(action)
        return allow_kw + " " + src_t + " " + tgt_t + ":" + tgt_c + " " + action + ";"
    dbg(u"regularize({}): mo didn't match: ".format(lineno(), rule))
    return None


def regroup(lst):
    if len(lst) > 1:
        return "{ " + " ".join(sorted(lst)) + " }"
    else:
        return lst[0]


def degroup(rules):
    outrules = []
    while (len(rules) > 0):
        inrule = rules.pop(0)
        dbg(u"degroup({}): '{}'".format(lineno(), inrule))
        mo = re_grouping.match(inrule)
        if mo:
            for insideitem in mo.group(2).split():
                dbg(u"degroup({}): insideitem:'{}'".format(lineno(), insideitem))
                rules.append(mo.group(1) + ' ' + insideitem + ' ' + mo.group(3))
        else:
            regularized = regularize(inrule)
            if regularized:
                outrules.append(regularized)
    return outrules


def type_or_str(term):
    if isinstance(term, string_types):
        return term
    else:
        return type(term)


class FilterModule(object):
    def filters(self):
        return {'allow2te': allow2te}
