#!/usr/bin/env python

import sys
import json

class Node(object):
    def __init__(self, text):
        self.text = text
        self.children = []

    def append(self, node):
        self.children.append(node)

class PandocOPML(object):
    def __init__(self):
        self.head, self.body = json.loads(sys.stdin.read())
        self.nodes = self.parse()

    def parse(self):
        nodes = []

        def inner(content, depth = 0):
            for obj in content:
                if obj.get('t') == 'BulletList':
                    for element in obj.get('c'):
                        inner(element, depth + 1)
                elif obj.get('t') == 'Plain':
                    node = Node(self.extract(obj.get('c')))

                    try:
                        nodes[depth - 1].append(node)
                    except IndexError:
                        nodes.append([node])

                    if (depth - 1) > 0:
                        # minus 2 to make it zero-indexed and then get the parent
                        parent = nodes[depth - 2][-1]
                        parent.append(node)

        inner(self.body)

        return nodes

    def write(self, output):
        output = open(output, 'w') if output else sys.stdout

        def process(node, depth = 1):
            for child in node.children:
                output.write((' ' * depth * 2) + child.text + '\n')
                process(child, depth + 1)

        for summit in self.nodes.pop(0):
            output.write(summit.text + '\n')
            process(summit)

        output.flush()

    def extract(self, contents):
        ret = []
        for obj in contents:
            if obj.get('t') == 'Str':
                ret.append(self.escape(obj.get('c')))
            elif obj.get('t') == 'Space':
                ret.append(' ')
            else:
                ret.append('!!!')
        return ''.join(ret)

    def escape(self, s):
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

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    args = parser.parse_args()

    p = PandocOPML()
    p.write(args.output)
