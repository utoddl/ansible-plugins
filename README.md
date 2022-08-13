# Overview

This repo contains plugins I've developed for use at work, but they are mine.

    plugins
    ├── filter
    │   ├── allow2te.py
    │   ├── logical.py
    │   └── polymac.py
    ├── lookup
    │   ├── mergevars.py
    │   ├── netspec.py
    │   └── yumpkggrouper.py
    └── README.md

Insufficently detailed documentation can be found in each plugin's source file. A brief
description for some of them follows. I really need to flesh out some better examples.

## Filter Plugins
https://docs.ansible.com/ansible/latest/plugins/filter.html

Filter plugins manipulate data. With the right filter you can extract a particular value, transform
data types and formats, perform mathematical calculations, split and concatenate strings, insert
dates and times, and do much more. Ansible uses the standard filters shipped with Jinja2 and adds
some specialized filter plugins.

### plugins/filter/logical.py
`logical` evaluates `if`, `elif`, `else`, `and`, `or`, and `not` operators in
Ansible data structures.

### plugins/filter/polymac.py
`polymac` adds a powerful macro expansion capability to Ansible data structures.
This promotes the DRY (Don't Repeat Yourself -- opps, I just did) principle, in that it
enables specification of multiple similar data by stating what they have in common once, and
isolating how they differ.

## Lookup Plugins
https://docs.ansible.com/ansible/latest/plugins/lookup.html

Lookup plugins are an Ansible-specific extension to the Jinja2 templating language. You can use
lookup plugins to access data from outside sources (files, databases, key/value stores, APIs, and
other services) within your playbooks. Like all templating, lookups execute and are evaluated on
the Ansible control machine. Ansible makes the data returned by a lookup plugin available using the
standard templating system. You can use lookup plugins to load variables or templates with
information from external sources.

### plugins/lookup/mergevars.py
`mergevars` provides a means to merge variables by name, explicitly and by matching regex.

### plugins/lookup/netspec.py
`netspec` helps you avoid accumulation of bare IP addresses and CIDRs in your Ansible
configs by providing a framework for annotating, merging, and rendering IPs and CIDRs.

### plugins/lookup/yumpkggrouper.py
`yumpkggrouper` takes package specifications and groups them by their common parameters.
This allows you to make fewer but more productive calls to the package management module.
