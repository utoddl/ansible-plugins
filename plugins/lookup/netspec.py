# -*- coding: utf-8 -*-
# Copyright 2021 Todd M. Lewis
# GNU General Public License v3.0+
# (see https://www.gnu.org/licenses/gpl-3.0.txt)

"""
# An Ansible lookup plugin for taking host and network addresses up a level.
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleError

from ansible_collections.ansible.utils.plugins.plugin_utils.base.ipaddr_utils import ipaddr

from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.plugins.filter.core import flatten
from ansible.module_utils.six import string_types
import socket
import inspect

try:
    import netaddr
    HAS_NETADDR = True
except ImportError:
    HAS_NETADDR = False

DOCUMENTATION = """
    name: netspec
    author: Todd Lewis <todd_lewis@unc.edu>
    version_added: "2.9"
    short_description: turn human readable network and host specifications into IP addresses.
    description:
      - >-
        Given a liberal set of optionally commented host, hostgroup, and IP
        specifications, produces a set of strings suitable for various types of
        config files.
    options:
      _terms:
        description:
          - |
            list of literal or implied IP specifications. These can be a mix of
            literal IP addresses, CIDRs, ansible hostgroup names, and host names,
            any of which may be specified as a string, the 'ip' field of a
            dict which may also contain a 'comment', or the name of a variable
            containing such a string or dict. If a dict is given which contains
            no 'comment', one is generated from the originating string.

            Literal IP addresses and CIDRs are left unchanged.

            Ansible hostgroup names are converted to lists of the groups' member host names.

            Finally, host names are replaced by the first available value from:
            - each host's IP address from DNS (gethostbyname()),
            - the optional dns dictionary.

            Failure to resolve a host name from one of the above sources
            constitutes a fatal error.
        required: true
      dns:
        description: alternative dict mapping strings to IP addresses when gethostbyname() fails.
        required: false
        type: dict
      fmt:
        description: |
          string indicating the desired format of the returned data.
          'ips' (the default) produces a list of IP addresses and/or CIDRs.
          'raw' produces a list of dicts, each of which contains two fields:
          'ip' which is either a list of IP addresses or CIDRs, and 'comment'.
          This is the form used internally by the plugin itself.
          'ranges' produces a list like that produced by 'ips' but with ranges
          as hyphen-delimited pairs of addresses rather than CIDRs.
          The lists produced by 'ips' and 'raw' can be fed back into the
          netspec filter for combining with additional data or to change
          the format. If the list produced by 'ranges' contains any hyphen joined
          pairs, then that list cannot be used by further netspec invocations.
        default: ips
        required: false
        type: string
        choices:
        - ips
        - ranges
        - raw

"""

EXAMPLES = r"""
- name: show net specs
  debug:
    msg:
      - "{{ lookup('netspec', 'host1.unc.edu', 'host2.unc.edu', fmt='ips') }}"
      - "{{ lookup('netspec', [{ip: host1_unc_edu, comment: 'big box'}, {ip: '8.8.4.4', comment: 'googleDNS'}]) }}"
      - "{{ lookup('netspec', 'hostgroup1', 'hostgroup2', '152.2.22.62', ['onyen0.isis.unc.edu', [ 'hostgroup4'] ]) }}"

  '11.22.33.44', '11.22.23.34'
  '11.22.33.44', '8.8.4.4'
  '1.1.1.1', '2.2.2.2', '2.2.2.3', '152.2.22.62', '152.19.209.8', '4.4.4.4'
"""

RETURN = """
_raw:
   description: array of strings in the requested format
