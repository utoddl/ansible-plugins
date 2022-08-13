from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# import os
import re

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
# from ansible.utils.vars import merge_hash
# from ansible.module_utils.six.moves import reduce
# from ansible.plugins.filter.core import combine
from ansible.plugins.filter.core import flatten
from ansible.module_utils.six import string_types

# from ansible.module_utils._text import to_bytes, to_text
# from ansible.template import generate_ansible_template_vars


DOCUMENTATION = """
    lookup: mergevars
    author: Todd Lewis <todd_lewis@unc.edu>
    version_added: "2.7.10"
    short_description: merge variables matching list, regex
    description:
      - Listed variables and/or those matching the supplied regex will be
        deep-merged and returned. Scalar variables (int and str) are treated
        like single element lists. All variables must be either lists or dicts;
        you can't mix them. Order is preserved for explicitly listed variables.
        Variables matching var_regex are sorted and come after explicit variables.
    options:
      _terms:
        description:
          - list of variables to merge. These can be names of variables ("'foo'"), or
            expressions ("foo[3]").
        required: false
      regex:
        description: regular expression matching names of variables to merge
        required: false
      dedup:
        discription: whether to deduplicate the resulting list
        default: true
        required: false
        type: boolean
      recursive:
        description: a boolean to indicate whether to recursively merge dictionaries
        default: true
        required: false
        type: boolean
"""

EXAMPLES = """
- name: show merged variables
  debug: msg="{{ lookup('mergevars', regex='^merge_these_.*') }}

- name: show merged variables
  debug: msg="{{ lookup('mergevars', 'ansible_fqdn', 'ansible_mounts', regex='^merge_these_.*') }}

"""

RETURN = """
_raw:
   description: list of merged variables
"""

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):

        varpat = kwargs.get('regex', '')
        dedup = kwargs.get('dedup', True)
        recursive_dict_merge = kwargs.get('recursive', True)
        keys = []
        for key in terms:
            if not isinstance(key, string_types):
                keys.append(key)
            elif key not in keys and key in variables.keys():
                keys.append(key)

        if len(varpat) > 0:
            for key in sorted(variables.keys()):
                if key not in keys and re.match(varpat, key):
                    keys.append(key)

        display.v("Merging vars in this order: {}".format(list(map(type_or_str, keys))))

        # We need to render any jinja in the merged var now, because once it
        # leaves this plugin, ansible will cleanse it by turning any jinja tags
        # into comments.
        # And we need it done before merging the variables,
        # in case any structured data is specified with templates.
        merge_vals = []
        for key in keys:
            if isinstance(key, string_types):
                val = self._templar.template(variables[key])
            else:
                val = self._templar.template(key)
            if isinstance(val, int) or isinstance(val, str):
                merge_vals.append([val])
            else:
                merge_vals.append(val)

        # Dispatch based on type that we're merging
        if len(merge_vals) == 0:
            merged = []
        elif isinstance(merge_vals[0], list):
            merged = merge_list(merge_vals, dedup, recursive_dict_merge)
        elif isinstance(merge_vals[0], dict):
            merged = merge_dict(merge_vals, dedup, recursive_dict_merge)
        else:
            raise AnsibleError(
                "Don't know how to merge variables of type: {}".format(type(merge_vals[0]))
            )

        return [merged]


def type_or_str(term):
    if isinstance(term, string_types):
        return term
    else:
        return type(term)


def merge_dict(merge_vals, dedup, recursive_dict_merge):
    """
    To merge dicts, just update one with the values of the next, etc.
    """
    check_type(merge_vals, dict)
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


def merge_list(merge_vals, dedup, recursive_dict_merge):
    """ To merge lists, just concat them. Dedup if wanted. """
    check_type(merge_vals, list)
    flatten_levels = 0
    if recursive_dict_merge:
        flatten_levels = 999
    merged = flatten(merge_vals, flatten_levels)
    if dedup:
        merged = deduplicate(merged)
    return merged


def check_type(mylist, _type):
    """ Ensure that all members of mylist are of type _type. """
    if not all([isinstance(item, _type) for item in mylist]):
        raise AnsibleError("All values to merge must be of the same type, either dict or list")


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
