#!/usr/bin/env python

import sys
import json
from xml.etree import ElementTree as ET

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
        def process(parent, node):
            for child in node.children:
                el = ET.SubElement(parent, 'outline', text=child.text)
                process(el, child)

        root = ET.Element('opml', version='2.0')
        head = ET.SubElement(root, 'head')
        body = ET.SubElement(root, 'body')

        for summit in self.nodes.pop(0):
            el = ET.SubElement(body, 'outline', text=summit.text)
            process(el, summit)

        content = ET.ElementTree(root)
        content.write(
            open(output, 'wb') if output else sys.stdout,
            encoding = 'UTF-8',
            xml_declaration = True,
        )

    def extract(self, contents):
        ret = []
        for obj in contents:
            if obj.get('t') == 'Str':
                ret.append(obj.get('c'))
            elif obj.get('t') == 'Space':
                ret.append(' ')
        return ''.join(ret)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    args = parser.parse_args()

    p = PandocOPML()
    p.write(args.output)
