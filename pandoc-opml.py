#!/usr/bin/env python

import sys
import json
import pprint

def escape(s):
    reps = [
        ('"', '&quot;'),
        ('&', '&amp;'),
        ("'", '&apos;'),
        ('<', '&lt;'),
        ('>', '&gt;'),
    ]
    for char, rep in reps:
        s = s.replace(char, rep)
    return s

def extract(contents):
    ret = []
    for obj in contents:
        if obj.get('t') == 'Str':
            ret.append(escape(obj.get('c')))
        elif obj.get('t') == 'Space':
            ret.append(' ')
        else:
            ret.append('!!!')
    return ''.join(ret)

class Node(object):
    def __init__(self, text):
        self.text = text
        self.children = []

    def append(self, node):
        self.children.append(node)

nodes = []

def build(nodes):
    def process(node, depth = 1):
        for child in node.children:
            print (' ' * depth * 2) + child.text
            process(child, depth + 1)

    for summit in nodes.pop(0):
        print summit.text
        process(summit)

def parse(content, depth = 0):
    for obj in content:
        if obj.get('t') == 'BulletList':
            for element in obj.get('c'):
                parse(element, depth + 1)
        elif obj.get('t') == 'Plain':
            node = Node(extract(obj.get('c')))

            try:
                nodes[depth - 1].append(node)
            except IndexError:
                nodes.append([node])

            if (depth - 1) > 0:
                # minus 2 to make it zero-indexed and then get the parent
                parent = nodes[depth - 2][-1]
                parent.append(node)

if __name__ == '__main__':
    head, body = json.loads(sys.stdin.read())
    parse(body)
    build(nodes)
