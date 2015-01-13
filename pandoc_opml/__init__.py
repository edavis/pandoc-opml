import sys
import json
import time
import itertools
import subprocess
from datetime import datetime
from xml.etree import ElementTree as ET

__version__ = '0.1'

def gmt(s=None):
    utc = time.gmtime(s)
    d = datetime(*utc[:6])
    return d.strftime('%a, %d %b %Y %H:%M:%S') + ' GMT'

class Node(object):
    def __init__(self, text, attr=None):
        self.text = text
        self.attr = attr or {}
        self.children = []

    def append(self, node):
        self.children.append(node)

class PandocOPML(object):
    def __init__(self, json_ast=None):
        if json_ast is None:
            self.head, self.body = json.loads(sys.stdin.read())
        else:
            self.head, self.body = json.loads(json_ast)
        self.head = self.head['unMeta']
        self.depth = 0
        self.el = None
        self.nodes = self.parse()

    def parse(self):
        nodes = []
        def inner(content):
            for obj in content:
                if obj.get('t') in {'Para', 'Plain'}:
                    node = Node(self.extract(obj.get('c')))

                    try:
                        nodes[self.depth].append(node)
                    except IndexError:
                        nodes.append([node])

                    if self.depth > 0:
                        parent = nodes[self.depth - 1][-1]
                        parent.append(node)

                    self.el = obj.get('t')

                elif obj.get('t') == 'OrderedList':
                    info, contents = obj.get('c')
                    counter = itertools.count(info[0])
                    if self.el in {'Header', 'Para'} or self.el is None:
                        for element in contents:
                            inner(element)
                            n = nodes[self.depth][-1] # most recently added node
                            c = next(counter)
                            n.attr.update({
                                'ordinal': str(c),
                                'list': 'ordered',
                            })
                    else:
                        self.depth += 1
                        for element in contents:
                            inner(element)
                            n = nodes[self.depth][-1]
                            c = next(counter)
                            n.attr.update({
                                'ordinal': str(c),
                                'list': 'ordered',
                            })
                        self.depth -= 1

                elif obj.get('t') == 'BulletList':
                    if self.el in {'Header', 'Para'} or self.el is None:
                        # Don't increase the depth when a BulletList
                        # follows a Header or Para object.
                        #
                        # If the last object was Header, it has
                        # already incremented the depth.
                        for element in obj.get('c'):
                            inner(element)
                            n = nodes[self.depth][-1]
                            n.attr['list'] = 'unordered'
                    else:
                        # But do increase the depth when a BulletList
                        # follows anything else.
                        #
                        # This makes nested BulletLists work.
                        self.depth += 1
                        for element in obj.get('c'):
                            inner(element)
                            n = nodes[self.depth][-1]
                            n.attr['list'] = 'unordered'
                        self.depth -= 1

                elif obj.get('t') == 'Header':
                    level, attr, content = obj.get('c')
                    outline_attr = self.extract_header_attributes(attr)
                    outline_attr['level'] = str(level)
                    node = Node(self.extract(content), outline_attr)
                    self.depth = level - 1

                    try:
                        nodes[self.depth].append(node)
                    except IndexError:
                        nodes.append([node])

                    if self.depth > 0:
                        parent = nodes[self.depth - 1][-1]
                        parent.append(node)

                    # the next elements are children of this header
                    self.depth += 1
                    self.el = 'Header'

        inner(self.body)
        return nodes

    def write(self, output):
        def process(parent, node):
            for child in node.children:
                params = {'text': child.text}
                params.update(child.attr)
                el = ET.SubElement(parent, 'outline', **params)
                process(el, child)

        root = ET.Element('opml', version='2.0')
        head = ET.SubElement(root, 'head')
        body = ET.SubElement(root, 'body')
        now = gmt()

        def header(key, value):
            ET.SubElement(head, key).text = value

        if 'title' in self.head:
            header('title', self.extract(self.head['title']['c']))

        if 'description' in self.head:
            header('description', self.extract(self.head['description']['c']))

        if 'author' in self.head:
            # Markdown returns a MetaList of MetaInlines while org-mode returns MetaInlines.
            authors = []
            if self.head['author'].get('t') == 'MetaList':
                for author in self.head['author']['c']:
                    authors.append(self.extract(author['c']))
            elif self.head['author'].get('t') == 'MetaInlines':
                authors = [self.extract(self.head['author']['c'])]
            header('ownerName', ', '.join(authors))

        if 'email' in self.head:
            header('ownerEmail', self.extract(self.head['email']['c']))

        if 'date' in self.head:
            header('dateCreated', self.extract(self.head['date']['c']))

        header('dateModified', now)
        header('generator', 'https://github.com/edavis/pandoc-opml')
        header('docs', 'http://dev.opml.org/spec2.html')

        generated = ET.Comment(' OPML generated by pandoc-opml v%s on %s ' % (__version__, now))
        root.insert(0, generated)

        for summit in self.nodes.pop(0):
            params = {'text': summit.text}
            params.update(summit.attr)
            el = ET.SubElement(body, 'outline', **params)
            process(el, summit)

        content = ET.ElementTree(root)
        content.write(
            open(output, 'wb') if output else sys.stdout,
            encoding = 'UTF-8',
            xml_declaration = True,
        )

    def extract_header_attributes(self, attr):
        outline_attr = {}
        name, args, kwargs = attr
        if name:
            outline_attr['name'] = name
        for arg in args:
            outline_attr[arg] = 'true'
        outline_attr.update(dict(kwargs))
        return outline_attr

    def extract(self, contents):
        ret = []
        for obj in contents:
            if obj.get('t') == 'Str':
                ret.append(obj.get('c'))
            elif obj.get('t') == 'Space':
                ret.append(' ')
            elif obj.get('t') == 'Link':
                content, (link_url, link_title) = obj.get('c')
                text = self.extract(content)
                if link_title:
                    ret.append(r'<a href="%s" title="%s">%s</a>' % (link_url, link_title, text))
                else:
                    ret.append(r'<a href="%s">%s</a>' % (link_url, text))
            elif obj.get('t') == 'Emph':
                ret.append(r'<em>%s</em>' % self.extract(obj.get('c')))
            elif obj.get('t') == 'Strong':
                ret.append(r'<strong>%s</strong>' % self.extract(obj.get('c')))
            elif obj.get('t') == 'Subscript':
                ret.append(r'<sub>%s</sub>' % self.extract(obj.get('c')))
            elif obj.get('t') == 'Superscript':
                ret.append(r'<sup>%s</sup>' % self.extract(obj.get('c')))
            elif obj.get('t') == 'Strikeout':
                ret.append(r'<del>%s</del>' % self.extract(obj.get('c')))
            elif obj.get('t') == 'Code':
                (_, code) = obj.get('c')
                ret.append(r'<code>%s</code>' % code)

        return ''.join(ret)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    parser.add_argument('input')
    args = parser.parse_args()

    json_ast = subprocess.check_output(['pandoc', '-t', 'json', args.input])

    p = PandocOPML(json_ast)
    p.write(args.output)
