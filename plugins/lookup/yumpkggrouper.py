from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# import os
# import re
import copy
# from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
# from ansible.utils.vars import merge_hash
# from ansible.module_utils.six.moves import reduce
# from ansible.plugins.filter.core import combine
from ansible.module_utils.six import string_types

# from ansible.module_utils._text import to_bytes, to_text
# from ansible.template import generate_ansible_template_vars


DOCUMENTATION = """
    lookup: yumpkggrouper
    author: Todd Lewis <todd_lewis@unc.edu>
    version_added: "2.7.10"
    short_description: group lists of pkgs by their attributes
    description:
      - A list of package names or dicts of package with yum parameters
        are grouped by common attributes and returned as a list of items
        to be processed by the yum or dnf modules. The object is to reduce
        the number of times yum must be called.
    options:
      _terms:
        description:
          - list of strings and/or dicts to be grouped.
        required: true
      defs:
        description: dict containing default attributes for calling yum.
        required: true
"""

EXAMPLES = """
- name: show grouped packages
  vars:
    mw_linux_packages_all:
      - pkg1
      - pkg2
      - name: pkg3
        state: state3
        autoremove: yes
      - name: ['not_me', 'not_this_one', 'this_one_neither']
        state: absent
    mw_linux_packages_install_os:
      - pkgio4
      - name: pgkio5
        state: latest
      - pkgio6
    pkglist: "{{ mw_linux_packages_all + mw_linux_packages_install_os }}"
    ypg_defaults:
      state: present
      autoremove: None
  debug:
    msg="{{ lookup('yumpkggrouper', defs=ypg_defaults, pkglist) }}"
"""

RETURN = """
_raw:
   description: list packages grouped by common attributes
"""

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):

        defs = kwargs.get('defs', {})
        pkgs = {}
        for term in terms:
            for key in term:
                pkg = copy.deepcopy(defs)
                if isinstance(key, string_types):
                    pkg['name'] = key
                elif isinstance(key, dict) and key.get('name', ''):
                    for name, val in key.items():
                        pkg[name] = val
                else:
                    display.error(u"Skipping bad pkg: {}".format(key))
                    continue
                # Here's the weird bit: we're going to temporarily remove
                # the name, and stringify the rest of pkg to get a grouping key
                name = pkg.pop('name', 'MISSING')
                grpkey = u"{}".format(pkg)
                # Another gotchya: if name is a list, we want to split it out
                # into multiple entries.
                if not isinstance(name, list):
                    name = [name]
                for singlename in name:
                    if grpkey not in pkgs:
                        pkg['name'] = [singlename]
                        pkgs[grpkey] = copy.deepcopy(pkg)
                    else:
                        pkgs[grpkey]['name'].append(singlename)
        grps = []
        for val in pkgs.values():
            grps.append(val)
        return [grps]
