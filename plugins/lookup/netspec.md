
# NETSPEC Lookup Plugin

Our Ansible configuration contains many bare IP addresses, often
with little or no explanation of what those addresses refer to. The
netspec filter intends to address that issue by allowing names in
place of bare IP addresses in our YAML data, and thereby bringing
clarity to the humans who have to maintain it.

The "atom" of netspec data is a two-item dict containing:

    ip — one or more IP addresses, specified as any combination of:
        plain IPv4 or IPv6 addresses
        CIDRs
        Ansible host group names
        DNS resolvable names
        other Ansible variables containing netspecs.
    comment  — an optional comment.

These atoms can be joined in lists, combined with others, and
ultimately rendered through templates or as data to be input into
other parts of your Ansible workflow.

## Example 1

Consider the following pair of Ansible data definitions. The top
one is concise and easy to read, but the list of IP addresses means
nothing to someone tasked with maintaining it. The second one
defines exactly the same data, but the IP addresses are derived
from the corresponding host names through DNS using the netspec
lookup filter.

    iptable_rules_xkcd_tst_kerberos:
      - name: allow_kerberos-ports
        sources: ['181.17.48.47', '181.17.48.48', '181.17.48.15', '181.17.48.42',
                  '181.17.48.25', '181.17.48.36', '181.17.48.9',  '181.17.48.77', '181.17.48.78']
        protocols: ['tcp', 'udp']
        ports: ['88', '464', '749', '2121']
        action: ACCEPT

    new_tst_kerberos:
      - name: allow_kerberos-ports
        sources: "{{ lookup('netspec',
                              'xkdkrb0t.some.foo.net',
                              'xkdkrb1t.some.foo.net',
                              'xkdtools-test.its.unc.edu',
                              'xkddm0t.some.foo.net',
                              'xkddm1t.some.foo.net',
                              'xkdprov0t.some.foo.net',
                              'xkdprov1t.some.foo.net',
                              'yleapp0t.some.foo.net',
                              'yleapp1t.some.foo.net') }}"
        protocols: ['tcp', 'udp']
        ports: ['88', '464', '749', '2121']
        action: ACCEPT


## Example 2

Here's another real world example.

     # Example 2.a.
     custom_arguments: "<Location /balancer-manager>\n
        SetHandler balancer-manager\n
        Require ip ::1 127.0.0.1 10.0.250.96/28 181.17.47.18 181.17.45.8 181.17.45.3 181.17.130.192/26\n
       </Location>"

The snippet of Apache httpd configuration in Example 2.a. contains
both IP addresses and CIDRs with no indication of what any of them
refer to. Let's define another piece of Ansible data just for the
network and host addresses.

    # Example 2.b.
    raw: "{{ lookup('netspec',  {'ip': ['::1', '127.0.0.1'],   'comment': 'localhost' },
                                {'ip': '10.0.250.96/28',       'comment': 'Citrix proxies'},
                                       'toolsin.some.foo.net',
                                {'ip': '181.17.45.8',          'comment': 'Probably BAD; not in DNS'},
                                       'xkdbukld1.some.foo.net',
                                {'ip': '181.17.130.192/26',    'comment': 'XKD-Pub-VPN'},
                     fmt='raw', debug=False ) }}"

Here in Example 2.b. at last we see the individual "atoms" — the
fundamental building blocks of netspec data — as they are defined.
The 'localhost' part contains both and IPv6 and an IPv4 address.
Two others contain a simple host name so a bare string suffices;
the netspec filter will create appropriate atoms from them using
DNS. Two others contain CIDRs rather than host addresses, but with
their accompanying comment fields we at least get a hint what they
represent. Finally there's one address for a host which no longer
exists! That's unlikely to be spotted in Example 2.a., but it jumps
up and down and waves a red shirt at the maintainer of Example 2.b.

Note that we've also specified fmt='raw' for this netspec
invocation. The default format is 'ips' which is a simple,
uniquified list of addresses that doesn't preserve the comments.
We've chosen 'raw' for illustrative purposes below.