"""


display = Display()

show_debug_messages = False


def dbg(msg):
    if show_debug_messages:
        display.vv(msg)


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


class LookupModule(LookupBase):
    def _do_term(self, term, level, variables):
        dbg(u"{}netspec:do_term[{}]: {} processing term '{}'".format((" " * level), lineno(), level, term))
        if isinstance(term, list):
            newret = self._do_list(flatten([term], 999), level + 1, variables)
            dbg(u"{}netspec:do_term[{}]: {} do_list returned '{}'".format((" " * level), lineno(), level, newret))
            return newret
        if isinstance(term, dict):
            newret = self._do_dict(term, level + 1, variables)
            dbg(u"{}netspec:do_term[{}]: {} do_dict returned '{}'".format((" " * level), lineno(), level, newret))
            return newret
        if isinstance(term, string_types):
            newret = self._do_string(term, level + 1, variables)
            dbg(u"{}netspec:do_term[{}]: {} do_string returned '{}'".format((" " * level), lineno(), level, newret))
            return newret
        raise AnsibleError("Don't know how to netspec variables of type <{}> {}".format(type(term), term))
        return None

    def _do_string(self, string0, level, variables):
        dbg(u"{}netspec:do_string[{}]: {} processing string '{}'".format((" " * level), lineno(), level, string0))
        string = self._templar.template(string0)
        if string != string0:
            dbg(u"{}netspec:do_string[{}]: {} templated '{}' into '{}'".format((" " * level), lineno(), level, string0, string))
        ret = {"ip": [], "comment": string}
        ip = ipaddr(string)
        dbg(u"{}netspec:do_string[{}]: {} ipaddr('{}') returned '{}'".format((" " * level), lineno(), level, string, ip))
        if ip:
            ret.pop("comment")
            dbg(u"{}netspec:do_string[{}]: {} string is an ipaddr '{}'".format((" " * level), lineno(), level, ip))
            if ip not in self._seen:
                dbg(u"{}netspec:do_string[{}]: {} first time seeing '{}'".format((" " * level), lineno(), level, ip))
                self._seen.append(ip)
            ret["ip"].append(ip)
            dbg(u"{}netspec:do_string[{}]: {} ret now '{}'".format((" " * level), lineno(), level, ret))
        elif string in variables["groups"]:
            dbg(u"{}netspec:do_string[{}]: {} string is a hostgroup name '{}'".format((" " * level), lineno(), level, string))
            newret = self._do_term({"ip": variables["groups"][string], "comment": string}, level + 1, variables)
            dbg(u"{}netspec:do_string[{}]: {} _do_term returned '{}'".format((" " * level), lineno(), level, newret))
            newret = flatten([newret], 999)
            dbg(u"{}netspec:do_string[{}]: {} which after flattening is '{}'".format((" " * level), lineno(), level, newret))
            dbg(u"{}netspec:do_string[{}]: {} returning '{}'".format((" " * level), lineno(), level, newret))
            return newret
        elif string in variables:
            dbg(u"{}netspec:do_string[{}]: {} string is a variable reference '{}'".format((" " * level), lineno(), level, string))
            val = self._templar.template(variables[string])
            dbg(u"{}netspec:do_string[{}]: {} templated variable is '{}'".format((" " * level), lineno(), level, val))
            newret = self._do_term(val, level + 1, variables)
            dbg(u"{}netspec:do_string[{}]: {} _do_term returned '{}'".format((" " * level), lineno(), level, newret))
            newret = flatten([newret], 999)
            dbg(u"{}netspec:do_string[{}]: {} which after flattening is '{}'".format((" " * level), lineno(), level, newret))
            dbg(u"{}netspec:do_string[{}]: {} returning '{}'".format((" " * level), lineno(), level, newret))
            return newret
        else:
            dbg(u"{}netspec:do_string[{}]: {} attempting DNS on '{}'".format((" " * level), lineno(), level, string))
            try:
                addr1 = socket.gethostbyname(string)
                dbg(u"{}netspec:do_string[{}]: {} resolved to '{}'".format((" " * level), lineno(), level, addr1))
                newret = self._do_term({"ip": addr1, "comment": string}, level + 1, variables)
                dbg(u"{}netspec:do_string[{}]: {} returning '{}'".format((" " * level), lineno(), level, newret))
                return newret
            except socket.gaierror:
                if string in self._dns:
                    if string in self._resolving_strings:
                        raise AnsibleError("Cannot resolve recursively defined value '{}'.".format(string))
                    self._resolving_strings.append(string)
                    newret = self._do_term({"ip": self._dns[string], "comment": string}, level + 1, variables)
                    self._resolving_strings.pop()
                    return newret
                raise AnsibleError("Could not resolve gethostbyname('{}')".format(string))
                pass
        return ret

    def _do_list(self, terms, level, variables):
        dbg(u"{}netspec:do_list[{}]: {} processing list '{}'".format((" " * level), lineno(), level, terms))
        ret = []
        for term in terms:
            dbg(u"{}netspec:do_list[{}]: {} processing term '{}'; ret is '{}'".format((" " * level), lineno(), level, term, ret))
            newterms = flatten([self._do_term(term, level + 1, variables)], 999)
            for newterm in newterms:
                ret.append(newterm)
            dbg(u"{}netspec:do_list[{}]: {} ret now '{}'".format((" " * level), lineno(), level, ret))
        return ret

    def _do_dict(self, term, level, variables):
        dbg(u"{}netspec:do_dict[{}]: {} processing dict '{}'".format((" " * level), lineno(), level, term))
        ret = {"ip": []}
        if "ip" in term:
            dbg(u"{}netspec:do_dict[{}]: {} processing dict 'ip' of '{}'".format((" " * level), lineno(), level, term["ip"]))
            resolved = flatten([self._do_term(flatten([term["ip"]], 999), level + 1, variables)], 999)
            dbg(u"{}netspec:do_dict[{}]: {} resolved to '{}'".format((" " * level), lineno(), level, resolved))
            for r in resolved:
                dbg(u"{}netspec:do_dict[{}]: {} r '{}'".format((" " * level), lineno(), level, r))
                if len(r["ip"]):
                    dbg(u"{}netspec:do_dict[{}]: {} appending r['ip'] to '{}'".format((" " * level), lineno(), level, ret["ip"]))
                    for rip in r["ip"]:
                        ret["ip"].append(rip)
                    dbg(u"{}netspec:do_dict[{}]: {} ret now '{}'".format((" " * level), lineno(), level, ret))
        if "comment" in term:
            ret["comment"] = term["comment"]
        ret["ip"] = [ip for ip in ret["ip"] if ip]
        return ret

    def run(self, terms, variables, **kwargs):
        """combine ip specs or display them different ways"""
        global show_debug_messages
        show_debug_messages = kwargs.get("debug", False)
        if not HAS_NETADDR:
            AnsibleError("The netspec lookup plugin requires python's netaddr be installed on the ansible controller")
        if not ipaddr('1.2.3.4'):
            AnsibleError("The ipaddr filter, used by the netspec lookup plugin, is not working")
        fmt = kwargs.get("fmt", "ips")
        if fmt not in ["ips", "ranges", "raw"]:
            AnsibleError("fmt must be one of ['ips', 'ranges', 'raw'], not '{}'.".format(fmt))
        self._dns = kwargs.get("dns", {})
        self._resolving_strings = []
        self._seen = []
        # A call could look like any of these:
        # The first phase is to normalize the arbitrarily nested terms into a flat array of dicts, thus:
        #   [ { 'ip': ['1.2.3.4'], 'comment': 'oneDotTwoDotThreeDotFour' },
        #     { 'ip': ['5.6.7.8/9', ['2.4.6.8'], 'comment': 'Network 5678 and host 2.4.6.8' }, ... ]
        # If an 'ip' looks like a network or IP address, use it as is.
        # If it's a key to groups, get all the hosts in the group, resolve their IPs, and use them all.
        # If it's resolves in DNS as an A or AAAA, use the IP.
        # If a 'dns' dict was supplied, and a key matches, used the value.
        # Otherwise, it's an error, so bomb out.

        # The second phase formats an array of strings, the format of which is determined by the fmt parameter.

        level = 0
        rz = []
        for term in terms:
            dbg(u"{}netspec[{}]: {} processing term '{}'".format((" " * level), lineno(), level, term))
            ret = flatten([self._do_term(term, level + 1, variables)], 999)
            dbg(u"{}netspec[{}]: {} processed term into '{}'".format((" " * level), lineno(), level, ret))
            for r in ret:
                if isinstance(r, dict):
                    if len(r["ip"]):
                        dbg(u"{}netspec[{}]: {} appending '{}' to '{}'".format((" " * level), lineno(), level, r, rz))
                        rz.append(r)
                    else:
                        dbg(u"{}netspec[{}]: {} ignoring empty dict '{}'".format((" " * level), lineno(), level, r))
                else:
                    raise AnsibleError("Expected type dict, found type <{}>: '{}'".format(type(ret), ret))
        if fmt == "raw":
            return [rz]
        elif fmt == "ranges":
            return [[ipaddr(ip, "range_usable") if ipaddr(ip, "type") == "network" else ip for ip in self._seen]]
        elif fmt == "ips":
            return [self._seen]