We've also specified debug=False which is the default, but just so
you know, there is a lot of debugging output generated if you set
debug=True and you run with at least verbosity level two ( -vv ).

Rendering the "raw" data defined above with Ansible's debug module
produces the following output:

    # Example 2.c.
    ok: [localhost] => 
      msg:
      - comment: localhost
        ip:
        - ::1
        - 127.0.0.1
      - comment: Citrix proxies
        ip:
        - 10.0.250.96/28
      - comment: toolsin.some.foo.net
        ip:
        - 181.17.47.18
      - comment: Probably BAD; not in DNS
        ip:
        - 181.17.45.8
      - comment: xkdbukld1.some.foo.net
        ip:
        - 181.17.45.3
      - comment: XKD-Pub-VPN
        ip:
        - 181.17.130.192/26

It's possible to feed the raw output of netspec back through
netspec in order to, for example, combine it with more data, or to
reformat into the default 'ips' format which contains only a flat
list of unique addresses and CIDRs. In fact, let's do that next:

    # Example 2.d.
    [...]
           custom_arguments: "<Location /balancer-manager>\n
              SetHandler balancer-manager\n
              Require ip {{ lookup('netspec', raw, fmt='ips') | join(' ') }}\n
             </Location>"
      tasks:
      - name: Show the 'netspec' lookup-ified data
        debug:
          msg: "{{ custom_arguments }}"

    *** Output: *********************************************************
      msg:
      - custom_arguments: |-
          <Location /balancer-manager>
           SetHandler balancer-manager
           Require ip ::1 127.0.0.1 10.0.250.96/28 181.17.47.18 181.17.45.8 181.17.45.3 181.17.130.192/26
           </Location>

Note that this produces essentially the same contents as our
original data definition in Example 2.a.

Note also that specifying fmt='ips' in Example 2.d. line 4 is
unnecessary as that's the default, but we wanted to be clear that
the data being filtered is called "raw", and is not to be confused
with fmt="raw".

### Example 3

Finally, we want to show an example that uses Ansible host groups.
We have a couple of host groups with names like kd_numpi_dev  and
kd_c3po_dev_app. Let's use them.

    ---
    # Example 3.
    - hosts: localhost
      serial: 1
      gather_facts: false
      vars:
        specs:
          - kd_numpi_dev         # an inventory hostgroup
          - kd_c3po_dev_app      # another one
          - toolsin.some.foo.net # host from DNS
        addresses: "{{ lookup('netspec', specs, xkdbukld1.some.foo.net,
                         fmt='raw', debug=False ) }}"
      tasks:
      - name: Show the 'raw' version
        debug:
          msg: "{{ addresses }}"

      - name: Show the 'ips' version
        debug:
          msg: "{{ lookup('netspec', addresses) }}"

And here's a run:

    TASK [Show the 'raw' version] ***************************************************
    ok: [localhost] => 
      msg:
      - comment: kd_numpi_dev
        ip:
        - 181.12.207.200
        - 181.12.207.205
        - 181.12.207.210
        - 181.12.207.211
      - comment: kd_c3po_dev_app
        ip:
        - 181.17.46.5
        - 181.17.46.13
        - 181.17.46.31
        - 181.17.46.27
        - 10.0.209.136
        - 10.0.209.140
      - comment: toolsin.some.foo.net
        ip:
        - 181.17.47.18
      - comment: xkdbukld1.some.foo.net
        ip:
        - 181.17.45.3

    TASK [Show the 'ips' version] ***********************************************
    ok: [localhost] => 
      msg:
      - 181.12.207.200
      - 181.12.207.205
      - 181.12.207.210
      - 181.12.207.211
      - 181.17.46.5
      - 181.17.46.13
      - 181.17.46.31
      - 181.17.46.27
      - 10.0.209.136
      - 10.0.209.140
      - 181.17.47.18
      - 181.17.45.3
